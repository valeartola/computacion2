from PIL import Image
import io
import requests
from typing import List, Optional

def generate_thumbnail_bytes(image_url: str, size=(128, 128)) -> Optional[bytes]:
    """Descarga una imagen, genera un thumbnail optimizado y devuelve sus bytes PNG."""
    try:
        response = requests.get(image_url, stream=True, timeout=10)
        response.raise_for_status()
        
        image = Image.open(io.BytesIO(response.content))
        image.thumbnail(size) 
        
        output = io.BytesIO()
        image.save(output, format="PNG", optimize=True)
        return output.getvalue()
        
    except Exception as e:
        #print(f"Error al procesar imagen {image_url}: {e}")
        return None

def process_page_images(url: str, html_content: str, image_urls: List[str]) -> List[str]:
    """
    Genera thumbnails optimizados para una lista de URLs de imágenes.
    Retorna una lista de strings Base64 de los thumbnails.
    """
    from common.serialization import b64encode_bytes 
    
    thumbnail_list = []
    for img_url in image_urls[:3]: 
        thumb_bytes = generate_thumbnail_bytes(img_url)
        if thumb_bytes:
            thumbnail_list.append(b64encode_bytes(thumb_bytes))
    
    return thumbnail_list

download_and_thumbs = process_page_images