"""Worker de TrafficWatch: analiza los lotes que el gateway dejó en la cola.

Cada tarea recibe UN lote (5 lecturas de un micro) y hace todo el recorrido:
  1. guarda las lecturas en las ventanas de Redis (una por tramo y una por micro),
  2. descarta lo que tenga más de 30 s,
  3. lee la ventana del tramo y aplica la regla de congestión,
  4. si corresponde, publica una alerta (una sola vez por minuto y por tramo).

Los workers no recuerdan nada entre una tarea y otra, y la siguiente tarea puede
tomarla otro worker: por eso el historial reciente vive en Redis y no en memoria.

Cómo se levanta (desde la carpeta del proyecto, con el venv activado):
    celery -A tareas worker --loglevel=info --concurrency=2
"""
import json
import os

import redis
from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Umbrales: valores por defecto, se pueden cambiar con variables de entorno
VENTANA_S = float(os.environ.get("TW_VENTANA_S", 30))              # tamaño de la ventana
UMBRAL_CONGESTION_KMH = float(os.environ.get("TW_UMBRAL_KMH", 15))  # promedio por debajo = congestión
MIN_LECTURAS = int(os.environ.get("TW_MIN_LECTURAS", 3))            # lecturas mínimas para decidir
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

    # Cooldown: SET con NX solo tiene éxito para el primero que lo intenta, y es atómico.
    # Si dos workers detectan la congestión a la vez, solo uno logra publicar la alerta.
    if not r.set(f"alerta:congestion:{tramo}", "1", nx=True, ex=COOLDOWN_S):
        return None
    alerta = {
        "tipo": "congestion",
        "tramo": tramo,
        "velocidad_promedio": round(promedio, 1),
        "lecturas": len(en_marcha),
        "ts": ahora,
    }
    r.publish(CANAL_ALERTAS, json.dumps(alerta))
    return alerta


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
        alerta = evaluar_congestion(r, tramo, ahora)
        if alerta:
            alertas.append(alerta)
    return len(alertas)