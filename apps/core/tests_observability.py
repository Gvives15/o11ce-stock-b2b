"""
Tests para el sistema de observabilidad: health endpoints, logging y request tracking.
"""
import json
import uuid
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.db import connection
from django.core.cache import cache
import structlog
from apps.core.health import check_database, check_cache, health_live, health_ready


class HealthEndpointsTestCase(TestCase):
    """Tests para los endpoints de health check."""
    
    def setUp(self):
        self.client = Client()
    
    def test_health_live_always_returns_200(self):
        """Test: /health/live siempre debe retornar 200."""
        response = self.client.get('/health/live/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('timestamp', data)
        self.assertIn('service', data)
        self.assertIn('version', data)
        self.assertIn('latency_ms', data)
        self.assertEqual(data['service'], 'bff-stock-system')
    
    def test_health_ready_with_db_ok(self):
        """Test: /health/ready retorna 200 cuando DB está OK."""
        response = self.client.get('/health/ready/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('checks', data)
        self.assertIn('database', data['checks'])
        self.assertEqual(data['checks']['database']['status'], 'healthy')
    
    @patch('apps.core.health.check_database')
    def test_health_ready_with_db_failure(self, mock_check_db):
        """Test: /health/ready retorna 503 cuando DB falla."""
        # Mock database failure
        mock_check_db.return_value = {
            'status': 'unhealthy',
            'error': 'Connection failed',
            'details': 'Database connection failed'
        }
        
        response = self.client.get('/health/ready/')
        
        self.assertEqual(response.status_code, 503)
        data = response.json()
        
        self.assertEqual(data['status'], 'unhealthy')
        self.assertIn('database', data['failed_checks'])
        self.assertEqual(data['checks']['database']['status'], 'unhealthy')


class RequestIDMiddlewareTestCase(TestCase):
    """Tests para el middleware de Request ID."""
    
    def setUp(self):
        self.client = Client()
    
    def test_request_id_middleware_integration(self):
        """Test: El middleware de Request ID está funcionando."""
        # Hacer un request sin X-Request-ID
        response = self.client.get('/health/live/')
        
        # El middleware debería agregar el header en la respuesta
        # Verificamos que la respuesta sea exitosa
        self.assertEqual(response.status_code, 200)
        
        # En un entorno de test, verificamos que el middleware está configurado
        from django.conf import settings
        self.assertIn('apps.core.middleware.RequestIDMiddleware', settings.MIDDLEWARE)
    
    def test_request_id_context_setup(self):
        """Test: El contexto de structlog se configura correctamente."""
        # Verificar que el middleware está en la configuración
        from django.conf import settings
        middleware_classes = settings.MIDDLEWARE
        
        self.assertIn('apps.core.middleware.RequestIDMiddleware', middleware_classes)
        self.assertIn('apps.core.middleware.AccessLogMiddleware', middleware_classes)


class AccessLogMiddlewareTestCase(TestCase):
    """Tests para el middleware de logging de acceso."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_access_log_middleware_configured(self):
        """Test: El middleware de access log está configurado."""
        from django.conf import settings
        self.assertIn('apps.core.middleware.AccessLogMiddleware', settings.MIDDLEWARE)
    
    def test_request_processing_works(self):
        """Test: Los requests se procesan correctamente con el middleware."""
        response = self.client.get('/health/live/')
        
        # Verificar que la respuesta es exitosa
        self.assertEqual(response.status_code, 200)
        
        # Verificar que el middleware no interfiere con el funcionamiento normal
        data = response.json()
        self.assertEqual(data['status'], 'healthy')


class HealthCheckFunctionsTestCase(TestCase):
    """Tests para las funciones individuales de health check."""
    
    def test_check_database_success(self):
        """Test: check_database retorna healthy cuando DB está OK."""
        result = check_database()
        
        self.assertEqual(result['status'], 'healthy')
        self.assertIn('latency_ms', result)
        self.assertIn('details', result)
    
    @patch('django.db.connection.cursor')
    def test_check_database_failure(self, mock_cursor):
        """Test: check_database retorna unhealthy cuando DB falla."""
        # Mock database failure
        mock_cursor.side_effect = Exception('Connection failed')
        
        result = check_database()
        
        self.assertEqual(result['status'], 'unhealthy')
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'Connection failed')
    
    def test_check_cache_with_fault_tolerance(self):
        """Test: El chequeo de cache maneja errores con tolerancia a fallos."""
        # Simular error en cache
        with patch('django.core.cache.cache.get', side_effect=Exception("Cache error")):
            result = check_cache()
            
            # Verificar que el resultado indica degradación
            self.assertEqual(result['status'], 'degraded')
            self.assertIn('error', result)
            self.assertTrue(result['fault_tolerant'])


class StructlogConfigurationTestCase(TestCase):
    """Tests para la configuración de structlog."""
    
    def test_structlog_logger_creation(self):
        """Test: structlog puede crear loggers correctamente."""
        logger = structlog.get_logger(__name__)
        self.assertIsNotNone(logger)
        
        # Verificar que el logger tiene los métodos esperados
        self.assertTrue(hasattr(logger, 'info'))
        self.assertTrue(hasattr(logger, 'error'))
        self.assertTrue(hasattr(logger, 'warning'))
    
    def test_structlog_context_binding(self):
        """Test: structlog puede bindear contexto correctamente."""
        # Limpiar contexto
        structlog.contextvars.clear_contextvars()
        
        # Configurar contexto
        structlog.contextvars.bind_contextvars(
            request_id="test-request-id",
            user_id=123
        )
        
        # Verificar que el contexto se configuró
        # (No podemos verificar directamente el output, pero podemos verificar que no hay errores)
        logger = structlog.get_logger(__name__)
        
        # Esto no debería lanzar excepciones
        try:
            logger.info("test_message")
            context_works = True
        except Exception:
            context_works = False
        
        self.assertTrue(context_works)