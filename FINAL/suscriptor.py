"""Suscriptor de alertas por consola (lo reemplaza el dashboard más adelante).

Se suscribe al canal de alertas de Redis y las imprime apenas llegan.
    python3 suscriptor.py
"""
import json
import os
import time

import redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CANAL_ALERTAS = "alertas"


def main():
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    pubsub.subscribe(CANAL_ALERTAS)
    print(f"escuchando alertas en '{CANAL_ALERTAS}'...", flush=True)
    for mensaje in pubsub.listen():
        if mensaje["type"] != "message":
            continue
        alerta = json.loads(mensaje["data"])
        hora = time.strftime("%H:%M:%S", time.localtime(alerta["ts"]))
        print(f"[{hora}] ALERTA {alerta['tipo'].upper()} en {alerta['tramo']}: "
              f"velocidad promedio {alerta['velocidad_promedio']} km/h "
              f"({alerta['lecturas']} lecturas)", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("suscriptor detenido")