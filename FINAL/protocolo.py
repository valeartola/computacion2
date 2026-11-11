"""Protocolo entre micros y gateway.

TCP es un flujo de bytes sin límites de mensaje, así que cada mensaje se manda
con un prefijo de 4 bytes que dice cuántos bytes mide el JSON que viene después.

Mensajes (todos son diccionarios JSON con un campo "tipo"):
  micro -> gateway   {"tipo": "hola", "micro_id": "1", "linea": 1, "sesion": "ab12..."}
  micro -> gateway   {"tipo": "lote", "micro_id": "1", "n": 7, "lecturas": [ {...}, ... ]}
  gateway -> micro   {"tipo": "ack", "n": 7}
"""
import json
import struct

MAX_MENSAJE = 1_000_000  # bytes; protege al gateway de un largo absurdo


def empaquetar(mensaje: dict) -> bytes:
    """Convierte un diccionario en bytes listos para mandar: [largo][JSON]."""
    datos = json.dumps(mensaje).encode("utf-8")
    return struct.pack(">I", len(datos)) + datos


def _recibir_exacto(sock, cantidad: int) -> bytes:
    """Lee exactamente `cantidad` bytes (recv puede devolver menos de los pedidos)."""
    partes = []
    faltan = cantidad
    while faltan:
        trozo = sock.recv(faltan)
        if not trozo:
            raise ConnectionError("la conexión se cerró")
        partes.append(trozo)
        faltan -= len(trozo)
    return b"".join(partes)


def leer_mensaje(sock) -> dict:
    """Versión bloqueante (la usan los micros)."""
    (largo,) = struct.unpack(">I", _recibir_exacto(sock, 4))
    if largo > MAX_MENSAJE:
        raise ValueError(f"mensaje demasiado grande: {largo} bytes")
    return json.loads(_recibir_exacto(sock, largo))


async def leer_mensaje_async(reader) -> dict:
    """Versión asyncio (la usa el gateway). Falla con IncompleteReadError si se corta."""
    cabecera = await reader.readexactly(4)
    (largo,) = struct.unpack(">I", cabecera)
    if largo > MAX_MENSAJE:
        raise ValueError(f"mensaje demasiado grande: {largo} bytes")
    datos = await reader.readexactly(largo)
    return json.loads(datos)