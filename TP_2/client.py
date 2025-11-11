import aiohttp
import asyncio
import argparse
import json
import time

async def run_client(url: str, server_ip: str, server_port: int):
    """Envía una solicitud al Servidor A y muestra la respuesta."""
    full_url = f"http://{server_ip}:{server_port}/scrape?url={url}"
    
    print(f"Enviando solicitud al Servidor A: {full_url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            async with session.get(full_url, timeout=200) as response:
                end_time = time.time()
                
                print(f"Tiempo total de respuesta: {end_time - start_time:.2f} segundos")
                
                try:
                    data = await response.json()
                except aiohttp.ContentTypeError:
                    text = await response.text()
                    print(f"\n--- Respuesta No-JSON (Status {response.status}) ---")
                    print(text)
                    return
                
                print(f"\n--- Respuesta Consolidada del Servidor A (Status {response.status}) ---")
                
                print(json.dumps(data, indent=4))
                
                if response.status == 200:
                    print(f"\n Análisis exitoso (Estado Interno: {data.get('status')})")
                else:
                    print(f"\n Error o Fallo Parcial. Status HTTP: {response.status}")
                    
    except aiohttp.ClientConnectorError:
        print(f" Error de conexión: El Servidor A no está corriendo en {server_ip}:{server_port}")
    except asyncio.TimeoutError:
        print(" Tiempo de espera agotado (Timeout) del cliente.")
    except Exception as e:
        print(f" Ocurrió un error inesperado: {e}")

def main():
    parser = argparse.ArgumentParser(description="Cliente de Prueba del Sistema de Scraping Distribuido")
    parser.add_argument('url', help="URL a analizar (ej: https://www.google.com)")
    parser.add_argument('-i', '--ip', default="127.0.0.1", help="IP del Servidor A (default: 127.0.0.1)")
    parser.add_argument('-p', '--port', type=int, default=8080, help="Puerto del Servidor A (default: 8080)")
    args = parser.parse_args()

    asyncio.run(run_client(args.url, args.ip, args.port))

if __name__ == "__main__":
    main()