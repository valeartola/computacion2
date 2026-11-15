# TODO: mejoras posibles

## Pendiente del alcance original
- [ ] Dashboard web: una página que muestre las alertas en vivo (Server-Sent Events). Un único hilo suscripto a
      Redis reparte cada alerta a una `Queue` por navegador conectado.
- [ ] Guardar el historial de alertas en una base (SQLite) para consultarlo después.

## Limitaciones conocidas
- La **demora** se detecta al llegar a la parada, no se predice antes.
- Si un micro está desconectado mucho tiempo, su cola de pendientes (`deque(maxlen=100)`, unos 500 s) descarta lo más viejo.
- Al reconectar, el backlog se reenvía con las marcas de tiempo originales: el worker lo procesa, pero las ventanas de 30 s lo descartan.
- Un único tipo de línea (línea 1 con 5 paradas), con tráfico configurable por tramo pero sin mapa real.
- Los umbrales se fijan al iniciar el worker; no se cambian en caliente.

## Ideas futuras
- Contenedores Docker (un servicio por componente con `docker compose`).
- Varias líneas y tramos con horarios distintos.
- Autenticación de los micros en el gateway.
- Predicción de demora a partir de la velocidad actual y la distancia a la próxima parada.
- Pruebas automáticas (pytest) de las reglas del worker.
- Reemplazar el simulador por un cliente real (GPS) usando el mismo protocolo.