import os

pid = os.fork()

if pid > 0:
    print(f"Soy el proceso padre, mi PID es {os.getpid()} y mi hijo tiene PID {pid}")
else:
    print(f"Soy el proceso hijo, mi PID es {os.getpid()} y mi padre tiene PID {os.getppid()}")
