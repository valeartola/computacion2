import os
import time

pid = os.fork()

if pid > 0:
    print(f"Padre (PID {os.getpid()}) terminando...")
else:
    time.sleep(5)  # Espera para que el padre termine primero
    print(f"Hijo (PID {os.getpid()}) ahora es huérfano, su nuevo padre es {os.getppid()}")
