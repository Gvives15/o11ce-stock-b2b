"""
Tests para la API del panel administrativo
Incluye tests de snapshots, casos 422/403 y reintento idempotente
"""

import pytest
import json
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework_simplejwt.tokens import AccessToken

from apps.orders.models import Order, OrderItem
from apps.customers.models import Customer
from apps.catalog.models import Product
from apps.panel.state_mapper import DomainStatus, PanelStatus


class PanelAPITestCase(TestCase):
    """Base test case para la API del panel."""
    
    def setUp(self):
        """Setup común para todos los tests."""
        # Crear usuario con permisos
        self.user = User.objects.create_user(
            username='panel_user',
            password='testpass123',
            is_staff=True
        )
        
        # Crear permiso panel_access
        content_type = ContentType.objects.get_for_model(User)
        self.panel_permission, created = Permission.objects.get_or_create(
            codename='panel_access',
            name='Can access panel',
            content_type=content_type,
        )
        self.user.user_permissions.add(self.panel_permission)
        
        # Crear usuario sin permisos
        self.unauthorized_user = User.objects.create_user(
            username='no_panel_user',
            password='testpass123'
        )
        
        # Crear tokens JWT
        self.access_token = str(AccessToken.for_user(self.user))
        self.unauthorized_token = str(AccessToken.for_user(self.unauthorized_user))
        
        # Crear cliente HTTP
        self.client = Client()
        
        # Crear datos de test
        self.customer = Customer.objects.create(
            name='Test Customer',
            email='test@example.com',
            phone='+1234567890'
        )
        
        self.product = Product.objects.create(
            code='TEST001',
            name='Test Product',
            price=Decimal('10.00')
        )
        
        self.order = Order.objects.create(
            customer=self.customer,
            status=DomainStatus.PLACED.value,
            currency='USD',
            subtotal=Decimal('10.00'),
            tax_total=Decimal('1.00'),
            total=Decimal('11.00'),
            delivery_method='pickup'
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            qty=Decimal('1.00'),
            unit_price=Decimal('10.00')
        )
    
    def get_auth_headers(self, token=None):
        """Helper para obtener headers de autenticación."""
        if token is None:
            token = self.access_token
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}


class TestPanelAuthentication(PanelAPITestCase):
    """Tests de autenticación y autorización."""
    
    def test_health_endpoint_requires_auth(self):
        """Test que el endpoint de health requiere autenticación."""
        response = self.client.get('/api/v1/panel/v1/health')
        self.assertEqual(response.status_code, 401)
    
    def test_health_endpoint_with_valid_token(self):
        """Test endpoint de health con token válido."""
        response = self.client.get(
            '/api/v1/panel/v1/health',
            **self.get_auth_headers()
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['service'], 'panel')
    
    def test_health_endpoint_without_panel_permission(self):
        """Test endpoint de health sin permiso panel_access."""
        response = self.client.get(
            '/api/v1/panel/v1/health',
            **self.get_auth_headers(self.unauthorized_token)
        )
        self.assertEqual(response.status_code, 403)
    
    def test_orders_list_requires_auth(self):
        """Test que el listado de órdenes requiere autenticación."""
        response = self.client.get('/api/v1/panel/v1/orders/')
        self.assertEqual(response.status_code, 401)
    
    def test_orders_list_without_permission(self):
        """Test listado de órdenes sin permiso panel_access."""
        response = self.client.get(
            '/api/v1/panel/v1/orders/',
            **self.get_auth_headers(self.unauthorized_token)
        )
        self.assertEqual(response.status_code, 403)


class TestOrdersListEndpoint(PanelAPITestCase):
    """Tests para el endpoint de listado de órdenes."""
    
    def test_orders_list_success(self):
        """Test listado exitoso de órdenes."""
        response = self.client.get(
            '/api/v1/panel/v1/orders/',
            **self.get_auth_headers()
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('items', data)
        self.assertIn('next_cursor', data)
        self.assertIn('has_next', data)
        
        # Verificar estructura del item
        self.assertEqual(len(data['items']), 1)
        item = data['items'][0]
        self.assertEqual(item['id'], self.order.id)
        self.assertEqual(item['status'], 'NEW')  # Estado del panel
        self.assertEqual(item['customer']['name'], self.customer.name)
    
    def test_orders_list_with_status_filter(self):
        """Test listado con filtro por estado."""
        response = self.client.get(
            '/api/v1/panel/v1/orders/?status=NEW',
            **self.get_auth_headers()
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(len(data['items']), 1)
    
    def test_orders_list_with_invalid_status_filter(self):
        """Test listado con filtro de estado inválido."""
        response = self.client.get(
            '/api/v1/panel/v1/orders/?status=INVALID',
            **self.get_auth_headers()
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(len(data['items']), 0)  # No debe retornar items
    
    def test_orders_list_with_search_by_id(self):
        """Test búsqueda por ID de orden."""
        response = self.client.get(
            f'/api/v1/panel/v1/orders/?q={self.order.id}',
            **self.get_auth_headers()
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(data['items'][0]['id'], self.order.id)
    
    def test_orders_list_with_search_by_customer_name(self):
        """Test búsqueda por nombre de cliente."""
        response = self.client.get(
            '/api/v1/panel/v1/orders/?q=Test Customer',
            **self.get_auth_headers()
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(len(data['items']), 1)
    
    def test_orders_list_pagination(self):
        """Test paginación por cursor."""
        # Crear más órdenes
        for i in range(5):
            Order.objects.create(
                customer=self.customer,
                status=DomainStatus.PLACED.value,
                currency='USD',
                subtotal=Decimal('10.00'),
                tax_total=Decimal('1.00'),
                total=Decimal('11.00'),
                delivery_method='pickup'
            )
        
        # Primera página
        response = self.client.get(
            '/api/v1/panel/v1/orders/?limit=3',
            **self.get_auth_headers()
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(len(data['items']), 3)
        self.assertTrue(data['has_next'])
        self.assertIsNotNone(data['next_cursor'])
        
        # Segunda página
        response = self.client.get(
            f'/api/v1/panel/v1/orders/?limit=3&cursor={data["next_cursor"]}',
            **self.get_auth_headers()
        )
        self.assertEqual(response.status_code, 200)
        
        data2 = response.json()
        self.assertLessEqual(len(data2['items']), 3)


class TestOrderDetailEndpoint(PanelAPITestCase):
    """Tests para el endpoint de detalle de orden."""
    
    def test_order_detail_success(self):
        """Test obtención exitosa de detalle de orden."""
        response = self.client.get(
            f'/api/v1/panel/v1/orders/{self.order.id}',
            **self.get_auth_headers()
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['id'], self.order.id)
        self.assertEqual(data['status'], 'NEW')
        self.assertEqual(data['customer']['name'], self.customer.name)
        self.assertIn('items', data)
        self.assertIn('valid_next_states', data)
        
        # Verificar estados válidos siguientes
        self.assertIn('PICKING', data['valid_next_states'])
        self.assertIn('CANCELLED', data['valid_next_states'])
    
    def test_order_detail_not_found(self):
        """Test orden no encontrada."""
        response = self.client.get(
            '/api/v1/panel/v1/orders/99999',
            **self.get_auth_headers()
        )
        self.assertEqual(response.status_code, 404)
    
    def test_order_detail_unauthorized(self):
        """Test acceso no autorizado al detalle."""
        response = self.client.get(
            f'/api/v1/panel/v1/orders/{self.order.id}',
            **self.get_auth_headers(self.unauthorized_token)
        )
        self.assertEqual(response.status_code, 403)


class TestStatusChangeEndpoint(PanelAPITestCase):
    """Tests para el endpoint de cambio de estado."""
    
    def test_status_change_success(self):
        """Test cambio de estado exitoso."""
        response = self.client.post(
            f'/api/v1/panel/v1/orders/{self.order.id}/status',
            data=json.dumps({
                'status': 'PICKING',
                'reason': 'Starting order processing'
            }),
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='test-key-123',
            **self.get_auth_headers()
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['id'], self.order.id)
        self.assertEqual(data['old_status'], 'NEW')
        self.assertEqual(data['new_status'], 'PICKING')
        self.assertEqual(data['changed_by'], self.user.username)
        
        # Verificar que el estado se actualizó en la base de datos
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, DomainStatus.PROCESSING.value)
    
    def test_status_change_missing_idempotency_key(self):
        """Test cambio de estado sin Idempotency-Key."""
        response = self.client.post(
            f'/api/v1/panel/v1/orders/{self.order.id}/status',
            data=json.dumps({
                'status': 'PICKING',
                'reason': 'Starting order processing'
            }),
            content_type='application/json',
            **self.get_auth_headers()
        )
        self.assertEqual(response.status_code, 400)
        
        data = response.json()
        self.assertIn('detail', data)
        self.assertIn('Idempotency-Key', data['detail'])
    
    def test_status_change_invalid_transition(self):
        """Test transición de estado inválida (422)."""
        response = self.client.post(
            f'/api/v1/panel/v1/orders/{self.order.id}/status',
            data=json.dumps({
                'status': 'DELIVERED',  # Saltar estados
                'reason': 'Invalid transition'
            }),
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='test-key-invalid',
            **self.get_auth_headers()
        )
        self.assertEqual(response.status_code, 422)
        
        data = response.json()
        self.assertIn('detail', data)
        self.assertIn('Transición inválida', data['detail'])
    
    def test_status_change_invalid_status_value(self):
        """Test valor de estado inválido (422)."""
        response = self.client.post(
            f'/api/v1/panel/v1/orders/{self.order.id}/status',
            data=json.dumps({
                'status': 'INVALID_STATUS',
                'reason': 'Invalid status'
            }),
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='test-key-invalid-status',
            **self.get_auth_headers()
        )
        self.assertEqual(response.status_code, 422)
        
        data = response.json()
        self.assertIn('detail', data)
        self.assertIn('NEW → INVALID_STATUS', data['detail'])
    
    def test_status_change_unauthorized(self):
        """Test cambio de estado sin autorización (403)."""
        response = self.client.post(
            f'/api/v1/panel/v1/orders/{self.order.id}/status',
            data=json.dumps({
                'status': 'PICKING',
                'reason': 'Unauthorized attempt'
            }),
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='test-key-unauth',
            **self.get_auth_headers(self.unauthorized_token)
        )
        self.assertEqual(response.status_code, 403)
    
    def test_status_change_idempotent_retry(self):
        """Test reintento idempotente."""
        # Primer cambio
        response1 = self.client.post(
            f'/api/v1/panel/v1/orders/{self.order.id}/status',
            data=json.dumps({
                'status': 'PICKING',
                'reason': 'First attempt'
            }),
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='test-key-idempotent',
            **self.get_auth_headers()
        )
        self.assertEqual(response1.status_code, 200)
        
        # Segundo intento con la misma clave (idempotente)
        response2 = self.client.post(
            f'/api/v1/panel/v1/orders/{self.order.id}/status',
            data=json.dumps({
                'status': 'PICKING',
                'reason': 'Second attempt (should be idempotent)'
            }),
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='test-key-idempotent',
            **self.get_auth_headers()
        )
        self.assertEqual(response2.status_code, 200)
        
        # Ambas respuestas deben ser iguales
        data1 = response1.json()
        data2 = response2.json()
        self.assertEqual(data1['old_status'], data2['old_status'])
        self.assertEqual(data1['new_status'], data2['new_status'])
    
    def test_status_change_order_not_found(self):
        """Test cambio de estado en orden inexistente."""
        response = self.client.post(
            '/api/v1/panel/v1/orders/99999/status',
            data=json.dumps({
                'status': 'PICKING',
                'reason': 'Order not found'
            }),
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='test-key-not-found',
            **self.get_auth_headers()
        )
        self.assertEqual(response.status_code, 404)


class TestAPISnapshots(PanelAPITestCase):
    """Tests de snapshots para verificar estructura de respuestas."""
    
    def test_orders_list_response_structure(self):
        """Test estructura de respuesta del listado de órdenes."""
        response = self.client.get(
            '/api/v1/panel/v1/orders/',
            **self.get_auth_headers()
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        
        # Estructura principal
        expected_keys = {'items', 'next_cursor', 'has_next'}
        self.assertEqual(set(data.keys()), expected_keys)
        
        # Estructura del item
        if data['items']:
            item = data['items'][0]
            expected_item_keys = {
                'id', 'customer', 'status', 'total', 'delivery_method',
                'requested_delivery_date', 'created_at', 'items_count'
            }
            self.assertEqual(set(item.keys()), expected_item_keys)
            
            # Estructura del customer
            customer = item['customer']
            expected_customer_keys = {'id', 'name', 'email', 'phone'}
            self.assertEqual(set(customer.keys()), expected_customer_keys)
    
    def test_order_detail_response_structure(self):
        """Test estructura de respuesta del detalle de orden."""
        response = self.client.get(
            f'/api/v1/panel/v1/orders/{self.order.id}',
            **self.get_auth_headers()
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        
        # Estructura principal
        expected_keys = {
            'id', 'customer', 'status', 'currency', 'subtotal', 'discount_total',
            'tax_total', 'total', 'delivery_method', 'delivery_address_text',
            'delivery_window_from', 'delivery_window_to', 'delivery_instructions',
            'requested_delivery_date', 'created_at', 'items', 'valid_next_states'
        }
        self.assertEqual(set(data.keys()), expected_keys)
        
        # Estructura de los items
        if data['items']:
            item = data['items'][0]
            expected_item_keys = {
                'id', 'product_code', 'product_name', 'qty',
                'unit_price', 'total_price'
            }
            self.assertEqual(set(item.keys()), expected_item_keys)
    
    def test_status_change_response_structure(self):
        """Test estructura de respuesta del cambio de estado."""
        response = self.client.post(
            f'/api/v1/panel/v1/orders/{self.order.id}/status',
            data=json.dumps({
                'status': 'PICKING',
                'reason': 'Test status change'
            }),
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='test-key-structure',
            **self.get_auth_headers()
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        
        # Estructura de respuesta
        expected_keys = {'id', 'old_status', 'new_status', 'changed_at', 'changed_by'}
        self.assertEqual(set(data.keys()), expected_keys)


@pytest.mark.django_db
class TestPanelAPILogging:
    """Tests para verificar el logging de la API."""
    
    def test_orders_list_logging(self):
        """Test logging del endpoint de listado."""
        # Este test verificaría que se generen los logs apropiados
        # En un entorno real, se usaría un mock del logger
        pass
    
    def test_status_change_logging(self):
        """Test logging del cambio de estado."""
        # Este test verificaría que se logueen las transiciones
        # En un entorno real, se usaría un mock del logger
        pass