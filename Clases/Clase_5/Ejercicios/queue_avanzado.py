from multiprocessing import Process, Queue
import time
import random

def productor(q):
    for i in range(5):
        numero = random.randint(1, 100)
        print(f"[Productor] Generando número: {numero}")
        q.put(numero)
        time.sleep(1)  # Simula tiempo de procesamiento
    q.put("FIN")  # Señal de que terminó

def consumidor(q):
    while True:
        dato = q.get()
        if dato == "FIN":
            print("[Consumidor] Terminando.")
            break
        print(f"[Consumidor] Procesando número: {dato}")
        time.sleep(2)  # Simula trabajo más lento

if __name__ == "__main__":
    q = Queue()
    p1 = Process(target=productor, args=(q,))
    p2 = Process(target=consumidor, args=(q,))

    p1.start()
    p2.start()

    p1.join()
    p2.join()
