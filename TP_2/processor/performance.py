import requests
import time
from typing import Dict

def analyze_performance(url: str, timeout: int = 20) -> Dict:
    """Calcula el tiempo de carga y tamaño total de recursos (simulado)."""
    start_time = time.time()
    
    try:
        response = requests.get(url, timeout=timeout) 
        response.raise_for_status() 
        
        load_time_ms = int((time.time() - start_time) * 1000)
        
        total_size_kb = len(response.content) / 1024
        
        num_requests = 1 + len(response.history) + 15 
        
        return {
            "load_time_ms": load_time_ms,
            "total_size_kb": round(total_size_kb, 2),
            "num_requests": num_requests
        }
    except requests.RequestException as e:
        print(f"Error de rendimiento al analizar {url}: {e}")
        return {
            "load_time_ms": 0,
            "total_size_kb": 0,
            "num_requests": 0
        }