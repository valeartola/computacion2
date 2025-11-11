from unittest.mock import patch, MagicMock
import pytest
import io 

from processor.screenshot import capture_screenshot
from processor.performance import analyze_performance
from processor.image_processor import process_page_images
from common.serialization import b64encode_bytes 


@patch('processor.screenshot.sync_playwright') 
def test_capture_screenshot_returns_bytes(mock_playwright):
    """Verifica que la función devuelva el objeto de bytes de la imagen PNG."""
    
    mock_page = MagicMock()
    mock_page.screenshot.return_value = b"bytes_de_imagen_png_mock"
    
    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page
    mock_browser.close.return_value = None
    
    mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser

    url = "https://mock.dev"
    result = capture_screenshot(url) 
    
    assert isinstance(result, bytes)
    assert result == b"bytes_de_imagen_png_mock"
    assert mock_page.screenshot.called 
    assert mock_browser.close.called
    

@patch('processor.performance.requests.get')
@patch('processor.performance.time.time')
def test_analyze_performance_data_format(mock_time, mock_requests_get):
    """Verifica que analyze_performance devuelva el formato y la conversión de unidades correcta (ms y KB)."""
    
    mock_time.side_effect = [100.0, 100.5] 

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'A' * 1024000 
    mock_resp.history = [] 
    mock_resp.raise_for_status = MagicMock() 
    
    mock_requests_get.return_value = mock_resp

    url = "http://test.com"
    result = analyze_performance(url)
    
    assert result["load_time_ms"] == 500 
    assert result["total_size_kb"] == pytest.approx(1000.0, 0.1) 
    assert result["num_requests"] == 1 + 0 + 15 
    
    

@patch('processor.image_processor.requests.get')
@patch('processor.image_processor.Image.open')
@patch('common.serialization.b64encode_bytes')
def test_process_page_images(mock_b64encode, mock_image_open, mock_requests_get):
    """Verifica la lógica de descarga, redimensionamiento y codificación para los thumbnails."""
    
    mock_response = mock_requests_get.return_value
    mock_response.status_code = 200
    mock_response.content = b'fake_image_bytes'
    
    mock_img = mock_image_open.return_value
    mock_img.thumbnail.return_value = None 
    
    def mock_save(fp, format, optimize):
        fp.write(b'thumbnail_bytes')
        
    mock_img.save = mock_save
    
    mock_b64encode.side_effect = lambda b: f"base64_{b.decode('utf-8')}_test"
    
    url = "http://test.com"
    image_urls = ["http://test.com/img1.jpg", "http://test.com/img2.png"]
    
    result = process_page_images(url, "<html>", image_urls)
    
    assert isinstance(result, list)
    assert len(result) == 2 
    
    assert result == ["base64_thumbnail_bytes_test", "base64_thumbnail_bytes_test"]
    assert mock_requests_get.call_count == 2


@patch('processor.image_processor.requests.get', side_effect=Exception("Error de red simulado"))
@patch('common.serialization.b64encode_bytes') 
def test_process_page_images_handles_errors(mock_b64encode, mock_get):
    """Verifica que la función maneje excepciones durante la descarga de imágenes."""
    
    url = "http://test.com"
    image_urls = ["http://test.com/img1.jpg", "http://test.com/img2.png"]
    
    result = process_page_images(url, "<html>", image_urls)
    
    assert isinstance(result, list)
    assert len(result) == 0