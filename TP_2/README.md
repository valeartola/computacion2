# Trabajo Práctico 2 – Scraping y Procesamiento Distribuido Asíncrono
**Materia:** Computación II – Universidad de Mendoza  
**Año:** 2025  
**Autora:** María Valentina Artola  

---

## Descripción General

Este trabajo práctico implementa una **arquitectura distribuida** basada en dos servidores cooperativos:  
- **Servidor A (Scraping Asíncrono):** encargado de la extracción de información HTML desde una URL, utilizando `aiohttp` y `asyncio`.  
- **Servidor B (Procesamiento):** ejecuta tareas pesadas (CPU-bound) en paralelo con `multiprocessing`, procesando imágenes, métricas de rendimiento y capturas de pantalla.  

El objetivo es aplicar los conceptos de **concurrencia**, **asincronía**, **comunicación entre procesos** y **protocolos de red personalizados**, garantizando robustez, modularidad y testeo automatizado.

---
## Arquitectura General

El **Servidor A**:
1. Recibe una solicitud HTTP (`/scrape?url=`).
2. Descarga el HTML y extrae:
   - Título, links, headers H1–H6, imágenes y meta-tags.
3. Envía la información al **Servidor B** mediante un protocolo binario propio (pickle + framing).
4. Consolida la respuesta recibida (resultados de procesamiento) y responde al cliente con un JSON final.

El **Servidor B**:
1. Escucha peticiones TCP de A.  
2. Procesa las tareas en paralelo:
   - Captura de pantalla de la página (`Playwright`).
   - Análisis de rendimiento (`PerformanceProfiler`).
   - Procesamiento de imágenes (`Pillow`, `requests`, `base64`).
3. Devuelve un resultado estructurado al Servidor A.

---
## Instalación y Ejecución

1. **Clonar e ingresar al proyecto:**
   ```bash
    git clone git@github.com:valeartola/computacion2.git   

    cd computacion2

    cd TP_2
2. **Crear entorno virtual y descargar dependencias:**
    ```bash
    python3 -m venv venv

    source venv/bin/activate  

    pip install -r requirements.txt

    playwright install
3. **Ejecutar los servidores:**
    - Servidor B (Procesamiento)
    ```bash
    python server_processing.py -i 127.0.0.1 -p 8001
    ```

    - Servidor A (Scraping Asíncrono)
    ```bash
    python server_scraping.py -i 127.0.0.1 -p 8080 -bip 127.0.0.1 -bport 8001
    ```

4. **Realizar una solicitud de prueba:**
    ```bash
    curl -s "http://127.0.0.1:8080/scrape?url=https://example.com" | jq
    ```

---
## Test
El proyecto incluye 9 tests unitarios con pytest que validan

```bash
PYTHONPATH=. pytest tests/

```
Ejemplo de salida esperada:

==================== 9 passed in 0.75s ====================
