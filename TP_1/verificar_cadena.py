import json
import hashlib

def calcular_hash(prev_hash, datos, timestamp):
    bloque_str = str(prev_hash) + str(datos) + str(timestamp)
    return hashlib.sha256(bloque_str.encode()).hexdigest()

def verificar_cadena():
    try:
        with open("blockchain.json", "r") as f:
            blockchain = json.load(f)
    except FileNotFoundError:
        print("ERROR: No se encontró el archivo blockchain.json")
        return

    corruptos = 0
    alertas = 0
    suma_freq = 0
    suma_pres = 0
    suma_oxi = 0
    total = len(blockchain)

    for i, bloque in enumerate(blockchain):
        # Verificar encadenamiento
        prev_hash = "0"*64 if i == 0 else blockchain[i-1]["hash"]
        esperado = calcular_hash(prev_hash, bloque["datos"], bloque["timestamp"])
        if bloque["hash"] != esperado:
            print(f"[CORRUPTO] Bloque {i} tiene hash inválido")
            corruptos += 1

        if bloque["alerta"]:
            alertas += 1

        suma_freq += bloque["datos"]["frecuencia"]["media"]
        suma_pres += bloque["datos"]["presion"]["media"]
        suma_oxi  += bloque["datos"]["oxigeno"]["media"]

    prom_freq = suma_freq / total
    prom_pres = suma_pres / total
    prom_oxi  = suma_oxi  / total

    print("Verificación completa")
    print(f"Bloques totales: {total}")
    print(f"Bloques corruptos: {corruptos}")
    print(f"Bloques con alertas: {alertas}")

    with open("reporte.txt", "w") as f:
        f.write(f"Total de bloques: {total}\n")
        f.write(f"Bloques con alertas: {alertas}\n")
        f.write(f"Promedio frecuencia: {prom_freq:.2f}\n")
        f.write(f"Promedio presión: {prom_pres:.2f}\n")
        f.write(f"Promedio oxígeno: {prom_oxi:.2f}\n")

if __name__ == "__main__":
    verificar_cadena()
