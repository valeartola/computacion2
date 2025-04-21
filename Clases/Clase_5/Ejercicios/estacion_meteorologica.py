from multiprocessing import Process, Queue
import time
import random

def sensor(q):
    for _ in range(10):
        temp = random.randint(-10, 40)
        print(f"[Sensor] Emitiendo temperatura: {temp}°C")
        q.put(temp)
        time.sleep(1)
    q.put("FIN")  # Señal para terminar

def analizador(q):
    while True:
        dato = q.get()
        if dato == "FIN":
            print("[Analizador] Finalizando análisis.")
            break

        if dato < 10:
            clasificacion = "fría"
        elif 10 <= dato <= 25:
            clasificacion = "templada"
        else:
            clasificacion = "caliente"

        print(f"[Analizador] Temperatura {clasificacion} ({dato}°C)")
        time.sleep(1.5)  # Simula análisis más lento

if __name__ == "__main__":
    q = Queue()

    p1 = Process(target=sensor, args=(q,))
    p2 = Process(target=analizador, args=(q,))

    p1.start()
    p2.start()

    p1.join()
    p2.join()
