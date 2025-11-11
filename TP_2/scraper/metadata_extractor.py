from bs4 import BeautifulSoup
from typing import Dict

def extract_meta_tags(html_content: str) -> Dict:
    """Extrae meta tags relevantes (description, keywords, Open Graph tags)."""
    
    try:
        soup = BeautifulSoup(html_content, 'lxml')
    except:
        soup = BeautifulSoup(html_content, 'html.parser')
        
    meta_tags = {}
    
    for tag in soup.find_all('meta'):
        name = tag.get('name')
        content = tag.get('content')
        property_tag = tag.get('property')
        
        if name in ['description', 'keywords'] and content:
            meta_tags[name] = content
            
        if property_tag and property_tag.startswith('og:') and content:
            meta_tags[property_tag] = content

    return meta_tags