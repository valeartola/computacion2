import argparse
import json
import socketserver
import multiprocessing as mp
import time

from common.protocol import encode_message, decode_message 

from processor.screenshot import capture_screenshot
from processor.performance import analyze_performance
from processor.image_processor import process_page_images
from common.serialization import b64encode_bytes

POOL: mp.Pool = None
TIMEOUT_PROCESSING = 120 


def process_task(url: str, html_content: str, image_urls: list) -> dict:
    """Función que ejecuta todas las tareas CPU-bound en un proceso separado."""
    print(f"Procesando tareas para: {url} en {mp.current_process().pid}")
    
    try:
        screenshot_bytes = capture_screenshot(url)
        screenshot_b64 = b64encode_bytes(screenshot_bytes)
        
        performance_data = analyze_performance(url)
        
        thumbnails_b64 = process_page_images(url, html_content, image_urls)
        
        return {
            "status": "success",
            "result": {
                "screenshot": screenshot_b64, 
                "performance": performance_data,
                "thumbnails": thumbnails_b64,
            }
        }
    except Exception as e:
        print(f"Error en el worker para {url}: {e}")
        return {"status": "error", "message": f"Fallo al procesar en worker: {e.__class__.__name__}"}


class ProcessingHandler(socketserver.BaseRequestHandler):
    
    def handle(self):
        data_buffer = b''
        
        while True:
            try:
                received_data = self.request.recv(8192) 
                if not received_data:
                    break 
                
                data_buffer += received_data
                
                task_request, data_buffer = decode_message(data_buffer)
                
                if task_request is None:
                    continue
                
                url = task_request.get("url")
                html_content = task_request.get("html_content")
                image_urls = task_request.get("image_urls", [])

                print(f"Solicitud recibida para: {url}")

                future_result = POOL.apply_async(process_task, args=(url, html_content, image_urls))
                
                try:
                    result = future_result.get(timeout=TIMEOUT_PROCESSING) 
                except mp.TimeoutError:
                    result = {"status": "error", "message": f"Procesamiento excedió el tiempo límite ({TIMEOUT_PROCESSING}s)."}
                    
                response_message = encode_message(result)
                self.request.sendall(response_message)
                
                break 

            except Exception as e:
                print(f"Error de manejo de socket/protocolo: {e}")
                error_response = encode_message({"status": "error", "message": f"Error de socket: {e}"})
                self.request.sendall(error_response)
                break


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Servidor TCP que usa un hilo por cada nueva conexión."""
    allow_reuse_address = True
    daemon_threads = True

def main():
    global POOL
    
    parser = argparse.ArgumentParser(description="Servidor de Procesamiento Distribuido")
    parser.add_argument("-i", "--ip", required=True, help="Dirección de escucha")
    parser.add_argument("-p", "--port", required=True, type=int, help="Puerto de escucha")
    parser.add_argument(
        "-n", "--processes", default=mp.cpu_count(), type=int, 
        help=f"Número de procesos en el pool (default: {mp.cpu_count()})"
    )
    args = parser.parse_args()

    print(f"Inicializando Pool de {args.processes} procesos para tareas CPU-bound.")
    POOL = mp.Pool(args.processes)

    server_address = (args.ip, args.port)
    with ThreadedTCPServer(server_address, ProcessingHandler) as server:
        print(f"Servidor B escuchando en {args.ip}:{args.port} con {args.processes} workers.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nCerrando servidor por interrupción del usuario...")
        except Exception as e:
            print(f"Error fatal del servidor: {e}")
        finally:
            print("Cerrando Pool de Procesos...")
            POOL.terminate()
            POOL.join()

if __name__ == "__main__":
    main()