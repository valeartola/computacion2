"""Datos de las líneas y estado compartido del tráfico.

Una línea es una ruta recta medida en metros, con paradas en posiciones fijas.
Los tramos son los pedazos entre dos paradas consecutivas:
tramo 0 = entre la parada 0 y la 1, tramo 1 = entre la 1 y la 2, etc.
"""
import threading

LINEAS = {
    1: {
        "nombre": "Línea 1",
        # (nombre de la parada, metro de la ruta donde está)
        "paradas": [
            ("Terminal", 0),
            ("Plaza", 800),
            ("Hospital", 1500),
            ("Estación", 2200),
            ("Cierre", 3000),
        ],
    },
}

VELOCIDAD_BASE_KMH = 36      # velocidad con la calle libre
PARADA_SEGUNDOS = 10         # cuánto se queda quieto en cada parada


def id_tramo(linea: int, tramo: int) -> str:
    """Nombre del tramo que se usa en Redis y en el dashboard: 'L1-T0'."""
    return f"L{linea}-T{tramo}"


class Trafico:
    """Nivel de tráfico de cada tramo, entre 0 (libre) y 1 (colapsado).

    Lo leen todos los micros (hilos) y lo cambia el simulador, por eso lleva un Lock.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._niveles = {}

    def get(self, linea: int, tramo: int) -> float:
        with self._lock:
            return self._niveles.get((linea, tramo), 0.0)

    def set(self, linea: int, tramo: int, nivel: float) -> None:
        with self._lock:
            self._niveles[(linea, tramo)] = max(0.0, min(1.0, nivel))


# Una única instancia compartida por todos los micros del mismo proceso.
trafico = Trafico()