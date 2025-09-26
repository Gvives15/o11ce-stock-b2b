"""
Tests para verificar los endpoints de salud del sistema.
Estos tests verifican que los endpoints /health/live y /health/ready funcionen correctamente.
Categoría: Infrastructure - Tests que verifican la disponibilidad y estado de servicios del sistema.
"""
import pytest
import requests
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
import json


class TestHealthEndpoints(TestCase):
    """Tests para los endpoints de health check."""
    
    def setUp(self):
        """Configuración inicial para los tests."""
        self.client = Client()
    
    def test_health_live_endpoint(self):
        """Test que /health/live retorna respuesta correcta."""
        response = self.client.get('/health/live/')
        
        # Verificar código de respuesta
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Verificar estructura de respuesta
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'bff-stock-system')
        self.assertEqual(data['version'], '1.0.0')
        self.assertEqual(data['uptime_check'], 'ok')
        
        # Verificar campos de timing
        self.assertIn('timestamp', data)
        self.assertIn('latency_ms', data)
        self.assertIsInstance(data['timestamp'], (int, float))
        self.assertIsInstance(data['latency_ms'], (int, float))
        self.assertLess(data['latency_ms'], 1000)  # Debe ser rápido
    
    def test_health_ready_endpoint_healthy(self):
        """Test que /health/ready retorna respuesta correcta cuando todo está bien."""
        with patch('apps.core.health.check_database') as mock_db, \
             patch('apps.core.health.check_cache') as mock_cache, \
             patch('apps.core.health.check_smtp') as mock_smtp, \
             patch('apps.core.health.check_celery') as mock_celery:
            
            # Mock de respuestas saludables
            mock_db.return_value = {'status': 'healthy', 'latency_ms': 10}
            mock_cache.return_value = {'status': 'healthy', 'latency_ms': 5}
            mock_smtp.return_value = {'status': 'healthy', 'latency_ms': 20}
            mock_celery.return_value = {'status': 'healthy', 'latency_ms': 15}
            
            response = self.client.get('/health/ready/')
            
            # Verificar código de respuesta
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'application/json')
            
            # Verificar estructura de respuesta
            data = response.json()
            self.assertEqual(data['status'], 'healthy')
            self.assertEqual(data['service'], 'bff-stock-system')
            self.assertEqual(data['version'], '1.0.0')
            self.assertEqual(len(data['failed_checks']), 0)
            
            # Verificar que todos los checks están presentes
            self.assertIn('checks', data)
            self.assertIn('database', data['checks'])
            self.assertIn('cache', data['checks'])
            self.assertIn('smtp', data['checks'])
            self.assertIn('celery', data['checks'])
    
    def test_health_ready_endpoint_unhealthy(self):
        """Test que /health/ready retorna 503 cuando hay servicios no saludables."""
        with patch('apps.core.health.check_database') as mock_db, \
             patch('apps.core.health.check_cache') as mock_cache, \
             patch('apps.core.health.check_smtp') as mock_smtp, \
             patch('apps.core.health.check_celery') as mock_celery:
            
            # Mock de respuestas con fallas
            mock_db.return_value = {'status': 'unhealthy', 'error': 'Connection failed'}
            mock_cache.return_value = {'status': 'healthy', 'latency_ms': 5}
            mock_smtp.return_value = {'status': 'healthy', 'latency_ms': 20}
            mock_celery.return_value = {'status': 'healthy', 'latency_ms': 15}
            
            response = self.client.get('/health/ready/')
            
            # Verificar código de respuesta de error
            self.assertEqual(response.status_code, 503)
            
            # Verificar estructura de respuesta
            data = response.json()
            self.assertEqual(data['status'], 'unhealthy')
            self.assertIn('database', data['failed_checks'])
    
    def test_health_live_via_url_name(self):
        """Test que el endpoint live funciona usando el nombre de URL."""
        url = reverse('health_live')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
    
    def test_health_ready_via_url_name(self):
        """Test que el endpoint ready funciona usando el nombre de URL."""
        with patch('apps.core.health.check_database') as mock_db, \
             patch('apps.core.health.check_cache') as mock_cache, \
             patch('apps.core.health.check_smtp') as mock_smtp, \
             patch('apps.core.health.check_celery') as mock_celery:
            
            # Mock de respuestas saludables
            mock_db.return_value = {'status': 'healthy', 'latency_ms': 10}
            mock_cache.return_value = {'status': 'healthy', 'latency_ms': 5}
            mock_smtp.return_value = {'status': 'healthy', 'latency_ms': 20}
            mock_celery.return_value = {'status': 'healthy', 'latency_ms': 15}
            
            url = reverse('health_ready')
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data['status'], 'healthy')


class TestHealthEndpointsIntegration:
    """Tests de integración para los endpoints de salud usando requests."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Configuración para tests de integración."""
        self.base_url = "http://localhost"
        self.timeout = 10
    
    def test_health_live_integration(self):
        """Test de integración para /health/live."""
        try:
            response = requests.get(
                f"{self.base_url}/health/live/",
                timeout=self.timeout
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'healthy'
            assert data['service'] == 'bff-stock-system'
            assert 'timestamp' in data
            assert 'latency_ms' in data
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Servidor no disponible para test de integración")
    
    def test_health_ready_integration(self):
        """Test de integración para /health/ready."""
        try:
            response = requests.get(
                f"{self.base_url}/health/ready/",
                timeout=self.timeout
            )
            
            # El endpoint puede retornar 200 o 503 dependiendo del estado
            assert response.status_code in [200, 503]
            data = response.json()
            assert 'status' in data
            assert 'service' in data
            assert 'checks' in data
            assert 'timestamp' in data
            
            # Verificar que los checks esperados están presentes
            expected_checks = ['database', 'cache', 'smtp', 'celery']
            for check in expected_checks:
                assert check in data['checks']
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Servidor no disponible para test de integración")


if __name__ == '__main__':
    # Ejecutar tests unitarios
    import unittest
    unittest.main()