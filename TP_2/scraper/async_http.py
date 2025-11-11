import asyncio
import aiohttp
from aiohttp import ClientSession, ClientTimeout, ClientError
from typing import Optional

DEFAULT_TIMEOUT = 30

async def fetch_html(url: str) -> Optional[str]:
    """
    Descarga el contenido HTML de una URL de forma asíncrona usando aiohttp.
    Maneja Timeouts y errores HTTP (4xx/5xx).
    """
    try:
        timeout_config = ClientTimeout(total=DEFAULT_TIMEOUT)
        async with ClientSession(timeout=timeout_config) as session:
            async with session.get(url) as response:
                response.raise_for_status() 
                return await response.text()
    
    except asyncio.TimeoutError:
        print(f"[ERROR] Timeout agotado (>{DEFAULT_TIMEOUT}s) al descargar {url}.")
        return None
    except ClientError as e:
        print(f"[ERROR] Error HTTP/Conexión al descargar {url}: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Error inesperado en fetch_html para {url}: {e}")
        return None