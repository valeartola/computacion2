from playwright.sync_api import sync_playwright
import time
from typing import Optional

def capture_screenshot(url: str, timeout: int = 30) -> Optional[bytes]:
    """
    Genera una imagen (PNG) de la página web renderizada usando Playwright.
    Retorna los bytes binarios de la imagen.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(url, timeout=timeout * 1000, wait_until="networkidle") 
            
            screenshot_bytes = page.screenshot(type="png", full_page=True)
            
            browser.close()
            return screenshot_bytes
            
    except Exception as e:
        print(f"Error al generar screenshot de {url}: {e}")
        return b'' 
    
make_screenshot_stub = capture_screenshot