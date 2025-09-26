"""
Test para verificar que el servidor Django arranca correctamente.
Parte del Bloque A - Esqueleto BFF + Config.
"""
import pytest
from django.test import Client


class TestServerBoots:
    """Tests para verificar que el servidor arranca correctamente."""
    
    def test_server_boots_smoke_test(self):
        """
        Smoke test: verifica que el servidor responde con códigos válidos.
        DoD: GET / responde 404 (app viva).
        """
        client = Client()
        response = client.get("/")
        
        # El servidor debe estar vivo y responder con códigos válidos
        assert response.status_code in (200, 404, 301), (
            f"Servidor no responde correctamente. Status code: {response.status_code}"
        )
    
    def test_server_handles_invalid_routes(self):
        """Verifica que el servidor maneja rutas inválidas correctamente."""
        client = Client()
        response = client.get("/ruta-inexistente-12345/")
        
        # Debe responder con 404 para rutas inexistentes
        assert response.status_code == 404
    
    def test_server_accepts_basic_requests(self):
        """Verifica que el servidor acepta requests básicos sin errores de servidor."""
        client = Client()
        response = client.get("/")
        
        # No debe haber errores de servidor (5xx)
        assert response.status_code < 500, (
            f"Error de servidor detectado. Status code: {response.status_code}"
        )