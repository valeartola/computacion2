import os

pid = os.fork()

if pid == 0:
    os.execlp("ls", "ls", "-l")  # Reemplaza el proceso hijo con `ls -l`
else:
    os.wait()  # Espera al hijo antes de terminar
