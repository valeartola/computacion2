# Propuesta: TrafficWatch

**Materia:** Computación II · **Alumna:** Mechi Artola

## 1. Problema que resuelve
Quien administra una línea de micros necesita enterarse rápido de tres cosas: que un tramo está congestionado,
que un micro quedó parado fuera de una parada, o que un micro llega mucho más tarde de lo previsto.
TrafficWatch simula la flota y detecta esas situaciones en tiempo real.

## 2. Descripción verbal
Cada micro (cliente) mide su posición y velocidad una vez por segundo y manda lotes de 5 lecturas, por una
conexión TCP que se mantiene abierta, a un gateway (servidor). El gateway valida el lote, lo deja en una cola de
tareas distribuida y responde con un ACK. Varios workers (procesos) toman los lotes, guardan las lecturas
recientes en Redis y aplican las reglas. Si una se cumple, publican una alerta en un canal y un suscriptor la muestra.
Un simulador crea los micros (hilos) y permite provocar situaciones con señales del sistema operativo.

- **Concurrencia:** micros como hilos; gateway con asyncio (muchos clientes a la vez).
- **Paralelismo:** workers como procesos (Celery).
- **Comunicación asincrónica:** gateway -> workers por cola (Celery sobre Redis); workers -> suscriptor por pub/sub.

## 3. Arquitectura
Ver `arquitectura.png`.

```
simulador -> micros (hilos) --TCP + ACK--> gateway (asyncio) --Celery--> Redis --> workers (procesos)
workers <--> Redis (ventanas de 30 s)        workers --pub/sub "alertas"--> suscriptor
```

## 4. Entidades y funcionalidades
| Entidad | Qué hace |
|---|---|
| Simulador | Crea N micros como hilos; recibe señales (USR1 tráfico, USR2 avería, TERM apagar) y las convierte en cambios de tráfico y órdenes a los micros. |
| Micro | Avanza por la ruta, se detiene en las paradas, arma lotes, espera el ACK, se reconecta con espera creciente y reenvía lo no confirmado. |
| Gateway | Acepta muchos micros con asyncio, valida y deduplica lotes, los encola sin bloquear, responde ACK solo si encoló, cierra sesiones inactivas a los 10 s. |
| Worker | Guarda lecturas en ventanas de Redis, recorta a 30 s, evalúa las reglas y publica alertas con cooldown atómico. |
| Redis | Broker de la cola, ventanas de lecturas y canal de alertas. |
| Suscriptor | Imprime las alertas. (Dashboard web previsto, ver TODO.md.) |

## 5. Reglas de detección
- **Congestión:** velocidad promedio del tramo menor a 15 km/h, con al menos 3 lecturas de 2 o más micros distintos.
- **Micro detenido:** velocidad 0 en la misma posición, fuera de parada, 15 s o más.
- **Demora:** llegada a una parada más de 120 s después del horario previsto.

## 6. Sincronización e IPC
Señales (IPC entre procesos), `queue.Queue` (entre hilos), `Lock` (tráfico compartido), `Event` (avería y apagado),
Redis pub/sub y cola de Celery (entre procesos), `SET NX` (exclusión mutua distribuida para el cooldown).
Las justificaciones están en `INFO.md`.

## 7. Requisitos de la cátedra cubiertos
| Requisito | Cómo se cumple |
|---|---|
| Sockets con clientes múltiples concurrentes | Gateway asyncio con varios micros conectados |
| IPC | Señales, colas, Redis pub/sub |
| I/O asincrónico | asyncio en el gateway |
| Cola de tareas distribuida | Celery + Redis |
| Argumentos por línea de comandos | `argparse` en gateway, micro y simulador |
| Opcionales | Celery (sí); dashboard web, base de datos y Docker (ver `TODO.md`) |

## 8. Cambios respecto de la primera versión
Los micros pasaron de procesos a hilos (casi solo esperan I/O); se agregó sesión abierta con ACK y reenvío; el
historial de los workers vive en Redis con ventanas de 30 s y expiración; la congestión exige 2 micros distintos.