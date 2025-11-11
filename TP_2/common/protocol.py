import struct
from .serialization import serialize, deserialize

LENGTH_FIELD_SIZE = 4
BYTE_ORDER = '!' 

def encode_message(data: dict) -> bytes:
    """Codifica un diccionario en un mensaje binario: [longitud_4_bytes][payload]"""
    payload = serialize(data)
    payload_len = len(payload)
    
    if payload_len == 0:
        return b''

    packed_len = struct.pack(f'{BYTE_ORDER}I', payload_len)
    
    return packed_len + payload

def decode_message(stream: bytes) -> tuple[dict | None, bytes]:
    """
    Intenta decodificar un mensaje completo del stream de bytes.
    Retorna (mensaje_decodificado, bytes_restantes)
    """
    if len(stream) < LENGTH_FIELD_SIZE:
        return None, stream

    payload_len_bytes = stream[:LENGTH_FIELD_SIZE]
    payload_len = struct.unpack(f'{BYTE_ORDER}I', payload_len_bytes)[0]

    if len(stream) < LENGTH_FIELD_SIZE + payload_len:
        return None, stream

    payload_start = LENGTH_FIELD_SIZE
    payload_end = LENGTH_FIELD_SIZE + payload_len
    payload = stream[payload_start:payload_end]
    
    message = deserialize(payload)
    remaining_bytes = stream[payload_end:]

    return message, remaining_bytes