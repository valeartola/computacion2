from bs4 import BeautifulSoup
from typing import Dict, List, Tuple

def parse_html_content(html_content: str) -> Tuple[Dict, List[str]]:
    """
    Extrae datos básicos del HTML (título, enlaces, estructura H1-H6) 
    y lista las URLs de imágenes principales.
    """
    try:
        soup = BeautifulSoup(html_content, 'lxml')
    except:
        soup = BeautifulSoup(html_content, 'html.parser')

    title = soup.title.string.strip() if soup.title and soup.title.string else "Sin Título"

    links = [a.get('href') for a in soup.find_all('a', href=True) if a.get('href')]
    

    structure = {f'h{i}': len(soup.find_all(f'h{i}')) for i in range(1, 7)}
    
    image_tags = soup.find_all('img')
    images_count = len(image_tags)
    

    image_urls = [img.get('src') for img in image_tags if img.get('src')]
    
    scraping_data = {
        "title": title,
        "links_count": len(links),
        "links": links[:10],
        "structure": structure,
        "images_count": images_count
    }
    

    return scraping_data, image_urls[:5]