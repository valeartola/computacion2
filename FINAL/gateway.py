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

from protocolo import empaquetar, leer_mensaje_async

TIMEOUT_SESION = 10  # segundos sin recibir nada de un micro antes de cerrar su sesión

conexiones = {}   # micro_id -> writer de su conexión abierta (servirá para avisarle al micro)
sesiones = {}     # micro_id -> id de sesión del micro (cambia cada vez que el micro se reinicia)
ultimo_lote = {}  # micro_id -> número del último lote encolado (para descartar repetidos)


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


def lote_valido(msg: dict) -> bool:
    return (msg.get("tipo") == "lote" and isinstance(msg.get("n"), int)
            and isinstance(msg.get("lecturas"), list) and len(msg["lecturas"]) > 0)


async def atender(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Una corrutina por micro conectado. Cuando espera datos, el event loop atiende a los demás."""
    peer = writer.get_extra_info("peername")
    micro_id = None
    try:
        hola = await asyncio.wait_for(leer_mensaje_async(reader), TIMEOUT_SESION)
        if hola.get("tipo") != "hola" or "micro_id" not in hola:
            print(f"{peer}: no empezó con 'hola', lo cierro", flush=True)
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
            if not lote_valido(msg):
                print(f"micro {micro_id}: mensaje inválido, lo descarto", flush=True)
                continue
            n = msg["n"]
            if n > ultimo_lote.get(micro_id, 0):
                try:
                    await encolar(msg)
                except Exception as e:
                    # Sin ACK: el micro da el lote por no entregado y lo reenvía más tarde.
                    print(f"micro {micro_id}: no pude encolar el lote {n} ({e}); no mando ACK", flush=True)
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