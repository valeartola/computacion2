"""Gateway: recibe los lotes de todos los micros y los encola. No analiza nada.

Un solo proceso con un solo hilo (asyncio) sostiene todas las conexiones: mientras
un micro no manda nada, el gateway atiende a otro. Por cada lote:
  1. lo lee (prefijo de largo + JSON) y lo valida,
  2. lo encola (por ahora lo imprime; en la sesión de Celery pasa a analizar_lote.delay),
  3. recién entonces responde el ACK: "recibí y encolé el lote n".

Uso:
    python3 gateway.py --port 9000              # con Celery y Redis
    python3 gateway.py --port 9000 --sin-cola   # solo imprime, sin Redis
"""
import argparse
import asyncio
import re

from protocolo import empaquetar, leer_mensaje_async

TIMEOUT_SESION = 10  # segundos sin recibir nada de un micro antes de cerrar su sesión

# Formas permitidas. Los ids se usan para armar claves de Redis, así que se limitan a letras, números, _ y -.
ID_VALIDO = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
TRAMO_VALIDO = re.compile(r"^L\d+-T\d+$")
CAMPOS_LECTURA = ("micro_id", "linea", "ts", "posicion", "tramo", "velocidad", "en_parada")
MAX_LECTURAS_POR_LOTE = 100

conexiones = {}   # micro_id -> writer de su conexión abierta (servirá para avisarle al micro)
sesiones = {}     # micro_id -> id de sesión del micro (cambia cada vez que el micro se reinicia)
ultimo_lote = {}  # micro_id -> número del último lote encolado (para descartar repetidos)
candados = {}     # micro_id -> asyncio.Lock: una sola conexión a la vez revisa y encola lotes de ese micro


analizar_lote = None  # la tarea de Celery; se carga en el arranque salvo con --sin-cola


async def encolar(lote: dict) -> None:
    """Deja el lote en la cola de Celery (un papelito para los workers) e imprime un resumen.

    .delay() es una llamada de red bloqueante, así que se hace en un hilo aparte:
    mientras tanto el event loop sigue atendiendo a los demás micros.
    Si Redis está caído lanza una excepción y el lote no se confirma.
    """
    if analizar_lote is not None:
        await asyncio.to_thread(analizar_lote.delay, lote)
    lecturas = lote["lecturas"]
    ultima = lecturas[-1]
    print(f"  lote {lote['n']} del micro {lote['micro_id']}: {len(lecturas)} lecturas, "
          f"última en {ultima['tramo']} a {ultima['velocidad']} km/h", flush=True)


def es_numero(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)   # bool es un int en Python, no lo queremos


def motivo_hola_invalido(hola):
    """Devuelve por qué el 'hola' no sirve, o None si está bien."""
    if not isinstance(hola, dict):
        return "no es un diccionario"
    if hola.get("tipo") != "hola":
        return "no empezó con 'hola'"
    if not ID_VALIDO.match(str(hola.get("micro_id", ""))):
        return "micro_id inválido"
    return None


def motivo_lectura_invalida(lec, micro_id):
    """Devuelve por qué una lectura no sirve, o None si está bien."""
    if not isinstance(lec, dict):
        return "una lectura no es un diccionario"
    for campo in CAMPOS_LECTURA:
        if campo not in lec:
            return f"a una lectura le falta '{campo}'"
    if str(lec["micro_id"]) != micro_id:
        return "una lectura es de otro micro"
    if not (es_numero(lec["ts"]) and es_numero(lec["posicion"]) and es_numero(lec["velocidad"])):
        return "ts, posicion o velocidad no son números"
    if lec["posicion"] < 0 or lec["velocidad"] < 0:
        return "posicion o velocidad negativas"
    if not isinstance(lec["en_parada"], bool):
        return "en_parada tiene que ser verdadero o falso"
    if not (isinstance(lec["tramo"], str) and TRAMO_VALIDO.match(lec["tramo"])):
        return "tramo inválido"
    if lec.get("parada") is not None and not isinstance(lec["parada"], str):
        return "parada tiene que ser texto"
    if lec.get("t_llegada") is not None and not es_numero(lec["t_llegada"]):
        return "t_llegada tiene que ser un número"
    return None


def motivo_lote_invalido(msg, micro_id):
    """Devuelve por qué el lote no sirve, o None si está bien."""
    if not isinstance(msg, dict):
        return "no es un diccionario"
    if msg.get("tipo") != "lote":
        return "el tipo no es 'lote'"
    n = msg.get("n")
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        return "'n' tiene que ser un entero positivo"
    if str(msg.get("micro_id")) != micro_id:
        return "el lote dice ser de otro micro"
    lecturas = msg.get("lecturas")
    if not isinstance(lecturas, list) or not lecturas:
        return "'lecturas' tiene que ser una lista con algo adentro"
    if len(lecturas) > MAX_LECTURAS_POR_LOTE:
        return "demasiadas lecturas en un lote"
    for lec in lecturas:
        motivo = motivo_lectura_invalida(lec, micro_id)
        if motivo:
            return motivo
    return None


async def atender(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Una corrutina por micro conectado. Cuando espera datos, el event loop atiende a los demás."""
    peer = writer.get_extra_info("peername")
    micro_id = None
    try:
        hola = await asyncio.wait_for(leer_mensaje_async(reader), TIMEOUT_SESION)
        motivo = motivo_hola_invalido(hola)
        if motivo:
            print(f"{peer}: 'hola' rechazado ({motivo}), cierro la conexión", flush=True)
            return
        micro_id = str(hola["micro_id"])
        # Si el micro se reinició (sesión nueva), su numeración de lotes vuelve a empezar de 1.
        if sesiones.get(micro_id) != hola.get("sesion"):
            sesiones[micro_id] = hola.get("sesion")
            ultimo_lote[micro_id] = 0
        conexiones[micro_id] = writer
        print(f"micro {micro_id} conectado desde {peer}", flush=True)

        while True:
            msg = await asyncio.wait_for(leer_mensaje_async(reader), TIMEOUT_SESION)
            motivo = motivo_lote_invalido(msg, micro_id)
            if motivo:
                # Un micro de verdad nunca manda esto: es una violación del protocolo, se corta la conexión.
                print(f"micro {micro_id}: lote rechazado ({motivo}), cierro la conexión", flush=True)
                return
            n = msg["n"]
            # El candado hace que "revisar si es nuevo + encolar + anotar" sea un solo bloque por micro:
            # si dos conexiones del mismo micro mandan el mismo lote a la vez, la segunda espera y lo ve repetido.
            candado = candados.setdefault(micro_id, asyncio.Lock())
            async with candado:
                if n > ultimo_lote.get(micro_id, 0):
                    try:
                        await encolar(msg)
                    except Exception as e:
                        # Sin ACK: el micro da el lote por no entregado y lo reenvía más tarde.
                        print(f"micro {micro_id}: no pude encolar el lote {n} "
                              f"({type(e).__name__}: {e}); no mando ACK", flush=True)
                        continue
                    ultimo_lote[micro_id] = n
                else:
                    print(f"  lote {n} del micro {micro_id} repetido, lo descarto", flush=True)
            # El ACK se manda también para los repetidos, así el micro deja de reenviarlos.
            writer.write(empaquetar({"tipo": "ack", "n": n}))
            await writer.drain()
    except asyncio.TimeoutError:
        print(f"micro {micro_id or peer}: {TIMEOUT_SESION} s sin actividad, cierro la sesión", flush=True)
    except (asyncio.IncompleteReadError, ConnectionError):
        print(f"micro {micro_id or peer} se desconectó", flush=True)
    except ValueError as e:
        print(f"micro {micro_id or peer}: mensaje ilegible ({e})", flush=True)
    finally:
        if micro_id is not None and conexiones.get(micro_id) is writer:
            del conexiones[micro_id]
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def main(host, port):
    # host=None escucha en todas las interfaces, IPv4 e IPv6
    servidor = await asyncio.start_server(atender, host, port)
    direcciones = ", ".join(str(s.getsockname()[:2]) for s in servidor.sockets)
    print(f"gateway escuchando en {direcciones}", flush=True)
    async with servidor:
        await servidor.serve_forever()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Gateway de TrafficWatch")
    p.add_argument("--host", default=None, help="por defecto, todas las interfaces")
    p.add_argument("--port", type=int, default=9000)
    p.add_argument("--sin-cola", action="store_true",
                   help="no usar Celery/Redis: solo recibir e imprimir (para probar sin Redis)")
    a = p.parse_args()
    if not a.sin_cola:
        from tareas import analizar_lote as _tarea
        analizar_lote = _tarea
    try:
        asyncio.run(main(a.host, a.port))
    except KeyboardInterrupt:
        print("gateway detenido")