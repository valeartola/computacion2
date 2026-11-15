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


def describir(a: dict) -> str:
    if a["tipo"] == "congestion":
        return (f"CONGESTION en {a['tramo']}: velocidad promedio "
                f"{a['velocidad_promedio']} km/h ({a['lecturas']} lecturas de {a['micros']} micros)")
    if a["tipo"] == "detenido":
        return (f"MICRO DETENIDO: micro {a['micro_id']} quieto hace {a['segundos']} s "
                f"en {a['tramo']}, metro {a['posicion']}")
    if a["tipo"] == "demora":
        return (f"DEMORA: micro {a['micro_id']} llegó a {a['parada']} con "
                f"{a['demora_s']} s de retraso")
    return str(a)


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
        print(f"[{hora}] ALERTA {describir(alerta)}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("suscriptor detenido")