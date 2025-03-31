import os
import time

pid = os.fork()

if pid > 0:
    print(f"Padre esperando que termine el hijo {pid}...")
    os.wait()  # Espera a que el hijo termine
    print("Hijo finalizó, padre continúa.")
else:
    print(f"Hijo ejecutándose (PID {os.getpid()})...")
    time.sleep(3)  # Simula un proceso largo
    print("Hijo termina.")
