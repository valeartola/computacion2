import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch 
from aiohttp import ClientError

from scraper.async_http import fetch_html
from scraper.html_parser import parse_html_content
from scraper.metadata_extractor import extract_meta_tags

TEST_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Título de la Página de Prueba</title>
    <meta name="description" content="Una descripción para SEO.">
    <meta name="keywords" content="prueba, test, tp2">
    <meta property="og:title" content="Título OG">
</head>
<body>
    <h1>Header Principal</h1>
    <h2>Subtítulo 1</h2>
    <h2>Subtítulo 2</h2>
    <a href="/link1">Link Local</a>
    <a href="https://externo.com/link2">Link Externo</a>
    <img src="imagen1.jpg" alt="Imagen 1">
    <img src="/imagen2.png" alt="Imagen 2">
</body>
</html>
"""



def test_parse_html_content_ok():
    """Verifica que parse_html_content devuelva correctamente los datos de scraping y las URLs de imagen."""
    scraping_data, image_urls = parse_html_content(TEST_HTML)

    assert scraping_data["title"] == "Título de la Página de Prueba"
    assert scraping_data["links_count"] == 2
    assert set(scraping_data["links"]) == {"/link1", "https://externo.com/link2"}
    assert scraping_data["images_count"] == 2
    assert scraping_data["structure"] == {"h1": 1, "h2": 2, "h3": 0, "h4": 0, "h5": 0, "h6": 0}

    assert image_urls == ["imagen1.jpg", "/imagen2.png"]

def test_extract_meta_tags_ok():
    """Verifica que extract_meta_tags reciba un string HTML y extraiga las metas correctas."""
    meta = extract_meta_tags(TEST_HTML)
    assert meta["description"] == "Una descripción para SEO."
    assert meta["keywords"] == "prueba, test, tp2"
    assert meta["og:title"] == "Título OG"


@pytest.mark.asyncio
@patch("scraper.async_http.ClientSession")
async def test_fetch_html_success(MockClientSession):
    """Verifica el caso exitoso donde se retorna el HTML."""
    
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock() 
    mock_resp.text = AsyncMock(return_value=TEST_HTML)

    mock_get_cm = MagicMock()
    mock_get_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_get_cm.__aexit__ = AsyncMock(return_value=None)
    
    mock_session = MagicMock() 
    mock_session.get.return_value = mock_get_cm
    
    mock_client_session_cm = MagicMock()
    mock_client_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_client_session_cm.__aexit__ = AsyncMock(return_value=None)

    MockClientSession.return_value = mock_client_session_cm

    html = await fetch_html("http://test.com") 
    assert html == TEST_HTML

@pytest.mark.asyncio
@patch("scraper.async_http.ClientSession")
async def test_fetch_html_timeout_returns_none(MockClientSession):
    """Verifica que ante un TimeoutError se retorna None."""
    
    async def _raise_timeout(*a, **k): 
        raise asyncio.TimeoutError
    
    mock_get_cm = MagicMock()
    mock_get_cm.__aenter__ = AsyncMock(side_effect=_raise_timeout)
    mock_get_cm.__aexit__ = AsyncMock(return_value=None)
    
    mock_session = MagicMock() 
    mock_session.get.return_value = mock_get_cm

    mock_client_session_cm = MagicMock()
    mock_client_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_client_session_cm.__aexit__ = AsyncMock(return_value=None)
    
    MockClientSession.return_value = mock_client_session_cm

    html = await fetch_html("http://test.com")
    assert html is None 

@pytest.mark.asyncio
@patch("scraper.async_http.ClientSession")
async def test_fetch_html_clienterror_returns_none(MockClientSession):
    """Verifica que ante un ClientError (ej. DNS, conexión) se retorna None."""
    
    async def _raise_clienterror(*a, **k): 
        raise ClientError 
        
    mock_get_cm = MagicMock()
    mock_get_cm.__aenter__ = AsyncMock(side_effect=_raise_clienterror)
    mock_get_cm.__aexit__ = AsyncMock(return_value=None)
    
    mock_session = MagicMock() 
    mock_session.get.return_value = mock_get_cm
    
    mock_client_session_cm = MagicMock()
    mock_client_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_client_session_cm.__aexit__ = AsyncMock(return_value=None)
    
    MockClientSession.return_value = mock_client_session_cm

    html = await fetch_html("http://test.com")
    assert html is None