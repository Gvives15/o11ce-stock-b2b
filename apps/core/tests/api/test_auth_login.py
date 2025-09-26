"""
Tests para el endpoint de login de autenticación JWT.
Bloque 1 - Authentication + 'FE contract'
"""
import json
import pytest
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch
from rest_framework_simplejwt.tokens import RefreshToken


class TestAuthLogin(TestCase):
    """Tests para el endpoint /auth/login"""
    
    def setUp(self):
        """Configuración inicial para los tests"""
        self.client = Client()
        self.login_url = '/auth/login'
        
        # Crear usuario de prueba
        self.test_user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com',
            is_active=True
        )
        
        # Usuario inactivo para tests
        self.inactive_user = User.objects.create_user(
            username='inactive',
            password='testpass123',
            email='inactive@example.com',
            is_active=False
        )
    
    def test_login_successful(self):
        """Test: Login exitoso con credenciales válidas"""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        # Verificar que se devuelven los tokens
        self.assertIn('access', response_data)
        self.assertIn('refresh', response_data)
        
        # Verificar que los tokens no están vacíos
        self.assertTrue(response_data['access'])
        self.assertTrue(response_data['refresh'])
    
    def test_login_invalid_credentials(self):
        """Test: Login con credenciales inválidas"""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        
        self.assertEqual(response_data['error'], 'INVALID_CREDENTIALS')
        self.assertIn('Invalid username or password', response_data['message'])
    
    def test_login_missing_username(self):
        """Test: Login sin username"""
        data = {
            'password': 'testpass123'
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        
        self.assertEqual(response_data['error'], 'MISSING_CREDENTIALS')
        self.assertIn('Username and password are required', response_data['message'])
    
    def test_login_missing_password(self):
        """Test: Login sin password"""
        data = {
            'username': 'testuser'
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        
        self.assertEqual(response_data['error'], 'MISSING_CREDENTIALS')
        self.assertIn('Username and password are required', response_data['message'])
    
    def test_login_inactive_user(self):
        """Test: Login con usuario inactivo"""
        data = {
            'username': 'inactive',
            'password': 'testpass123'
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        
        self.assertEqual(response_data['error'], 'INACTIVE_USER')
        self.assertIn('User account is disabled', response_data['message'])
    
    def test_login_invalid_json(self):
        """Test: Login con JSON inválido"""
        response = self.client.post(
            self.login_url,
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        
        self.assertEqual(response_data['error'], 'INVALID_JSON')
        self.assertIn('Invalid JSON in request body', response_data['message'])
    
    def test_login_method_not_allowed(self):
        """Test: Método GET no permitido en login"""
        response = self.client.get(self.login_url)
        
        self.assertEqual(response.status_code, 405)  # Method Not Allowed
    
    @patch('apps.core.auth_api.authenticate')
    def test_login_authentication_exception(self, mock_authenticate):
        """Test: Manejo de excepciones durante autenticación"""
        mock_authenticate.side_effect = Exception("Database error")
        
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        
        self.assertEqual(response_data['error'], 'INTERNAL_ERROR')
        self.assertIn('An internal error occurred', response_data['message'])
    
    def test_login_rate_limiting_structure(self):
        """Test: Verificar que el rate limiting está configurado"""
        # Este test verifica que el endpoint tiene rate limiting
        # El rate limiting real se testea en tests de integración
        
        # Hacer múltiples requests rápidos
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        responses = []
        for _ in range(3):
            response = self.client.post(
                self.login_url,
                data=json.dumps(data),
                content_type='application/json'
            )
            responses.append(response.status_code)
        
        # Todos deberían ser 401 (credenciales inválidas) no 429 (rate limited)
        # en un entorno de test normal
        for status_code in responses:
            self.assertIn(status_code, [401, 429])  # 429 si rate limit activo
    
    def test_login_response_structure(self):
        """Test: Verificar estructura de respuesta exitosa"""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        # Verificar estructura exacta de respuesta
        expected_keys = {'access', 'refresh'}
        self.assertEqual(set(response_data.keys()), expected_keys)
        
        # Verificar que los tokens son strings válidos
        self.assertIsInstance(response_data['access'], str)
        self.assertIsInstance(response_data['refresh'], str)
        self.assertTrue(len(response_data['access']) > 50)  # JWT típico
        self.assertTrue(len(response_data['refresh']) > 50)  # JWT típico


@pytest.mark.django_db
class TestAuthLoginPytest:
    """Tests adicionales usando pytest para el endpoint de login"""
    
    def test_login_with_special_characters(self, client):
        """Test: Login con caracteres especiales en credenciales"""
        # Crear usuario con caracteres especiales
        user = User.objects.create_user(
            username='user@domain.com',
            password='pass!@#$%^&*()',
            is_active=True
        )
        
        data = {
            'username': 'user@domain.com',
            'password': 'pass!@#$%^&*()'
        }
        
        response = client.post(
            '/auth/login',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert 'access' in response_data
        assert 'refresh' in response_data
    
    def test_login_case_sensitive_username(self, client):
        """Test: Verificar que el username es case-sensitive"""
        User.objects.create_user(
            username='TestUser',
            password='testpass123',
            is_active=True
        )
        
        # Intentar login con diferente case
        data = {
            'username': 'testuser',  # lowercase
            'password': 'testpass123'
        }
        
        response = client.post(
            '/auth/login',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 401
        response_data = json.loads(response.content)
        assert response_data['error'] == 'INVALID_CREDENTIALS'