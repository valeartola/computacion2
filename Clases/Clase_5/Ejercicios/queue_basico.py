from multiprocessing import Process
from multiprocessing import Queue

q = Queue()

def productor(q):
    q.put("Hola desde el productor")

def consumidor(q):
    mensaje = q.get()
    print("Consumidor recibió:", mensaje)

# Crear la cola
q = Queue()

# Crear procesos
p1 = Process(target=productor, args=(q,))
p2 = Process(target=consumidor, args=(q,))

# Iniciar procesos
p1.start()
p2.start()

# Esperar a que terminen
p1.join()
p2.join()
