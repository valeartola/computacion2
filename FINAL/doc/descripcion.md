# TrafficWatch: descripción

## Descripción verbal
TrafficWatch es una aplicación cliente-servidor que monitorea micros simulados. Cada micro (cliente) mide su
posición y velocidad una vez por segundo y manda lotes de 5 lecturas por una conexión TCP persistente a un
gateway (servidor). El gateway valida cada lote, lo deja en una cola de tareas distribuida y le responde al micro con un ACK. Varios workers, en procesos distintos, toman los lotes de la cola, guardan las lecturas recientes en Redis y aplican tres reglas: congestión, micro detenido y demora. Cuando una se cumple, el worker publica una alerta en un canal de Redis y un suscriptor la muestra.

Se usa **concurrencia** en los micros (hilos) y en el gateway (asyncio, muchos clientes a la vez), **paralelismo** en los workers (procesos) y **comunicación asincrónica** entre el gateway y los workers (cola Celery sobre Redis) y entre los workers y el suscriptor (pub/sub).

## Arquitectura
Ver `arquitectura.png` en esta carpeta.

```
simulador --(Queue / señales)--> micros (hilos)
micros --TCP + ACK--> gateway (asyncio)
gateway --Celery .delay--> Redis (broker) --> workers (procesos)
workers <--> Redis (ventanas)
workers --pub/sub "alertas"--> suscriptor
```

## Funcionalidades por entidad
**Simulador** (`simulador.py`): crea N micros como hilos, escalonando su salida; recibe señales del usuario (USR1: alterna tráfico, USR2: alterna avería, TERM/INT: apagar) y las traduce en cambios de tráfico y órdenes a los micros; apaga todo ordenadamente.

**Micro** (`micro.py`): avanza por la ruta según el tráfico del tramo, se detiene diez segundos en cada parada, arma lotes de lecturas, los envía y espera el ACK, se reconecta con espera creciente y reenvía lo que no fue confirmado, y obedece órdenes de avería y reparación.

**Gateway** (`gateway.py`): acepta muchos micros a la vez con asyncio, lee mensajes con prefijo de largo, valida los lotes, descarta duplicados, los encola en Celery sin bloquear, responde ACK solo si encoló, y cierra sesiones inactivas a los 10 s.

**Worker** (`tareas.py`): guarda las lecturas en dos ventanas de Redis (por tramo y por micro), recorta a 30 s, evalúa las tres reglas y publica alertas con cooldown atómico de 60 s.

**Redis**: broker de Celery, almacén de las ventanas y canal de alertas.

**Suscriptor** (`suscriptor.py`): se suscribe al canal `alertas` y las imprime con su hora. Lo reemplazará el dashboard web (ver `TODO.md`).

**Configuración y protocolo** (`config.py`, `protocolo.py`): la línea, las paradas, los horarios previstos y el tráfico compartido; y el formato de los mensajes (4 bytes de largo + JSON).