import os

print(f"Soy el proceso padre con PID {os.getpid()}")

for i in range(3):

    pid = os.fork()

    if pid == 0:
        print(f"Soy el hijo {os.getpid()}, ejecutando 'ls -l'")
        os.execlp("ls", "ls", "-l")  # El hijo ejecuta 'ls -l'
    else:
        print(f"El padre {os.getpid()} espera a que su hijo termine...")
        os.wait()  # Espera a que el hijo termine antes de continuar
        print("El hijo ha terminado, el padre continúa")