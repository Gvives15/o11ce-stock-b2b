"""
Tests para el endpoint /auth/me de autenticación JWT.
Bloque 1 - Authentication + 'FE contract'
"""
import json
import pytest
from django.test import TestCase, Client
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch, Mock


class TestAuthMe(TestCase):
    """Tests para el endpoint /auth/me"""
    
    def setUp(self):
        """Configuración inicial para los tests"""
        self.client = Client()
        self.me_url = '/auth/me'
        
        # Crear usuario de prueba
        self.test_user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com',
            is_active=True
        )
        
        # Crear superuser para tests de roles
        self.admin_user = User.objects.create_superuser(
            username='admin',
            password='adminpass123',
            email='admin@example.com'
        )
        
        # Generar tokens JWT para los tests
        self.user_refresh = RefreshToken.for_user(self.test_user)
        self.user_access_token = str(self.user_refresh.access_token)
        
        self.admin_refresh = RefreshToken.for_user(self.admin_user)
        self.admin_access_token = str(self.admin_refresh.access_token)
    
    def test_me_successful_regular_user(self):
        """Test: Endpoint /me exitoso para usuario regular"""
        response = self.client.get(
            self.me_url,
            HTTP_AUTHORIZATION=f'Bearer {self.user_access_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        # Verificar estructura de respuesta
        self.assertIn('id', response_data)
        self.assertIn('username', response_data)
        self.assertIn('roles', response_data)
        
        # Verificar datos del usuario
        self.assertEqual(response_data['id'], self.test_user.id)
        self.assertEqual(response_data['username'], 'testuser')
        self.assertIsInstance(response_data['roles'], list)
    
    def test_me_successful_admin_user(self):
        """Test: Endpoint /me exitoso para usuario admin"""
        response = self.client.get(
            self.me_url,
            HTTP_AUTHORIZATION=f'Bearer {self.admin_access_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        # Verificar que el admin tiene rol de admin
        self.assertEqual(response_data['id'], self.admin_user.id)
        self.assertEqual(response_data['username'], 'admin')
        self.assertIn('admin', response_data['roles'])
    
    def test_me_missing_authorization_header(self):
        """Test: /me sin header Authorization"""
        response = self.client.get(self.me_url)
        
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        
        self.assertEqual(response_data['error'], 'MISSING_TOKEN')
        self.assertIn('Authorization header with Bearer token is required', response_data['message'])
    
    def test_me_invalid_authorization_format(self):
        """Test: /me con formato de Authorization inválido"""
        response = self.client.get(
            self.me_url,
            HTTP_AUTHORIZATION='InvalidFormat token123'
        )
        
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        
        self.assertEqual(response_data['error'], 'MISSING_TOKEN')
        self.assertIn('Authorization header with Bearer token is required', response_data['message'])
    
    def test_me_invalid_token(self):
        """Test: /me con token JWT inválido"""
        response = self.client.get(
            self.me_url,
            HTTP_AUTHORIZATION='Bearer invalid.jwt.token'
        )
        
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        
        self.assertEqual(response_data['error'], 'INVALID_TOKEN')
        self.assertIn('Invalid or expired token', response_data['message'])
    
    def test_me_expired_token(self):
        """Test: /me con token JWT expirado"""
        # Crear token con tiempo de vida muy corto
        from rest_framework_simplejwt.tokens import AccessToken
        from datetime import timedelta
        
        # Mock para simular token expirado
        with patch('rest_framework_simplejwt.authentication.JWTAuthentication.get_validated_token') as mock_validate:
            from rest_framework_simplejwt.exceptions import TokenError
            mock_validate.side_effect = TokenError("Token is invalid or expired")
            
            response = self.client.get(
                self.me_url,
                HTTP_AUTHORIZATION=f'Bearer {self.user_access_token}'
            )
            
            self.assertEqual(response.status_code, 401)
            response_data = json.loads(response.content)
            
            self.assertEqual(response_data['error'], 'INVALID_TOKEN')
            self.assertIn('Invalid or expired token', response_data['message'])
    
    def test_me_method_not_allowed(self):
        """Test: Método POST no permitido en /me"""
        response = self.client.post(
            self.me_url,
            HTTP_AUTHORIZATION=f'Bearer {self.user_access_token}'
        )
        
        self.assertEqual(response.status_code, 405)  # Method Not Allowed
    
    def test_me_response_structure(self):
        """Test: Verificar estructura exacta de respuesta de /me"""
        response = self.client.get(
            self.me_url,
            HTTP_AUTHORIZATION=f'Bearer {self.user_access_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        # Verificar campos obligatorios
        required_fields = {'id', 'username', 'roles'}
        self.assertTrue(required_fields.issubset(set(response_data.keys())))
        
        # Verificar tipos de datos
        self.assertIsInstance(response_data['id'], int)
        self.assertIsInstance(response_data['username'], str)
        self.assertIsInstance(response_data['roles'], list)
    
    @patch('apps.core.auth_api.Customer')
    def test_me_with_customer_data_error(self, mock_customer):
        """Test: /me con error al obtener datos de customer"""
        # Simular error en la consulta de Customer
        mock_customer.objects.get.side_effect = Exception("Database error")
        
        response = self.client.get(
            self.me_url,
            HTTP_AUTHORIZATION=f'Bearer {self.user_access_token}'
        )
        
        # Debería devolver información básica del usuario
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertEqual(response_data['id'], self.test_user.id)
        self.assertEqual(response_data['username'], 'testuser')
        self.assertIn('roles', response_data)
    
    def test_me_with_scope_permissions(self):
        """Test: /me con permisos de scope (si están implementados)"""
        # Este test verifica la estructura para futuros scopes
        response = self.client.get(
            self.me_url,
            HTTP_AUTHORIZATION=f'Bearer {self.user_access_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        # Verificar que la respuesta es consistente
        self.assertIn('roles', response_data)
        # Los scopes específicos se implementarán en futuras versiones
    
    @patch('apps.core.auth_api.logger')
    def test_me_logging_successful(self, mock_logger):
        """Test: Verificar que se registra correctamente el acceso exitoso"""
        response = self.client.get(
            self.me_url,
            HTTP_AUTHORIZATION=f'Bearer {self.user_access_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar que se llamó al logger con información correcta
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        self.assertEqual(call_args[0][0], "me_endpoint_successful")
        self.assertIn('user_id', call_args[1])
        self.assertIn('username', call_args[1])
    
    @patch('apps.core.auth_api.logger')
    def test_me_logging_invalid_token(self, mock_logger):
        """Test: Verificar logging para token inválido"""
        response = self.client.get(
            self.me_url,
            HTTP_AUTHORIZATION='Bearer invalid.token'
        )
        
        self.assertEqual(response.status_code, 401)
        
        # Verificar que se registró el intento con token inválido
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        self.assertEqual(call_args[0][0], "me_endpoint_invalid_token")


@pytest.mark.django_db
class TestAuthMePytest:
    """Tests adicionales usando pytest para el endpoint /me"""
    
    def test_me_with_staff_user(self, client):
        """Test: /me con usuario staff"""
        staff_user = User.objects.create_user(
            username='staff',
            password='staffpass123',
            is_staff=True,
            is_active=True
        )
        
        refresh = RefreshToken.for_user(staff_user)
        access_token = str(refresh.access_token)
        
        response = client.get(
            '/auth/me',
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )
        
        assert response.status_code == 200
        response_data = json.loads(response.content)
        
        assert response_data['id'] == staff_user.id
        assert response_data['username'] == 'staff'
        assert 'admin' in response_data['roles']  # Staff debería tener rol admin
    
    def test_me_concurrent_requests(self, client):
        """Test: Múltiples requests concurrentes a /me"""
        user = User.objects.create_user(
            username='concurrent_user',
            password='testpass123',
            is_active=True
        )
        
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        
        # Simular múltiples requests concurrentes
        responses = []
        for _ in range(5):
            response = client.get(
                '/auth/me',
                HTTP_AUTHORIZATION=f'Bearer {access_token}'
            )
            responses.append(response)
        
        # Todos deberían ser exitosos
        for response in responses:
            assert response.status_code == 200
            response_data = json.loads(response.content)
            assert response_data['username'] == 'concurrent_user'
    
    def test_me_token_without_user(self, client):
        """Test: /me con token que referencia usuario inexistente"""
        # Crear usuario, generar token, luego eliminar usuario
        temp_user = User.objects.create_user(
            username='temp_user',
            password='testpass123',
            is_active=True
        )
        
        refresh = RefreshToken.for_user(temp_user)
        access_token = str(refresh.access_token)
        
        # Eliminar el usuario
        temp_user.delete()
        
        response = client.get(
            '/auth/me',
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )
        
        # Debería fallar con token inválido
        assert response.status_code == 401
        response_data = json.loads(response.content)
        assert response_data['error'] == 'INVALID_TOKEN'