import os
import time

pid = os.fork()

if pid > 0:
    print(f"Padre (PID {os.getpid()}) creando un zombi...")
    time.sleep(10)  # El padre sigue ejecutándose sin hacer wait()
else:
    print(f"Hijo (PID {os.getpid()}) terminando...")
    exit(0)
