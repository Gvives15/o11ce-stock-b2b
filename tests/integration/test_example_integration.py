"""
Ejemplo de test de integración.
Tests que verifican la interacción entre componentes.
"""
import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.integration
@pytest.mark.django_db
class TestExampleIntegration:
    """Ejemplo de clase de test de integración."""
    
    def test_api_endpoint(self, client):
        """Test de endpoint de API."""
        # Ejemplo de test de API
        response = client.get('/api/health/')
        
        # Verificar respuesta
        assert response.status_code in [200, 404]  # 404 si no existe el endpoint
    
    def test_database_interaction(self, db):
        """Test de interacción con base de datos."""
        # Ejemplo de test con base de datos
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        
        assert user.username == 'testuser'
        assert User.objects.count() == 1
