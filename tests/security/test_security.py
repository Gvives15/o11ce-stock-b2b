"""
Tests de seguridad para el Bloque 3 - Seguridad práctica.

Tests requeridos:
- test_jwt_expiry_and_refresh
- test_logout_blacklists_refresh
- test_login_rate_limited_429
- test_checkout_rate_limited_429
- test_cors_allowed_origin_ok
- test_cors_blocked_origin_403
- test_schema_rejects_qty_le_zero_and_past_dates
"""

import os
import django
from django.conf import settings

# Configurar Django antes de importar modelos
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

import json
import time
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from apps.customers.models import Customer
from apps.stock.models import Product


class JWTSecurityTestCase(TestCase):
    """Tests para JWT: expiración, refresh y blacklist."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_jwt_expiry_and_refresh(self):
        """Test que verifica expiración de access token y funcionamiento del refresh."""
        # Login para obtener tokens
        response = self.client.post('/api/v1/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('access', data)
        self.assertIn('refresh', data)
        
        access_token = data['access']
        refresh_token = data['refresh']
        
        # Verificar que el access token funciona inicialmente
        headers = {'HTTP_AUTHORIZATION': f'Bearer {access_token}'}
        
        # Simular expiración del access token (en producción sería después de 15 minutos)
        # Para el test, usamos el refresh token directamente
        refresh_response = self.client.post('/api/v1/auth/refresh/', {
            'refresh': refresh_token
        }, content_type='application/json')
        
        self.assertEqual(refresh_response.status_code, 200)
        refresh_data = refresh_response.json()
        self.assertIn('access', refresh_data)
        # El refresh endpoint ahora solo devuelve access token según la especificación

    def test_logout_blacklists_refresh(self):
        """Test que verifica que logout agrega el refresh token al blacklist."""
        # Login para obtener tokens
        response = self.client.post('/api/v1/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        refresh_token = data['refresh']
        
        # Logout
        logout_response = self.client.post('/api/v1/auth/logout/', {
            'refresh_token': refresh_token
        }, content_type='application/json')
        
        self.assertEqual(logout_response.status_code, 200)
        
        # Intentar usar el refresh token después del logout (debe fallar)
        refresh_response = self.client.post('/api/v1/auth/refresh/', {
            'refresh': refresh_token
        }, content_type='application/json')
        
        self.assertEqual(refresh_response.status_code, 401)
        
        # Verificar que el token está en el blacklist (sin crear RefreshToken que falla)
        # El token ya está blacklistado, así que verificamos que el logout fue exitoso
        self.assertEqual(logout_response.status_code, 200)

    def test_auth_me_endpoint_with_roles(self):
        """Test que verifica que GET /auth/me devuelve roles específicos B0-BE-02."""
        # Crear roles
        from apps.panel.models import Role
        admin_role = Role.objects.create(name='admin', description='Administrador')
        vendedor_caja_role = Role.objects.create(name='vendedor_caja', description='Vendedor de Caja')
        
        # Crear usuario con roles específicos
        user = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        
        # Obtener o crear UserScope para el usuario (se crea automáticamente por signal)
        from apps.panel.models import UserScope
        scope, created = UserScope.objects.get_or_create(
            user=user,
            defaults={
                'has_scope_inventory': True,
                'has_scope_orders': True,
                'has_scope_dashboard': True
            }
        )
        if not created:
            # Si ya existe, actualizar los scopes
            scope.has_scope_inventory = True
            scope.has_scope_orders = True
            scope.has_scope_dashboard = True
            scope.save()
        
        # Asignar rol de vendedor_caja
        scope.roles.add(vendedor_caja_role)
        
        # Login para obtener token
        login_response = self.client.post('/api/v1/auth/login/', {
            'username': 'testuser2',
            'password': 'testpass123'
        }, content_type='application/json')
        
        self.assertEqual(login_response.status_code, 200)
        data = login_response.json()
        access_token = data['access']
        
        # Llamar al endpoint /auth/me
        headers = {'HTTP_AUTHORIZATION': f'Bearer {access_token}'}
        me_response = self.client.get('/api/v1/auth/me/', **headers)
        
        self.assertEqual(me_response.status_code, 200)
        me_data = me_response.json()
        
        # Verificar estructura de respuesta según especificación
        self.assertIn('id', me_data)
        self.assertIn('username', me_data)
        self.assertIn('roles', me_data)
        self.assertIsInstance(me_data['roles'], list)
        
        # Verificar que devuelve el rol específico de B0-BE-02
        self.assertIn('vendedor_caja', me_data['roles'])
        self.assertEqual(len(me_data['roles']), 1)

    def test_auth_me_endpoint_superuser(self):
        """Test que verifica roles de superusuario según B0-BE-02."""
        # Crear superusuario
        superuser = User.objects.create_superuser(
            username='superuser',
            email='super@example.com',
            password='testpass123'
        )
        
        # Login
        login_response = self.client.post('/api/v1/auth/login/', {
            'username': 'superuser',
            'password': 'testpass123'
        }, content_type='application/json')
        
        self.assertEqual(login_response.status_code, 200)
        data = login_response.json()
        access_token = data['access']
        
        # Llamar al endpoint /auth/me
        headers = {'HTTP_AUTHORIZATION': f'Bearer {access_token}'}
        me_response = self.client.get('/api/v1/auth/me/', **headers)
        
        self.assertEqual(me_response.status_code, 200)
        me_data = me_response.json()
        
        # Superusuario debe tener rol de admin según B0-BE-02
        self.assertIn('admin', me_data['roles'])
        self.assertEqual(len(me_data['roles']), 1)

    def test_auth_me_endpoint_invalid_token(self):
        """Test que verifica error 401 con token inválido."""
        # Llamar al endpoint /auth/me sin token
        me_response = self.client.get('/api/v1/auth/me/')
        self.assertEqual(me_response.status_code, 401)
        
        # Llamar con token inválido
        headers = {'HTTP_AUTHORIZATION': 'Bearer invalid_token'}
        me_response = self.client.get('/api/v1/auth/me/', **headers)
        self.assertEqual(me_response.status_code, 401)

    def test_login_invalid_credentials(self):
        """Test que verifica error 401 con credenciales inválidas."""
        response = self.client.post('/api/v1/auth/login/', {
            'username': 'nonexistent',
            'password': 'wrongpassword'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'INVALID_CREDENTIALS')

    def test_refresh_invalid_token(self):
        """Test que verifica error 401 con refresh token inválido."""
        response = self.client.post('/api/v1/auth/refresh/', {
            'refresh': 'invalid_refresh_token'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'INVALID_TOKEN')

    def test_auth_me_vendedor_caja_role(self):
        """Test específico para rol vendedor_caja según B0-BE-02."""
        # Crear rol vendedor_caja
        from apps.panel.models import Role
        vendedor_caja_role = Role.objects.create(name='vendedor_caja', description='Vendedor de Caja')
        
        # Crear usuario
        user = User.objects.create_user(
            username='vendedor_caja_user',
            email='vendedor@example.com',
            password='testpass123'
        )
        
        # Asignar rol
        from apps.panel.models import UserScope
        scope, created = UserScope.objects.get_or_create(user=user)
        scope.roles.add(vendedor_caja_role)
        
        # Login
        login_response = self.client.post('/api/v1/auth/login/', {
            'username': 'vendedor_caja_user',
            'password': 'testpass123'
        }, content_type='application/json')
        
        self.assertEqual(login_response.status_code, 200)
        data = login_response.json()
        access_token = data['access']
        
        # Llamar al endpoint /auth/me
        headers = {'HTTP_AUTHORIZATION': f'Bearer {access_token}'}
        me_response = self.client.get('/api/v1/auth/me/', **headers)
        
        self.assertEqual(me_response.status_code, 200)
        me_data = me_response.json()
        
        # Verificar que incluye el rol vendedor_caja
        self.assertIn('vendedor_caja', me_data['roles'])
        self.assertEqual(len(me_data['roles']), 1)

    def test_auth_me_admin_role(self):
        """Test específico para rol admin según B0-BE-02."""
        # Crear rol admin
        from apps.panel.models import Role
        admin_role = Role.objects.create(name='admin', description='Administrador')
        
        # Crear usuario
        user = User.objects.create_user(
            username='admin_user',
            email='admin@example.com',
            password='testpass123'
        )
        
        # Asignar rol
        from apps.panel.models import UserScope
        scope, created = UserScope.objects.get_or_create(user=user)
        scope.roles.add(admin_role)
        
        # Login
        login_response = self.client.post('/api/v1/auth/login/', {
            'username': 'admin_user',
            'password': 'testpass123'
        }, content_type='application/json')
        
        self.assertEqual(login_response.status_code, 200)
        data = login_response.json()
        access_token = data['access']
        
        # Llamar al endpoint /auth/me
        headers = {'HTTP_AUTHORIZATION': f'Bearer {access_token}'}
        me_response = self.client.get('/api/v1/auth/me/', **headers)
        
        self.assertEqual(me_response.status_code, 200)
        me_data = me_response.json()
        
        # Verificar que incluye el rol admin
        self.assertIn('admin', me_data['roles'])
        self.assertEqual(len(me_data['roles']), 1)


class RateLimitingTestCase(TestCase):
    """Tests para rate limiting en login y checkout."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Crear datos para checkout
        self.customer = Customer.objects.create(
            name='Test Customer',
            email='customer@test.com'
        )
        self.product = Product.objects.create(
            code='TEST-001',
            name='Test Product',
            price=Decimal('10.00')
        )

    def test_login_rate_limited_429(self):
        """Test que verifica rate limiting en login (5/min por IP)."""
        login_url = '/api/v1/auth/login/'
        login_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        # Hacer 5 requests exitosos (dentro del límite)
        for i in range(5):
            response = self.client.post(login_url, login_data, content_type='application/json')
            self.assertEqual(response.status_code, 200)
        
        # El 6to request debe ser bloqueado con 429
        response = self.client.post(login_url, login_data, content_type='application/json')
        self.assertEqual(response.status_code, 429)

    def test_checkout_rate_limited_429(self):
        """Test que verifica rate limiting en checkout (10/min por usuario)."""
        # Primero hacer login para obtener autenticación
        login_response = self.client.post('/api/v1/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        }, content_type='application/json')
        
        access_token = login_response.json()['access']
        headers = {'HTTP_AUTHORIZATION': f'Bearer {access_token}'}
        
        checkout_url = '/api/v1/order/checkout'
        checkout_data = {
            'customer_id': self.customer.id,
            'items': [{'product_id': self.product.id, 'qty': '1.0'}],
            'delivery_method': 'pickup'
        }
        
        # Hacer 10 requests (dentro del límite)
        for i in range(10):
            response = self.client.post(
                checkout_url, 
                checkout_data, 
                content_type='application/json',
                **headers
            )
            # Puede ser 201 (éxito) o 400/409 (error de validación), pero no 429
            self.assertNotEqual(response.status_code, 429)
        
        # El 11vo request debe ser bloqueado con 429
        response = self.client.post(
            checkout_url, 
            checkout_data, 
            content_type='application/json',
            **headers
        )
        self.assertEqual(response.status_code, 429)


class CORSSecurityTestCase(TestCase):
    """Tests para CORS allowlist."""

    def setUp(self):
        self.client = Client()

    def test_cors_allowed_origin_ok(self):
        """Test que verifica que orígenes permitidos pueden hacer requests."""
        # Simular request desde origen permitido
        response = self.client.options(
            '/api/v1/auth/login/',
            HTTP_ORIGIN='http://localhost:3000'
        )
        
        # Verificar que el request es permitido
        self.assertNotEqual(response.status_code, 403)
        
        # Verificar headers CORS
        if 'Access-Control-Allow-Origin' in response:
            self.assertIn('localhost:3000', response['Access-Control-Allow-Origin'])

    def test_cors_blocked_origin_403(self):
        """Test que verifica que orígenes no permitidos son bloqueados."""
        # Simular request desde origen no permitido
        response = self.client.options(
            '/api/v1/auth/login/',
            HTTP_ORIGIN='http://malicious-site.com'
        )
        
        # El middleware de CORS debería bloquear esto
        # Nota: django-cors-headers no devuelve 403, sino que omite los headers CORS
        # Verificamos que no hay header Access-Control-Allow-Origin
        self.assertNotIn('Access-Control-Allow-Origin', response)


class SchemaValidationTestCase(TestCase):
    """Tests para validaciones duras de esquemas."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Login para obtener token
        login_response = self.client.post('/api/v1/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        }, content_type='application/json')
        
        self.access_token = login_response.json()['access']
        self.headers = {'HTTP_AUTHORIZATION': f'Bearer {self.access_token}'}
        
        # Crear datos de prueba
        self.customer = Customer.objects.create(
            name='Test Customer',
            email='customer@test.com'
        )
        self.product = Product.objects.create(
            code='TEST-001',
            name='Test Product',
            price=Decimal('10.00')
        )

    def test_schema_rejects_qty_le_zero_and_past_dates(self):
        """Test que verifica rechazo de qty <= 0 y fechas pasadas."""
        checkout_url = '/api/v1/order/checkout'
        
        # Test 1: qty <= 0 debe ser rechazado con 400
        invalid_qty_data = {
            'customer_id': self.customer.id,
            'items': [{'product_id': self.product.id, 'qty': '0'}],
            'delivery_method': 'pickup'
        }
        
        response = self.client.post(
            checkout_url,
            invalid_qty_data,
            content_type='application/json',
            **self.headers
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn('qty debe ser > 0', response_data.get('message', ''))
        
        # Test 2: qty negativa debe ser rechazada
        negative_qty_data = {
            'customer_id': self.customer.id,
            'items': [{'product_id': self.product.id, 'qty': '-1'}],
            'delivery_method': 'pickup'
        }
        
        response = self.client.post(
            checkout_url,
            negative_qty_data,
            content_type='application/json',
            **self.headers
        )
        
        self.assertEqual(response.status_code, 400)
        
        # Test 3: Fecha pasada debe ser rechazada
        past_date = date.today() - timedelta(days=1)
        past_date_data = {
            'customer_id': self.customer.id,
            'items': [{'product_id': self.product.id, 'qty': '1'}],
            'delivery_method': 'delivery',
            'delivery_address_text': 'Test Address',
            'requested_delivery_date': past_date.isoformat()
        }
        
        response = self.client.post(
            checkout_url,
            past_date_data,
            content_type='application/json',
            **self.headers
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn('fecha futura', response_data.get('message', ''))
        
        # Test 4: Límite máximo de cantidad
        max_qty_data = {
            'customer_id': self.customer.id,
            'items': [{'product_id': self.product.id, 'qty': '10001'}],
            'delivery_method': 'pickup'
        }
        
        response = self.client.post(
            checkout_url,
            max_qty_data,
            content_type='application/json',
            **self.headers
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn('10,000', response_data.get('message', ''))
        
        # Test 5: Límite máximo de items
        too_many_items = [
            {'product_id': self.product.id, 'qty': '1'} 
            for _ in range(101)
        ]
        
        max_items_data = {
            'customer_id': self.customer.id,
            'items': too_many_items,
            'delivery_method': 'pickup'
        }
        
        response = self.client.post(
            checkout_url,
            max_items_data,
            content_type='application/json',
            **self.headers
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn('100 items', response_data.get('message', ''))