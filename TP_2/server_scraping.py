import argparse
import asyncio
from aiohttp import web

from scraper.async_http import fetch_html
from scraper.html_parser import parse_html_content
from scraper.metadata_extractor import extract_meta_tags
from common.protocol import encode_message, decode_message


PROCESSING_SERVER_IP = "127.0.0.1" 
PROCESSING_SERVER_PORT = 8001      
TIMEOUT_PROCESSING_REQUEST = 150   


async def request_processing(url: str, html_content: str, image_urls: list) -> dict:
    """
    Establece una conexión TCP asíncrona con el Servidor B,
    envía la tarea y espera el resultado binario.
    """
    
    request_data = {
        "url": url,
        "html_content": html_content,
        "image_urls": image_urls
    }
    
    message_to_send = encode_message(request_data)
    data_buffer = b''
    
    try:
        reader, writer = await asyncio.open_connection(
            PROCESSING_SERVER_IP, PROCESSING_SERVER_PORT
        )
        
        writer.write(message_to_send)
        await writer.drain() 

        while True:
            data = await asyncio.wait_for(reader.read(8192), timeout=TIMEOUT_PROCESSING_REQUEST)
            
            if not data:
                break 
            
            data_buffer += data
            
            result_response, data_buffer = decode_message(data_buffer)
            
            if result_response is not None:
                writer.close()
                await writer.wait_closed()
                return result_response 
            
        writer.close()
        await writer.wait_closed()
        return {"status": "error", "message": "Servidor B cerró la conexión antes de respuesta completa (Error de Protocolo)."}

    except asyncio.TimeoutError:
        print(f"[ERROR] Timeout: El Servidor B tardó más de {TIMEOUT_PROCESSING_REQUEST}s en responder.")
        return {"status": "error", "message": "Timeout agotado. El Servidor B tardó demasiado en responder."}
    except ConnectionRefusedError:
        print(f"[ERROR] Conexión rechazada: Servidor B no está corriendo en {PROCESSING_SERVER_IP}:{PROCESSING_SERVER_PORT}")
        return {"status": "error", "message": "Conexión rechazada. Asegúrate de que el Servidor B esté corriendo."}
    except Exception as e:
        print(f"[ERROR] Error inesperado de comunicación con Servidor B: {e.__class__.__name__}: {e}")
        return {"status": "error", "message": f"Error inesperado de comunicación con Servidor B: {e.__class__.__name__}"}



async def scrape_handler(request):
    """Maneja la solicitud HTTP principal del cliente: orquestación."""
    
    url = request.query.get('url')
    if not url:
        return web.json_response(
            {"status": "error", "message": "Parámetro 'url' no encontrado en la solicitud."}, 
            status=400
        )
    
    print(f"\n[INFO] Iniciando solicitud para: {url}")
    
    html_content = await fetch_html(url)
    
    if not html_content:
        return web.json_response(
            {"status": "error", "message": f"Fallo al obtener el HTML de {url}."}, 
            status=500
        )

    scraping_data, image_urls = parse_html_content(html_content)
    meta_data = extract_meta_tags(html_content)
    
    final_data = {
        "url": url,
        "scraping_result": {**scraping_data, "meta_tags": meta_data},
        "processing_result": {}
    }

    print(f"[INFO] Enviando tarea de procesamiento a Servidor B: {url}")
    processing_response = await request_processing(url, html_content, image_urls)
    
    final_data["processing_result"] = processing_response
    
    if processing_response.get("status") == "error":
        status_code = 503 
    else:
        status_code = 200

    print(f"[INFO] Finalizada solicitud para: {url} con status HTTP {status_code}")
    return web.json_response(final_data, status=status_code)


def parse_args():
    """Configuración de argumentos de línea de comandos para el Servidor A."""
    parser = argparse.ArgumentParser(description="Servidor de Extracción Asíncrono (A)")
    parser.add_argument('-i', '--ip', default="0.0.0.0", help="Dirección de escucha del Servidor A")
    parser.add_argument('-p', '--port', type=int, default=8080, help="Puerto de escucha del Servidor A")
    parser.add_argument('-bip', '--b_ip', default="127.0.0.1", help="IP del Servidor de Procesamiento (B)")
    parser.add_argument('-bport', '--b_port', type=int, default=8001, help="Puerto del Servidor de Procesamiento (B)")
    return parser.parse_args()

def main():
    global PROCESSING_SERVER_IP, PROCESSING_SERVER_PORT
    args = parse_args()
    
    PROCESSING_SERVER_IP = args.b_ip
    PROCESSING_SERVER_PORT = args.b_port

    app = web.Application()
    app.add_routes([
        web.get('/scrape', scrape_handler),
    ])

    print("--- Servidor de Extracción Asíncrono (A) ---")
    print(f"URL de escucha: http://{args.ip}:{args.port}/scrape?url=...")
    print(f"Coordinando con Servidor B en {args.b_ip}:{args.b_port}\n")
    
    try:
        web.run_app(app, host=args.ip, port=args.port)
    except Exception as e:
        print(f"Error al iniciar el servidor aiohttp: {e}")

if __name__ == '__main__':
    main()