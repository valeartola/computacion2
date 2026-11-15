"""Simulador de TrafficWatch: crea varios micros (uno por hilo) y permite provocar problemas.

Uso (en Ubuntu/WSL, con el gateway andando):
    python3 simulador.py --micros 3 --port 9000

Señales (IPC entre procesos): desde OTRA terminal se le "toca el hombro" al simulador:
    pkill -USR1 -f simulador.py    # alterna TRÁFICO: sube a 0.9 en toda la línea / vuelve a 0
    pkill -USR2 -f simulador.py    # alterna AVERÍA: se descompone / se repara el micro 1
    pkill -TERM -f simulador.py    # (o Ctrl+C) apaga todo ordenadamente

El handler de la señal solo anota "llegó USR1" en una Queue; el trabajo real lo hace el
hilo principal. Así el handler es cortito y no se pisa con el resto del programa.
"""
import argparse
import queue
import signal
import threading

from config import LINEAS, trafico
from micro import Micro

NIVEL_TRAFICO_ALTO = 0.9   # 36 km/h * (1 - 0.8*0.9) = 10 km/h, por debajo del umbral de 15


def main():
    p = argparse.ArgumentParser(description="Simulador de TrafficWatch")
    p.add_argument("--micros", type=int, default=3, help="cantidad de micros")
    p.add_argument("--linea", type=int, default=1)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=9000)
    p.add_argument("--intervalo", type=float, default=1.0, help="segundos entre lecturas")
    p.add_argument("--batch", type=int, default=5, help="lecturas por lote")
    p.add_argument("--separacion", type=float, default=8.0,
                   help="segundos entre la salida de un micro y la del siguiente")
    a = p.parse_args()

    n_tramos = len(LINEAS[a.linea]["paradas"]) - 1
    micros = [Micro(i + 1, a.linea, a.host, a.port, a.intervalo, a.batch) for i in range(a.micros)]
    avisos = queue.Queue()          # acá los handlers dejan lo que pasó; el hilo principal lo atiende
    apagar = threading.Event()

    signal.signal(signal.SIGUSR1, lambda s, f: avisos.put("trafico"))
    signal.signal(signal.SIGUSR2, lambda s, f: avisos.put("averia"))
    signal.signal(signal.SIGTERM, lambda s, f: apagar.set())
    signal.signal(signal.SIGINT, lambda s, f: apagar.set())

    hilos = []
    for m in micros:
        h = threading.Thread(target=m.run, name=f"micro-{m.micro_id}", daemon=True)
        h.start()
        hilos.append(h)
        print(f"[sim] salió el micro {m.micro_id}", flush=True)
        if apagar.wait(a.separacion):       # espera entre salidas, pero corta si piden apagar
            break

    trafico_alto = False
    averiado = False
    print("[sim] listo. USR1 = tráfico, USR2 = avería, Ctrl+C = salir "
          f"(pid {__import__('os').getpid()})", flush=True)

    while not apagar.is_set():
        try:
            aviso = avisos.get(timeout=0.5)
        except queue.Empty:
            continue
        if aviso == "trafico":
            trafico_alto = not trafico_alto
            nivel = NIVEL_TRAFICO_ALTO if trafico_alto else 0.0
            for t in range(n_tramos):
                trafico.set(a.linea, t, nivel)
            print(f"[sim] tráfico {'ALTO' if trafico_alto else 'normal'} en toda la línea {a.linea}", flush=True)
        elif aviso == "averia":
            averiado = not averiado
            micros[0].ordenes.put("averiar" if averiado else "reparar")
            print(f"[sim] {'avería' if averiado else 'reparación'} del micro {micros[0].micro_id}", flush=True)

    print("[sim] apagando micros...", flush=True)
    for m in micros:
        m.detener.set()
    for h in hilos:
        h.join(timeout=5)
    print("[sim] listo, chau", flush=True)


if __name__ == "__main__":
    main()