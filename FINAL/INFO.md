# Decisiones de diseño y justificación

## Visión general
Pipeline de eventos: **micros -> gateway -> cola -> workers -> alertas**. Cada etapa se desacopla de la siguiente
con una cola o un canal, para que una etapa lenta o caída no frene a las demás.

## Por qué cada tecnología
| Decisión | Por qué sí | Por qué no la alternativa |
|---|---|---|
| **Micros como hilos** (`threading`) | Casi todo su tiempo esperan I/O (dormir entre lecturas, esperar el ACK). Un hilo es barato y alcanza. | Un proceso por micro gasta memoria y CPU sin necesidad; con I/O el GIL no molesta. |
| **Gateway con asyncio** | Atiende muchos clientes TCP conectados a la vez con un solo hilo; cada conexión espera casi todo el tiempo. | Un hilo o proceso por cliente escala peor; asyncio es el caso típico de "muchas conexiones, poco trabajo". |
| **Workers como procesos** (Celery prefork) | El análisis es trabajo de CPU: procesos reales usan varios núcleos sin el GIL. | Hilos no darían paralelismo real en cálculo. |
| **Cola de tareas** (Celery + Redis) | El gateway responde enseguida y no se bloquea analizando; si hay más carga, se suman workers. | Procesar dentro del gateway lo haría lento y haría perder datos si se cae. |
| **Sesión TCP persistente** | Menos costo que reconectar por cada lote, y permite el ACK. | Una conexión por mensaje es más lenta y no tiene "sesión". |
| **Framing con prefijo de 4 bytes + JSON** | TCP es un flujo de bytes sin límites de mensaje; el largo permite saber dónde termina cada uno. | Separar por salto de línea falla si el JSON lo contiene; sin framing los mensajes se mezclan. |
| **ACK + reintento** | El micro no descarta un lote hasta que el gateway confirma que lo encoló. | Sin ACK un corte de red perdería datos sin que nadie se entere. |
| **Redis para el historial reciente** | Los workers no guardan memoria entre tareas y cualquiera puede tomar la siguiente; el estado compartido tiene que estar afuera. | Memoria local de cada worker daría resultados distintos según quién tome la tarea. |

## Protocolo de sesión
- El gateway cierra una sesión inactiva a los 10 s; el micro espera el ACK 2 s.
- El micro se reconecta con espera creciente (1, 2, 4... hasta 10 s) y reenvía en orden los lotes sin confirmar.
- El gateway descarta duplicados por `(micro_id, n° de lote)`. El micro manda un `uuid` de sesión en el "hola": si cambia (el micro se reinició), el gateway reinicia su contador.
- El gateway envía el ACK solo si logró encolar; si no, el micro reenvía.

## Ventanas en Redis
- Un *sorted set* por tramo (`ventana:tramo:{id}`, para congestión) y uno por micro (`ventana:micro:{id}`, para detenido).
- El *score* es la hora de la lectura: Redis las mantiene ordenadas aunque los lotes lleguen desordenados.
- El *member* es la lectura en JSON con claves ordenadas: si un lote llega dos veces no se duplica (idempotente).
- Se recorta a 30 s (`ZREMRANGEBYSCORE`) relativo a la lectura más nueva, no al reloj del worker. Además cada clave tiene `EXPIRE` de 300 s, así que lo que nadie usa se borra solo.

## Reglas de alerta
- **Congestión**: promedio de velocidad de las lecturas en marcha (sin paradas) del tramo, menor a 15 km/h, con al menos 3 lecturas **de al menos 2 micros distintos**. Un solo micro roto es una avería, no un embotellamiento.
- **Micro detenido**: velocidad 0 en la misma posición, fuera de parada, durante al menos 15 s.
- **Demora**: llegada a una parada más de 120 s después del horario previsto.
- **Cooldown**: la misma alerta no se repite antes de 60 s. Se logra con `SET alerta:... NX EX 60`, que es atómico: si dos workers detectan lo mismo a la vez, solo uno publica.

## Sincronización e IPC usados
- **Señales** (`SIGUSR1`, `SIGUSR2`, `SIGTERM`): comunican otro proceso (la terminal del usuario) con el simulador. El handler solo anota el evento en una `Queue` y el hilo principal lo atiende.
- **`queue.Queue`**: el simulador manda órdenes ("averiar", "reparar") a cada micro (comunicación entre hilos).
- **`threading.Lock`**: protege el nivel de tráfico compartido (`Trafico`), que leen todos los micros y escribe el simulador.
- **`threading.Event`**: `averiado` hace que el micro se quede quieto; `detener` pide que termine y además sirve de espera interrumpible entre lecturas.
- **Redis pub/sub**: canal `alertas` entre workers y suscriptor.
- **Redis como broker** (cola de tareas) entre gateway y workers.
- **`SET NX`**: exclusión mutua distribuida para el cooldown.

## Limitaciones asumidas
Ver `TODO.md`.