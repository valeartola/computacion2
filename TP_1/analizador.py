from collections import deque

def analizador_frecuencia(conn, queue_salida):
    ventana = deque(maxlen=30)
    while True:
        dato = conn.recv()
        if dato == "FIN":
            queue_salida.put("FIN")
            break
        frecuencia = dato["frecuencia"]
        ventana.append(frecuencia)
        media = sum(ventana) / len(ventana)
        desv = (sum((x - media)**2 for x in ventana) / len(ventana))**0.5
        queue_salida.put({
            "tipo": "frecuencia",
            "timestamp": dato["timestamp"],
            "media": media,
            "desv": desv
        })

def analizador_presion(conn, queue_salida):
    ventana = deque(maxlen=30)
    while True:
        dato = conn.recv()
        if dato == "FIN":
            queue_salida.put("FIN")
            break
        sistolica = dato["presion"][0]
        ventana.append(sistolica)
        media = sum(ventana) / len(ventana)
        desv = (sum((x - media)**2 for x in ventana) / len(ventana))**0.5
        queue_salida.put({
            "tipo": "presion",
            "timestamp": dato["timestamp"],
            "media": media,
            "desv": desv
        })

def analizador_oxigeno(conn, queue_salida):
    ventana = deque(maxlen=30)
    while True:
        dato = conn.recv()
        if dato == "FIN":
            queue_salida.put("FIN")
            break
        oxigeno = dato["oxigeno"]
        ventana.append(oxigeno)
        media = sum(ventana) / len(ventana)
        desv = (sum((x - media)**2 for x in ventana) / len(ventana))**0.5
        queue_salida.put({
            "tipo": "oxigeno",
            "timestamp": dato["timestamp"],
            "media": media,
            "desv": desv
        })
