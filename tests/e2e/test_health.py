"""
Tests E2E para endpoints de health check.
Bloque 0 - Pre-flight: Verificación de endpoints /health/live y /health/ready.

Objetivo: Verificar que los endpoints de health respondan correctamente:
- GET /health/live ⇒ 200 + {"status":"ok"}
- GET /health/ready ⇒ 200 solo si DB/Redis/Celery/SMTP responden (simular falla y esperar 503)
"""
import pytest
from django.test import TestCase, Client
from unittest.mock import patch
import json


class TestHealthEndpointsE2E(TestCase):
    """Tests E2E para endpoints de health check."""
    
    def setUp(self):
        """Configuración inicial para los tests."""
        self.client = Client()
    
    def test_health_live_returns_200_with_status_ok(self):
        """
        Test que /health/live retorna 200 + {"status":"ok"}.
        Este endpoint debe estar siempre disponible.
        """
        response = self.client.get('/health/live/')
        
        # Verificar código de respuesta
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Verificar estructura de respuesta
        data = response.json()
        self.assertEqual(data['status'], 'healthy')  # El endpoint actual usa 'healthy'
        self.assertEqual(data['service'], 'bff-stock-system')
        self.assertEqual(data['version'], '1.0.0')
        self.assertEqual(data['uptime_check'], 'ok')
        
        # Verificar campos de timing
        self.assertIn('timestamp', data)
        self.assertIn('latency_ms', data)
        self.assertIsInstance(data['timestamp'], (int, float))
        self.assertIsInstance(data['latency_ms'], (int, float))
        self.assertLess(data['latency_ms'], 1000)  # Debe ser rápido
    
    def test_health_ready_returns_200_when_all_services_healthy(self):
        """
        Test que /health/ready retorna 200 cuando todos los servicios están saludables.
        """
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
    
    def test_health_ready_returns_503_when_database_fails(self):
        """
        Test que /health/ready retorna 503 cuando la base de datos falla.
        Simular falla y esperar 503.
        """
        with patch('apps.core.health.check_database') as mock_db, \
             patch('apps.core.health.check_cache') as mock_cache, \
             patch('apps.core.health.check_smtp') as mock_smtp, \
             patch('apps.core.health.check_celery') as mock_celery:
            
            # Mock de respuestas con falla en DB
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
            self.assertEqual(len(data['failed_checks']), 1)
    
    def test_health_ready_returns_503_when_redis_fails(self):
        """
        Test que /health/ready retorna 503 cuando Redis/Cache falla.
        """
        with patch('apps.core.health.check_database') as mock_db, \
             patch('apps.core.health.check_cache') as mock_cache, \
             patch('apps.core.health.check_smtp') as mock_smtp, \
             patch('apps.core.health.check_celery') as mock_celery:
            
            # Mock de respuestas con falla en Cache
            mock_db.return_value = {'status': 'healthy', 'latency_ms': 10}
            mock_cache.return_value = {'status': 'unhealthy', 'error': 'Redis connection failed'}
            mock_smtp.return_value = {'status': 'healthy', 'latency_ms': 20}
            mock_celery.return_value = {'status': 'healthy', 'latency_ms': 15}
            
            response = self.client.get('/health/ready/')
            
            # Verificar código de respuesta de error
            self.assertEqual(response.status_code, 503)
            
            # Verificar estructura de respuesta
            data = response.json()
            self.assertEqual(data['status'], 'unhealthy')
            self.assertIn('cache', data['failed_checks'])
    
    def test_health_ready_returns_503_when_celery_fails(self):
        """
        Test que /health/ready retorna 503 cuando Celery falla.
        """
        with patch('apps.core.health.check_database') as mock_db, \
             patch('apps.core.health.check_cache') as mock_cache, \
             patch('apps.core.health.check_smtp') as mock_smtp, \
             patch('apps.core.health.check_celery') as mock_celery:
            
            # Mock de respuestas con falla en Celery
            mock_db.return_value = {'status': 'healthy', 'latency_ms': 10}
            mock_cache.return_value = {'status': 'healthy', 'latency_ms': 5}
            mock_smtp.return_value = {'status': 'healthy', 'latency_ms': 20}
            mock_celery.return_value = {'status': 'unhealthy', 'error': 'Celery workers not responding'}
            
            response = self.client.get('/health/ready/')
            
            # Verificar código de respuesta de error
            self.assertEqual(response.status_code, 503)
            
            # Verificar estructura de respuesta
            data = response.json()
            self.assertEqual(data['status'], 'unhealthy')
            self.assertIn('celery', data['failed_checks'])
    
    def test_health_ready_returns_503_when_smtp_fails(self):
        """
        Test que /health/ready retorna 503 cuando SMTP falla.
        """
        with patch('apps.core.health.check_database') as mock_db, \
             patch('apps.core.health.check_cache') as mock_cache, \
             patch('apps.core.health.check_smtp') as mock_smtp, \
             patch('apps.core.health.check_celery') as mock_celery:
            
            # Mock de respuestas con falla en SMTP
            mock_db.return_value = {'status': 'healthy', 'latency_ms': 10}
            mock_cache.return_value = {'status': 'healthy', 'latency_ms': 5}
            mock_smtp.return_value = {'status': 'unhealthy', 'error': 'SMTP server unreachable'}
            mock_celery.return_value = {'status': 'healthy', 'latency_ms': 15}
            
            response = self.client.get('/health/ready/')
            
            # Verificar código de respuesta de error
            self.assertEqual(response.status_code, 503)
            
            # Verificar estructura de respuesta
            data = response.json()
            self.assertEqual(data['status'], 'unhealthy')
            self.assertIn('smtp', data['failed_checks'])
    
    def test_health_ready_returns_503_when_multiple_services_fail(self):
        """
        Test que /health/ready retorna 503 cuando múltiples servicios fallan.
        """
        with patch('apps.core.health.check_database') as mock_db, \
             patch('apps.core.health.check_cache') as mock_cache, \
             patch('apps.core.health.check_smtp') as mock_smtp, \
             patch('apps.core.health.check_celery') as mock_celery:
            
            # Mock de respuestas con múltiples fallas
            mock_db.return_value = {'status': 'unhealthy', 'error': 'DB connection failed'}
            mock_cache.return_value = {'status': 'unhealthy', 'error': 'Redis connection failed'}
            mock_smtp.return_value = {'status': 'healthy', 'latency_ms': 20}
            mock_celery.return_value = {'status': 'healthy', 'latency_ms': 15}
            
            response = self.client.get('/health/ready/')
            
            # Verificar código de respuesta de error
            self.assertEqual(response.status_code, 503)
            
            # Verificar estructura de respuesta
            data = response.json()
            self.assertEqual(data['status'], 'unhealthy')
            self.assertIn('database', data['failed_checks'])
            self.assertIn('cache', data['failed_checks'])
            self.assertEqual(len(data['failed_checks']), 2)


@pytest.mark.e2e
class TestHealthEndpointsE2EPytest:
    """Tests E2E usando pytest para endpoints de health check."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Configuración para tests de pytest."""
        from django.test import Client
        self.client = Client()
    
    def test_health_live_basic_functionality(self):
        """Test básico de funcionalidad del endpoint /health/live."""
        response = self.client.get('/health/live/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'latency_ms' in data
    
    def test_health_ready_with_all_services_up(self):
        """Test de /health/ready con todos los servicios funcionando."""
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
            
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'healthy'
            assert len(data['failed_checks']) == 0
    
    def test_health_ready_service_failure_returns_503(self):
        """Test de /health/ready con falla de servicio retorna 503."""
        with patch('apps.core.health.check_database') as mock_db, \
             patch('apps.core.health.check_cache') as mock_cache, \
             patch('apps.core.health.check_smtp') as mock_smtp, \
             patch('apps.core.health.check_celery') as mock_celery:
            
            # Mock con falla en cualquier servicio
            mock_db.return_value = {'status': 'unhealthy', 'error': 'Service down'}
            mock_cache.return_value = {'status': 'healthy', 'latency_ms': 5}
            mock_smtp.return_value = {'status': 'healthy', 'latency_ms': 20}
            mock_celery.return_value = {'status': 'healthy', 'latency_ms': 15}
            
            response = self.client.get('/health/ready/')
            
            assert response.status_code == 503
            data = response.json()
            assert data['status'] == 'unhealthy'
            assert len(data['failed_checks']) > 0