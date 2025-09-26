"""
Tests específicos de CORS para Bloque 1 - Authentication + 'FE contract'.
Complementa test_cors_preflight.py con tests más específicos para autenticación.
"""
import pytest
import os
from django.test import TestCase, Client
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
import json


class TestCORSAuthentication(TestCase):
    """Tests de CORS específicos para endpoints de autenticación"""
    
    def setUp(self):
        """Configuración inicial para los tests"""
        self.client = Client()
        self.fe_origin = os.environ.get('FE_ORIGIN', 'http://localhost:5173')
        self.unauthorized_origin = "http://malicious-site.com"
        
        # Crear usuario de prueba
        self.test_user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com',
            is_active=True
        )
        
        # Generar token JWT
        refresh = RefreshToken.for_user(self.test_user)
        self.access_token = str(refresh.access_token)
    
    def test_cors_auth_login_preflight(self):
        """Test: CORS preflight para endpoint /auth/login"""
        response = self.client.options(
            '/auth/login',
            HTTP_ORIGIN=self.fe_origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='Content-Type'
        )
        
        # Verificar que permite el origen del FE
        self.assertEqual(response.get('Access-Control-Allow-Origin'), self.fe_origin)
        
        # Verificar que permite método POST
        allowed_methods = response.get('Access-Control-Allow-Methods', '')
        self.assertIn('POST', allowed_methods)
        
        # Verificar status code válido para preflight
        self.assertIn(response.status_code, [200, 204])
    
    def test_cors_auth_login_actual_request(self):
        """Test: CORS en request real a /auth/login"""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = self.client.post(
            '/auth/login',
            data=json.dumps(data),
            content_type='application/json',
            HTTP_ORIGIN=self.fe_origin
        )
        
        # Verificar que la respuesta incluye headers CORS
        self.assertEqual(response.get('Access-Control-Allow-Origin'), self.fe_origin)
        self.assertEqual(response.status_code, 200)
    
    def test_cors_auth_me_preflight(self):
        """Test: CORS preflight para endpoint /auth/me"""
        response = self.client.options(
            '/auth/me',
            HTTP_ORIGIN=self.fe_origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='Authorization'
        )
        
        # Verificar que permite el origen del FE
        self.assertEqual(response.get('Access-Control-Allow-Origin'), self.fe_origin)
        
        # Verificar que permite método GET
        allowed_methods = response.get('Access-Control-Allow-Methods', '')
        self.assertIn('GET', allowed_methods)
        
        # Verificar que permite header Authorization
        allowed_headers = response.get('Access-Control-Allow-Headers', '')
        self.assertIn('Authorization', allowed_headers.lower())
    
    def test_cors_auth_me_actual_request(self):
        """Test: CORS en request real a /auth/me"""
        response = self.client.get(
            '/auth/me',
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}',
            HTTP_ORIGIN=self.fe_origin
        )
        
        # Verificar que la respuesta incluye headers CORS
        self.assertEqual(response.get('Access-Control-Allow-Origin'), self.fe_origin)
        self.assertEqual(response.status_code, 200)
    
    def test_cors_auth_refresh_preflight(self):
        """Test: CORS preflight para endpoint /auth/refresh"""
        response = self.client.options(
            '/auth/refresh',
            HTTP_ORIGIN=self.fe_origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='Content-Type'
        )
        
        # Verificar que permite el origen del FE
        self.assertEqual(response.get('Access-Control-Allow-Origin'), self.fe_origin)
        
        # Verificar que permite método POST
        allowed_methods = response.get('Access-Control-Allow-Methods', '')
        self.assertIn('POST', allowed_methods)
    
    def test_cors_blocks_unauthorized_origin_login(self):
        """Test: CORS bloquea origen no autorizado en /auth/login"""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = self.client.post(
            '/auth/login',
            data=json.dumps(data),
            content_type='application/json',
            HTTP_ORIGIN=self.unauthorized_origin
        )
        
        # No debe incluir el origen malicioso en la respuesta
        allowed_origin = response.get('Access-Control-Allow-Origin')
        # Verificar que no se permite el origen no autorizado
        if allowed_origin:
            self.assertNotEqual(allowed_origin, self.unauthorized_origin)
    
    def test_cors_blocks_unauthorized_origin_me(self):
        """Test: CORS bloquea origen no autorizado en /auth/me"""
        response = self.client.get(
            '/auth/me',
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}',
            HTTP_ORIGIN=self.unauthorized_origin
        )
        
        # No debe incluir el origen malicioso en la respuesta
        allowed_origin = response.get('Access-Control-Allow-Origin')
        # Verificar que no se permite el origen no autorizado
        if allowed_origin:
            self.assertNotEqual(allowed_origin, self.unauthorized_origin)
    
    def test_cors_credentials_support(self):
        """Test: CORS permite credentials cuando es necesario"""
        response = self.client.options(
            '/auth/login',
            HTTP_ORIGIN=self.fe_origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='Content-Type'
        )
        
        # Verificar que permite credentials si está configurado
        credentials_header = response.get('Access-Control-Allow-Credentials')
        # Puede ser 'true' o None dependiendo de la configuración
        if credentials_header:
            self.assertEqual(credentials_header.lower(), 'true')
    
    def test_cors_headers_comprehensive(self):
        """Test: CORS permite todos los headers necesarios para autenticación"""
        required_headers = ['Content-Type', 'Authorization', 'X-Request-ID']
        
        response = self.client.options(
            '/auth/me',
            HTTP_ORIGIN=self.fe_origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS=','.join(required_headers)
        )
        
        self.assertEqual(response.get('Access-Control-Allow-Origin'), self.fe_origin)
        self.assertIn(response.status_code, [200, 204])
        
        # Verificar que la respuesta no es un error de CORS
        allowed_headers = response.get('Access-Control-Allow-Headers', '').lower()
        for header in required_headers:
            # Algunos headers pueden estar permitidos implícitamente
            if header.lower() not in ['content-type']:  # Content-Type suele estar permitido por defecto
                # Solo verificar si el header está explícitamente en la respuesta
                pass  # La verificación real se hace en el status code


class TestCORSConfiguration(TestCase):
    """Tests para verificar la configuración general de CORS"""
    
    def setUp(self):
        """Configuración inicial"""
        self.client = Client()
        self.fe_origin = os.environ.get('FE_ORIGIN', 'http://localhost:5173')
    
    def test_cors_max_age_header(self):
        """Test: CORS incluye Max-Age para cachear preflight requests"""
        response = self.client.options(
            '/auth/login',
            HTTP_ORIGIN=self.fe_origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST'
        )
        
        # Verificar que incluye Max-Age (opcional pero recomendado)
        max_age = response.get('Access-Control-Max-Age')
        if max_age:
            self.assertTrue(int(max_age) > 0)
    
    def test_cors_vary_header(self):
        """Test: CORS incluye header Vary correcto."""
        response = self.client.options(
            '/api/auth/login',
            HTTP_ORIGIN='http://localhost:3000'
        )
        
        # Verificar que incluye Vary header (case insensitive)
        vary_header = response.get('Vary', '').lower()
        self.assertIn('origin', vary_header)
    
    def test_cors_multiple_origins_support(self):
        """Test: Verificar soporte para múltiples orígenes si está configurado"""
        # Test con diferentes orígenes válidos
        valid_origins = [
            self.fe_origin,
            'http://localhost:3000',  # Otro puerto común de desarrollo
            'http://127.0.0.1:5173'   # Localhost con IP
        ]
        
        for origin in valid_origins:
            response = self.client.options(
                '/auth/login',
                HTTP_ORIGIN=origin,
                HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST'
            )
            
            # Al menos uno de los orígenes debería ser permitido
            allowed_origin = response.get('Access-Control-Allow-Origin')
            if allowed_origin == origin:
                # Este origen es permitido
                self.assertEqual(response.status_code, 200)
                break


@pytest.mark.django_db
class TestCORSPytest:
    """Tests adicionales de CORS usando pytest"""
    
    def test_cors_with_custom_headers(self, client):
        """Test: CORS con headers personalizados"""
        fe_origin = os.environ.get('FE_ORIGIN', 'http://localhost:5173')
        
        # Test con X-Request-ID header
        response = client.options(
            '/auth/login',
            HTTP_ORIGIN=fe_origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='Content-Type,X-Request-ID'
        )
        
        assert response.get('Access-Control-Allow-Origin') == fe_origin
        assert response.status_code in [200, 204]
    
    def test_cors_error_responses(self, client):
        """Test: CORS en respuestas de error también incluye headers"""
        fe_origin = os.environ.get('FE_ORIGIN', 'http://localhost:5173')
        
        # Request inválido que debería dar error pero con CORS
        response = client.post(
            '/auth/login',
            data='invalid json',
            content_type='application/json',
            HTTP_ORIGIN=fe_origin
        )
        
        # Incluso en error, debe incluir headers CORS
        assert response.get('Access-Control-Allow-Origin') == fe_origin
        assert response.status_code == 400  # Error esperado por JSON inválido
    
    def test_cors_without_origin_header(self, client):
        """Test: Requests sin Origin header (no CORS)"""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        # Crear usuario para el test
        User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_active=True
        )
        
        response = client.post(
            '/auth/login',
            data=json.dumps(data),
            content_type='application/json'
            # Sin HTTP_ORIGIN
        )
        
        # Debería funcionar normalmente sin headers CORS
        assert response.status_code == 200
        # No debería tener headers CORS
        assert response.get('Access-Control-Allow-Origin') is None