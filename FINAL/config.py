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


def horarios_previstos(linea: int) -> dict:
    """Horario previsto de llegada a cada parada, en segundos desde que el micro sale de la terminal.

    Se calcula suponiendo calle libre (velocidad base) y la espera fija en cada parada.
    Con el tráfico alto el micro llega más tarde que esto, y esa diferencia es la demora.
    """
    paradas = LINEAS[linea]["paradas"]
    metros_por_segundo = VELOCIDAD_BASE_KMH / 3.6
    t = 0.0
    horarios = {}
    for i in range(1, len(paradas)):
        t += (paradas[i][1] - paradas[i - 1][1]) / metros_por_segundo   # viaje hasta esa parada
        horarios[paradas[i][0]] = round(t)
        t += PARADA_SEGUNDOS                                            # y la espera antes de salir
    return horarios


# Línea -> {parada: segundos previstos}. Con los valores de arriba, la línea 1 da
# Plaza 80 s, Hospital 160 s, Estación 240 s y Cierre 330 s.
HORARIOS = {linea: horarios_previstos(linea) for linea in LINEAS}


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