import time
import random
from datetime import datetime

def generador(pipe_a, pipe_b, pipe_c):
    for _ in range(60):
        data = {
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "frecuencia": random.randint(60, 180),
            "presion": [random.randint(110, 180), random.randint(70, 110)],
            "oxigeno": random.randint(90, 100)
        }

        pipe_a.send(data)
        pipe_b.send(data)
        pipe_c.send(data)
        time.sleep(1)

    # Avisar fin
    for pipe in [pipe_a, pipe_b, pipe_c]:
        pipe.send("FIN")
        pipe.close()
