"""Worker de TrafficWatch: analiza los lotes que el gateway dejó en la cola.

Cada tarea recibe UN lote (5 lecturas de un micro) y hace todo el recorrido:
  1. guarda las lecturas en las ventanas de Redis (una por tramo y una por micro),
  2. descarta lo que tenga más de 30 s,
  3. lee las ventanas y aplica las tres reglas:
       - congestión: velocidad promedio del tramo baja (ventana del tramo),
       - micro detenido: quieto fuera de una parada (ventana del micro),
       - demora: llegó a una parada mucho más tarde que lo previsto,
  4. si se cumple una, publica una alerta (una sola vez por minuto para la misma alerta).

Los workers no recuerdan nada entre una tarea y otra, y la siguiente tarea puede
tomarla otro worker: por eso el historial reciente vive en Redis y no en memoria.

Cómo se levanta (desde la carpeta del proyecto, con el venv activado):
    celery -A tareas worker --loglevel=info --concurrency=2
"""
import json
import os

import redis
from celery import Celery

from config import HORARIOS

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Umbrales: valores por defecto, se pueden cambiar con variables de entorno
VENTANA_S = float(os.environ.get("TW_VENTANA_S", 30))              # tamaño de la ventana
UMBRAL_CONGESTION_KMH = float(os.environ.get("TW_UMBRAL_KMH", 15))  # promedio por debajo = congestión
MIN_LECTURAS = int(os.environ.get("TW_MIN_LECTURAS", 3))            # lecturas mínimas para decidir
DETENIDO_S = float(os.environ.get("TW_DETENIDO_S", 15))            # quieto este tiempo fuera de parada = detenido
DEMORA_S = float(os.environ.get("TW_DEMORA_S", 120))                # más tarde que esto respecto del horario = demora
COOLDOWN_S = int(os.environ.get("TW_COOLDOWN_S", 60))               # no repetir la misma alerta antes
TTL_S = int(os.environ.get("TW_TTL_S", 300))                        # una clave sin uso se borra sola
CANAL_ALERTAS = "alertas"

app = Celery("trafficwatch", broker=REDIS_URL)
app.conf.task_ignore_result = True  # no necesitamos devolver resultados, solo actuar

_conexion = None


def get_redis():
    """Una conexión por proceso worker. Se crea la primera vez que se usa (no al importar),
    porque Celery crea varios procesos hijos y no deben compartir la misma conexión."""
    global _conexion
    if _conexion is None:
        _conexion = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    return _conexion


def clave_tramo(tramo: str) -> str:
    return f"ventana:tramo:{tramo}"


def clave_micro(micro_id: str) -> str:
    return f"ventana:micro:{micro_id}"


def guardar_lecturas(r, lecturas, ahora):
    """Pasos 1 y 2: guarda cada lectura en las dos ventanas y recorta lo viejo.

    La ventana es un sorted set: el 'score' es la hora de la lectura, así que Redis la
    mantiene ordenada por tiempo aunque los lotes lleguen desordenados. El 'member' es la
    lectura en JSON; si el mismo lote llega dos veces, el member es idéntico y no se duplica.
    """
    pipe = r.pipeline()
    claves = set()
    for lec in lecturas:
        miembro = json.dumps(lec, sort_keys=True)
        for clave in (clave_tramo(lec["tramo"]), clave_micro(lec["micro_id"])):
            pipe.zadd(clave, {miembro: lec["ts"]})
            claves.add(clave)
    for clave in claves:
        pipe.zremrangebyscore(clave, "-inf", ahora - VENTANA_S)   # tira lo de más de 30 s
        pipe.expire(clave, TTL_S)                                  # si nadie la usa, se borra sola
    pipe.execute()


def evaluar_congestion(r, tramo, ahora):
    """Pasos 3 y 4 para un tramo. Devuelve la alerta publicada, o None."""
    crudas = r.zrangebyscore(clave_tramo(tramo), ahora - VENTANA_S, "+inf")
    lecturas = [json.loads(x) for x in crudas]
    # Un micro quieto en una parada es normal: no cuenta para el promedio.
    en_marcha = [lec for lec in lecturas if not lec["en_parada"]]
    if len(en_marcha) < MIN_LECTURAS:
        return None
    promedio = sum(lec["velocidad"] for lec in en_marcha) / len(en_marcha)
    if promedio >= UMBRAL_CONGESTION_KMH:
        return None

    return publicar_alerta(r, f"alerta:congestion:{tramo}", {
        "tipo": "congestion",
        "tramo": tramo,
        "velocidad_promedio": round(promedio, 1),
        "lecturas": len(en_marcha),
        "ts": ahora,
    })


def publicar_alerta(r, clave_cooldown, alerta):
    """Publica la alerta solo si no se avisó lo mismo en el último minuto. Devuelve la alerta o None.

    SET con NX solo tiene éxito para el primero que lo intenta, y es atómico: si dos workers
    detectan el mismo problema a la vez, solo uno logra publicar.
    """
    if not r.set(clave_cooldown, "1", nx=True, ex=COOLDOWN_S):
        return None
    r.publish(CANAL_ALERTAS, json.dumps(alerta))
    return alerta


def evaluar_detenido(r, micro_id, ahora):
    """Micro detenido: velocidad 0 en la misma posición durante DETENIDO_S segundos, fuera de parada.

    Usa la ventana del micro. Se recorren sus lecturas desde la más nueva hacia atrás mientras
    el micro siga quieto; si esa racha dura lo suficiente, está detenido.
    """
    crudas = r.zrangebyscore(clave_micro(micro_id), ahora - VENTANA_S, "+inf")   # viene ordenado por hora
    lecturas = [json.loads(x) for x in crudas]
    if not lecturas:
        return None
    ultima = lecturas[-1]
    racha_desde = ultima["ts"]
    for lec in reversed(lecturas):
        quieto = (lec["velocidad"] == 0 and not lec["en_parada"]
                  and lec["posicion"] == ultima["posicion"])
        if not quieto:
            break
        racha_desde = lec["ts"]
    quieto_s = ultima["ts"] - racha_desde
    if ultima["en_parada"] or ultima["velocidad"] != 0 or quieto_s < DETENIDO_S:
        return None
    return publicar_alerta(r, f"alerta:detenido:{micro_id}", {
        "tipo": "detenido",
        "micro_id": micro_id,
        "tramo": ultima["tramo"],
        "posicion": ultima["posicion"],
        "segundos": round(quieto_s),
        "ts": ahora,
    })


def evaluar_demora(r, lecturas, ahora):
    """Demora: el micro llegó a una parada más de DEMORA_S segundos después de lo previsto.

    Mientras está en una parada, cada lectura trae su nombre y cuánto tardó en llegar (t_llegada).
    Se compara con el horario previsto de esa parada. Devuelve las alertas publicadas.
    """
    publicadas = []
    for lec in lecturas:
        parada, t_llegada = lec.get("parada"), lec.get("t_llegada")
        if parada is None or t_llegada is None:
            continue
        previsto = HORARIOS.get(lec["linea"], {}).get(parada)
        if previsto is None:
            continue
        demora = t_llegada - previsto
        if demora <= DEMORA_S:
            continue
        alerta = publicar_alerta(r, f"alerta:demora:{lec['micro_id']}:{parada}", {
            "tipo": "demora",
            "micro_id": lec["micro_id"],
            "tramo": lec["tramo"],
            "parada": parada,
            "demora_s": round(demora),
            "ts": ahora,
        })
        if alerta:
            publicadas.append(alerta)
    return publicadas


@app.task(name="analizar_lote")
def analizar_lote(lote):
    r = get_redis()
    lecturas = lote["lecturas"]
    # "Ahora" es la hora de las lecturas, no la del worker: así el resultado no depende
    # de cuánto tardó el lote en llegar.
    ahora = max(lec["ts"] for lec in lecturas)

    guardar_lecturas(r, lecturas, ahora)

    alertas = []
    for tramo in sorted({lec["tramo"] for lec in lecturas}):
        alertas.append(evaluar_congestion(r, tramo, ahora))
    for micro_id in sorted({lec["micro_id"] for lec in lecturas}):
        alertas.append(evaluar_detenido(r, micro_id, ahora))
    alertas.extend(evaluar_demora(r, lecturas, ahora))
    return sum(1 for a in alertas if a)