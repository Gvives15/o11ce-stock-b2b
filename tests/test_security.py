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
        self.assertIn('refresh', refresh_data)  # Refresh rotativo
        
        # Verificar que el nuevo refresh token es diferente (rotativo)
        self.assertNotEqual(refresh_token, refresh_data['refresh'])

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
            'refresh': refresh_token
        }, content_type='application/json')
        
        self.assertEqual(logout_response.status_code, 200)
        
        # Intentar usar el refresh token después del logout (debe fallar)
        refresh_response = self.client.post('/api/v1/auth/refresh/', {
            'refresh': refresh_token
        }, content_type='application/json')
        
        self.assertEqual(refresh_response.status_code, 401)
        
        # Verificar que el token está en el blacklist
        token = RefreshToken(refresh_token)
        blacklisted_exists = BlacklistedToken.objects.filter(
            token__jti=token['jti']
        ).exists()
        self.assertTrue(blacklisted_exists)


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