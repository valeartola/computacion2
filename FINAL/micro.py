"""Micro: un colectivo simulado que reporta sus lecturas al gateway.

Cada micro es un hilo (o el programa principal, si se corre solo). Casi todo su
tiempo lo pasa esperando, por eso alcanza con un hilo y no hace falta un proceso.

Uso solo (para probar):
    python micro.py --id 1 --linea 1 --host 127.0.0.1 --port 9000
Más adelante el simulador crea varios Micro como hilos.
"""
import argparse
import socket
import threading
import time
import uuid
from collections import deque

from config import LINEAS, PARADA_SEGUNDOS, VELOCIDAD_BASE_KMH, id_tramo, trafico
from protocolo import empaquetar, leer_mensaje


class Micro:
    def __init__(self, micro_id, linea=1, host="127.0.0.1", port=9000,
                 intervalo=1.0, batch=5, ack_timeout=2.0):
        self.micro_id = str(micro_id)
        self.linea = linea
        self.host = host
        self.port = port
        self.intervalo = intervalo       # segundos entre lecturas
        self.batch = batch               # lecturas por lote
        self.ack_timeout = ack_timeout   # cuánto espera el ACK antes de dar por caída la conexión
        self.sesion = uuid.uuid4().hex   # identifica esta ejecución del micro (ver gateway)

        self.paradas = LINEAS[linea]["paradas"]
        self.posicion = 0.0              # metros recorridos desde el inicio de la ruta
        self.proxima = 1                 # índice de la próxima parada; el tramo actual es proxima - 1
        self.parada_hasta = 0.0          # hasta cuándo se queda en la parada actual (reloj monotónico)

        self.averiado = threading.Event()  # el simulador lo activa para provocar una avería
        self.detener = threading.Event()   # pide que el micro termine

        self.sock = None
        self.n_lote = 0
        self.lote_actual = []
        # Lotes armados que el gateway todavía no confirmó. Si se llena, se pierden los más viejos.
        self.pendientes = deque(maxlen=100)
        self._espera_reconexion = 1.0
        self._proximo_intento = 0.0

    def log(self, texto):
        print(f"[micro {self.micro_id}] {texto}", flush=True)

    # ---------------------------------------------------------------- simulación
    def _tick(self) -> dict:
        """Avanza un paso de `intervalo` segundos y devuelve la lectura de ese momento."""
        ahora = time.monotonic()
        tramo = self.proxima - 1
        en_parada = ahora < self.parada_hasta

        if en_parada or self.averiado.is_set():
            velocidad = 0.0
        else:
            nivel = trafico.get(self.linea, tramo)
            velocidad = VELOCIDAD_BASE_KMH * (1 - 0.8 * nivel)
            self.posicion += velocidad / 3.6 * self.intervalo   # km/h -> m/s

            destino = self.paradas[self.proxima][1]
            if self.posicion >= destino:                         # llegó a la parada
                self.posicion = float(destino)
                self.parada_hasta = ahora + PARADA_SEGUNDOS
                if self.proxima == len(self.paradas) - 1:        # fin de la ruta: vuelve a empezar
                    self.posicion = 0.0
                    self.proxima = 1
                else:
                    self.proxima += 1

        return {
            "micro_id": self.micro_id,
            "linea": self.linea,
            "ts": time.time(),
            "posicion": round(self.posicion, 1),
            "tramo": id_tramo(self.linea, tramo),
            "velocidad": round(velocidad, 1),   # km/h
            "en_parada": en_parada,
        }

    # ---------------------------------------------------------------- red
    def _cerrar(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

    def _asegurar_conexion(self) -> bool:
        """Conecta si hace falta. Un solo intento por llamada, con espera creciente entre intentos,
        para que el micro siga avanzando aunque el gateway esté caído."""
        if self.sock is not None:
            return True
        if time.monotonic() < self._proximo_intento:
            return False
        try:
            s = socket.create_connection((self.host, self.port), timeout=5)
            s.settimeout(self.ack_timeout)
            s.sendall(empaquetar({"tipo": "hola", "micro_id": self.micro_id,
                                  "linea": self.linea, "sesion": self.sesion}))
            self.sock = s
            self._espera_reconexion = 1.0
            self.log(f"conectado a {self.host}:{self.port}")
            return True
        except OSError as e:
            self.log(f"no pude conectar ({e}); reintento en {self._espera_reconexion:.0f} s")
            self._proximo_intento = time.monotonic() + self._espera_reconexion
            self._espera_reconexion = min(self._espera_reconexion * 2, 10.0)
            return False

    def _enviar_pendientes(self):
        """Manda los lotes pendientes en orden. Cada uno se da por entregado solo cuando llega su ACK."""
        if not self._asegurar_conexion():
            return
        try:
            while self.pendientes:
                lote = self.pendientes[0]
                self.sock.sendall(empaquetar(lote))
                respuesta = leer_mensaje(self.sock)
                if respuesta.get("tipo") == "ack" and respuesta.get("n") == lote["n"]:
                    self.pendientes.popleft()
                else:
                    raise ConnectionError(f"respuesta inesperada: {respuesta}")
        except (OSError, ConnectionError, ValueError) as e:
            # OSError incluye el timeout de espera del ACK
            self.log(f"conexión perdida ({e}); quedan {len(self.pendientes)} lotes sin confirmar")
            self._cerrar()

    # ---------------------------------------------------------------- bucle principal
    def run(self):
        self.log(f"arranca en la línea {self.linea}")
        siguiente = time.monotonic()
        try:
            while not self.detener.is_set():
                self.lote_actual.append(self._tick())
                if len(self.lote_actual) >= self.batch:
                    self.n_lote += 1
                    self.pendientes.append({"tipo": "lote", "micro_id": self.micro_id,
                                            "n": self.n_lote, "lecturas": self.lote_actual})
                    self.lote_actual = []
                    self._enviar_pendientes()
                siguiente += self.intervalo
                self.detener.wait(max(0.0, siguiente - time.monotonic()))
        finally:
            self._cerrar()
            self.log("terminó")


def main():
    p = argparse.ArgumentParser(description="Micro simulado de TrafficWatch")
    p.add_argument("--id", required=True, help="identificador del micro")
    p.add_argument("--linea", type=int, default=1)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=9000)
    p.add_argument("--intervalo", type=float, default=1.0, help="segundos entre lecturas")
    p.add_argument("--batch", type=int, default=5, help="lecturas por lote")
    p.add_argument("--trafico", type=float, default=0.0,
                   help="nivel de tráfico 0..1 en toda la línea (para probar; después lo maneja el simulador)")
    a = p.parse_args()

    for tramo in range(len(LINEAS[a.linea]["paradas"]) - 1):
        trafico.set(a.linea, tramo, a.trafico)
    micro = Micro(a.id, a.linea, a.host, a.port, a.intervalo, a.batch)
    try:
        micro.run()
    except KeyboardInterrupt:
        micro.detener.set()


if __name__ == "__main__":
    main()