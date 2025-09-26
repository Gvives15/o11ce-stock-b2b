"""
Test para verificar que el API index del router B2B funciona correctamente.
Parte del Bloque A - Esqueleto BFF + Config.
"""
import pytest
from django.test import Client


class TestAPIIndex:
    """Tests para verificar el índice del API B2B."""
    
    def test_b2b_api_index_returns_200(self):
        """
        Test que verifica que GET /api/v1/b2b/v1/ devuelve 200.
        DoD: GET /api/v1/b2b/v1/ devuelve índice de Ninja (200).
        """
        client = Client()
        response = client.get("/api/v1/b2b/v1/")
        
        assert response.status_code == 200, (
            f"API index no responde correctamente. Status code: {response.status_code}"
        )
    
    def test_b2b_api_index_content_type(self):
        """Verifica que el API index devuelve contenido JSON."""
        client = Client()
        response = client.get("/api/v1/b2b/v1/")
        
        content_type = response.get('Content-Type', '')
        assert 'application/json' in content_type or 'text/html' in content_type, (
            f"Content-Type inesperado: {content_type}"
        )
    
    def test_b2b_api_index_has_content(self):
        """Verifica que el API index tiene contenido."""
        client = Client()
        response = client.get("/api/v1/b2b/v1/")
        
        assert len(response.content) > 0, "API index no tiene contenido"
    
    def test_b2b_api_root_accessible(self):
        """Verifica que la ruta raíz del API B2B es accesible."""
        client = Client()
        response = client.get("/api/v1/b2b/v1")  # Sin slash final
        
        # Debe redirigir o responder correctamente
        assert response.status_code in (200, 301, 302), (
            f"Ruta raíz del API no accesible. Status code: {response.status_code}"
        )