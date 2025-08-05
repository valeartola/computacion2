# Trabajo Práctico 1 — Sistema Concurrente de Análisis Biométrico con Blockchain Local

Este sistema simula el procesamiento de datos biométricos en tiempo real usando procesos concurrentes, comunicación mediante `Pipe` y `Queue`, y almacenamiento seguro en una cadena de bloques local.

---

## Archivos del proyecto

| Archivo | Descripción |
|--------|-------------|
| `main.py` | Lanza todos los procesos del sistema |
| `generador.py` | Proceso que genera 60 muestras de datos biométricos |
| `analizadores.py` | Procesos que calculan media y desvío para frecuencia, presión y oxígeno |
| `verificador.py` | Proceso que verifica los resultados y construye la blockchain |
| `verificar_cadena.py` | Script externo que valida la integridad de la cadena y genera un reporte |
| `blockchain.json` | Archivo generado con los bloques encadenados (se crea al ejecutar el sistema) |
| `reporte.txt` | Archivo generado con estadísticas y alertas (se crea al verificar la cadena) |

---

## Instrucciones de ejecución

1. **Clonar el repositorio**

```bash
git clone git@github.com:valeartola/computacion2.git
```

2. **Navegar hasta el directorio del TP**

```bash
cd TP_1
```

3. **Ejecutar el sistema concurrente (genera `blockchain.json`)**

```bash
python3 main.py
```

4. **Verificar la cadena y generar el reporte (genera `reporte.txt`)**

```bash
python3 verificar_cadena.py
```
