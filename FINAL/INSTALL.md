# Instalación

Pensado para Linux. En Windows se usa **WSL2 con Ubuntu**, porque Redis no corre de forma nativa,
Celery tiene problemas en Windows y las señales USR1/USR2 no existen allí.

## 1. Requisitos
- Python 3.10 o superior
- Redis (servidor)
- Git

## 2. Clonar
```
git clone https://github.com/valeartola/computacion2.git
cd computacion2/FINAL
```

## 3. Entorno virtual y dependencias
```
python3 -m venv ~/venvs/tw
source ~/venvs/tw/bin/activate
pip install -r requirements.txt
```
(Si falla `venv`: `sudo apt install python3-venv`. Si Celery pide `packaging`: `pip install packaging`.)

## 4. Redis
```
sudo apt install redis-server
sudo service redis-server start
redis-cli ping            # debe responder PONG
```
Por defecto se usa `redis://localhost:6379/0`; se cambia con la variable `REDIS_URL`.

## 5. Ejecutar
Abrir una terminal de Ubuntu por componente (con el venv activado, dentro de la carpeta del proyecto)
y seguir la tabla de `README.md`. Orden recomendado: Redis, worker, suscriptor, gateway, simulador.

Si el proyecto está en una carpeta de Windows, desde Ubuntu queda en `/mnt/c/Users/<usuario>/...`.

## 6. Verificar
Con todo corriendo, `pkill -USR1 -f simulador.py` debe producir en el suscriptor, en unos 30 segundos,
una alerta `CONGESTION`.