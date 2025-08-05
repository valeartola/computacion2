import hashlib
import json
import os

def calcular_hash(prev_hash, datos, timestamp):
    bloque_str = str(prev_hash) + str(datos) + str(timestamp)
    return hashlib.sha256(bloque_str.encode()).hexdigest()

def guardar_blockchain(blockchain):
    with open("blockchain.json", "w") as f:
        json.dump(blockchain, f, indent=4)
    print("Blockchain guardada en blockchain.json")

def verificador(queue_freq, queue_pres, queue_oxi):
    blockchain = []
    bloque_idx = 0

    while True:
        resultados = {}

        # Esperar un resultado de cada cola
        for cola, tipo in [(queue_freq, "frecuencia"), (queue_pres, "presion"), (queue_oxi, "oxigeno")]:
            resultado = cola.get()
            if resultado == "FIN":
                guardar_blockchain(blockchain)
                return
            resultados[tipo] = resultado

        timestamp = resultados["frecuencia"]["timestamp"]  # asumimos sincronía
        alerta = (
            resultados["frecuencia"]["media"] >= 200 or
            not (90 <= resultados["oxigeno"]["media"] <= 100) or
            resultados["presion"]["media"] >= 200
        )

        datos_bloque = {
            "frecuencia": {
                "media": resultados["frecuencia"]["media"],
                "desv": resultados["frecuencia"]["desv"]
            },
            "presion": {
                "media": resultados["presion"]["media"],
                "desv": resultados["presion"]["desv"]
            },
            "oxigeno": {
                "media": resultados["oxigeno"]["media"],
                "desv": resultados["oxigeno"]["desv"]
            }
        }

        prev_hash = blockchain[-1]["hash"] if blockchain else "0" * 64
        bloque = {
            "timestamp": timestamp,
            "datos": datos_bloque,
            "alerta": alerta,
            "prev_hash": prev_hash,
            "hash": calcular_hash(prev_hash, datos_bloque, timestamp)
        }

        blockchain.append(bloque)
        print(f"[BLOQUE #{bloque_idx}] Hash: {bloque['hash']}  Alerta: {bloque['alerta']}")
        bloque_idx += 1
