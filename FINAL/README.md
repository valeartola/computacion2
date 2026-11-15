# TrafficWatch

Sistema distribuido que monitorea micros simulados en tiempo real y avisa cuando detecta
**congestión** en un tramo, un **micro detenido** fuera de parada o una **demora** respecto del horario previsto.

## Cómo funciona (en una línea)
Los micros mandan lecturas por TCP a un gateway; el gateway las deja en una cola (Redis + Celery);
los workers las analizan y publican alertas, que un suscriptor imprime por consola.

```
simulador -> micros (hilos) --TCP--> gateway (asyncio) --Celery/Redis--> workers --pub/sub--> suscriptor
```

## Componentes y cómo lanzarlos
Todos desde la carpeta del proyecto, con el entorno virtual activado (ver INSTALL.md). Una terminal por componente:

| Componente | Comando |
|---|---|
| Redis | `sudo service redis-server start` |
| Worker | `celery -A tareas worker --loglevel=info --concurrency=2` |
| Suscriptor | `python3 suscriptor.py` |
| Gateway | `python3 gateway.py --port 9000` |
| Simulador | `python3 simulador.py --micros 3 --port 9000` |

Un micro suelto (para pruebas): `python3 micro.py --id 1 --port 9000 [--trafico 0.8] [--averia-en 5]`

## Provocar situaciones (desde otra terminal)
```
pkill -USR1 -f simulador.py   # alterna tráfico alto / normal en toda la línea  -> CONGESTION
pkill -USR2 -f simulador.py   # alterna avería / reparación del micro 1          -> MICRO DETENIDO (a los ~20 s)
pkill -TERM -f simulador.py   # apaga todo ordenadamente (Ctrl+C hace lo mismo)
```
La alerta de **DEMORA** aparece sola cuando un micro llega a una parada con más de 120 s de retraso
(ej.: `python3 micro.py --id 1 --trafico 0.8`, tarda unos 3 minutos y medio).

## Argumentos
- `gateway.py`: `--host`, `--port`, `--sin-cola` (prueba el gateway sin Celery).
- `simulador.py`: `--micros`, `--linea`, `--host`, `--port`, `--intervalo`, `--batch`, `--separacion`.
- `micro.py`: `--id`, `--linea`, `--host`, `--port`, `--intervalo`, `--batch`, `--trafico`, `--averia-en`.

## Umbrales (variables de entorno del worker)
`TW_UMBRAL_KMH=15`, `TW_MIN_LECTURAS=3`, `TW_MIN_MICROS=2`, `TW_DETENIDO_S=15`, `TW_DEMORA_S=120`,
`TW_VENTANA_S=30`, `TW_COOLDOWN_S=60`, `TW_TTL_S=300`. Ejemplo: `TW_UMBRAL_KMH=20 celery -A tareas worker ...`

## Más información
Decisiones de diseño: `INFO.md`. Mejoras futuras: `TODO.md`. Descripción y arquitectura: `doc/`.