"""
Test para verificar configuración CORS con preflight requests.
Parte del Bloque A - Esqueleto BFF + Config.
"""
import pytest
from django.test import Client
from django.conf import settings
import os


class TestCORSPreflight:
    """Tests para verificar configuración CORS."""
    
    def test_cors_preflight_from_fe_origin(self):
        """
        Test CORS preflight desde FE_ORIGIN.
        DoD: Preflight CORS a /api/v1/b2b/v1/version no es bloqueado desde FE.
        """
        client = Client()
        fe_origin = os.environ.get('FE_ORIGIN', 'http://localhost:5173')
        
        response = client.options(
            "/api/v1/b2b/v1/version",
            HTTP_ORIGIN=fe_origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET"
        )
        
        # Debe permitir el origen del FE
        assert response.get('Access-Control-Allow-Origin') == fe_origin, (
            f"CORS no configurado correctamente para {fe_origin}. "
            f"Header recibido: {response.get('Access-Control-Allow-Origin')}"
        )
    
    def test_cors_preflight_allows_get_method(self):
        """Verifica que CORS permite método GET."""
        client = Client()
        fe_origin = os.environ.get('FE_ORIGIN', 'http://localhost:5173')
        
        response = client.options(
            "/api/v1/b2b/v1/version",
            HTTP_ORIGIN=fe_origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET"
        )
        
        allowed_methods = response.get('Access-Control-Allow-Methods', '')
        assert 'GET' in allowed_methods, (
            f"Método GET no permitido en CORS. Métodos permitidos: {allowed_methods}"
        )
    
    def test_cors_preflight_allows_common_headers(self):
        """Verifica que CORS permite headers comunes."""
        client = Client()
        fe_origin = os.environ.get('FE_ORIGIN', 'http://localhost:5173')
        
        response = client.options(
            "/api/v1/b2b/v1/version",
            HTTP_ORIGIN=fe_origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="Content-Type,Authorization"
        )
        
        # Debe responder sin error (no necesariamente 200, puede ser 204)
        assert response.status_code in (200, 204), (
            f"Preflight request falló. Status code: {response.status_code}"
        )
    
    def test_cors_blocks_unauthorized_origin(self):
        """Verifica que CORS bloquea orígenes no autorizados."""
        client = Client()
        unauthorized_origin = "http://malicious-site.com"
        
        response = client.options(
            "/api/v1/b2b/v1/version",
            HTTP_ORIGIN=unauthorized_origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET"
        )
        
        # No debe incluir el origen malicioso en la respuesta
        allowed_origin = response.get('Access-Control-Allow-Origin')
        assert allowed_origin != unauthorized_origin, (
            f"CORS permite origen no autorizado: {unauthorized_origin}"
        )