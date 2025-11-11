import pickle
import base64
import io

def serialize(data: dict) -> bytes:
    """Serializa un diccionario Python a bytes usando pickle."""
    try:
        return pickle.dumps(data)
    except Exception as e:
        print(f"Error de serialización: {e}")
        return b''

def deserialize(data: bytes) -> dict:
    """Deserializa bytes a un diccionario Python usando pickle."""
    try:
        return pickle.loads(data)
    except Exception as e:
        print(f"Error de deserialización: {e}")
        return {}

def b64encode_bytes(data: bytes) -> str:
    """Codifica bytes a una cadena Base64 para incluir en JSON."""
    return base64.b64encode(data).decode('utf-8')

b64png = b64encode_bytes