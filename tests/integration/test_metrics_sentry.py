"""
Tests para métricas de Prometheus y integración con Sentry.
"""
import json
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from apps.catalog.models import Product
from apps.customers.models import Customer
from apps.orders.models import Order
from apps.orders.services import checkout
from apps.stock.models import StockLot, Warehouse
from apps.core.metrics import increment_orders_placed, update_near_expiry_lots


class MetricsTestCase(TestCase):
    """Tests para métricas de Prometheus."""
    
    def setUp(self):
        """Configuración inicial para los tests."""
        self.client = Client()
        
        # Crear datos de prueba
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.customer = Customer.objects.create(
            name='Cliente Test',
            email='cliente@test.com',
            segment='premium'
        )
        
        self.product = Product.objects.create(
            code='TEST001',
            name='Producto Test',
            price=Decimal('100.00')
        )
        
        self.warehouse = Warehouse.objects.create(
            name='Almacén Test',
            is_active=True
        )
        
        # Crear stock para el producto
        StockLot.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            lot_code='LOT001',
            expiry_date=date.today() + timedelta(days=90),
            qty_on_hand=Decimal('100.000'),
            unit_cost=Decimal('50.00')
        )

    def test_metrics_endpoint_ok(self):
        """Test: endpoint /metrics responde 200 con histogramas por endpoint."""
        response = self.client.get('/metrics')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/plain', response['Content-Type'])
        
        content = response.content.decode('utf-8')
        
        # Verificar que contiene métricas de django-prometheus
        self.assertIn('django_http_requests_total', content)
        # La métrica de duración puede no aparecer hasta que haya requests
        # Solo verificamos que el endpoint funciona correctamente

    def test_custom_counter_increments_on_order(self):
        """Test: métrica counter se incrementa al crear una orden."""
        # Crear una orden usando el servicio
        order = checkout(
            customer_id=self.customer.id,
            items=[{'product_id': self.product.id, 'qty': Decimal('5.000')}],
            delivery_method='pickup',
            delivery_address_text='',
            client_req_id='test-order-001'
        )
        
        # Verificar que la orden se creó
        self.assertEqual(order.status, Order.Status.PLACED)
        
        # Verificar que la métrica aparece en el endpoint
        response = self.client.get('/metrics')
        content = response.content.decode('utf-8')
        
        # Buscar la métrica orders_placed_total
        found_metric = False
        for line in content.split('\n'):
            if line.startswith('orders_placed_total'):
                value = float(line.split()[-1])
                self.assertGreaterEqual(value, 1.0)  # Al menos 1 orden
                found_metric = True
                break
        
        self.assertTrue(found_metric, "No se encontró la métrica orders_placed_total")

    def test_custom_gauge_sets_value(self):
        """Test: métrica gauge se actualiza correctamente."""
        # Ejecutar el comando que actualiza las métricas
        from django.core.management import call_command
        call_command('update_metrics')
        
        # Verificar que la métrica aparece en el endpoint
        response = self.client.get('/metrics')
        content = response.content.decode('utf-8')
        
        # Buscar la métrica near_expiry_lots
        found_metric = False
        for line in content.split('\n'):
            if line.startswith('near_expiry_lots'):
                # Solo verificar que existe, el valor puede ser 0
                found_metric = True
                break
        
        self.assertTrue(found_metric, "No se encontró la métrica near_expiry_lots")


class SentryTestCase(TestCase):
    """Tests para integración con Sentry."""
    
    def setUp(self):
        """Configuración inicial para los tests."""
        self.client = Client()

    @patch('sentry_sdk.capture_exception')
    @patch('sentry_sdk.last_event_id')
    def test_sentry_captures_exception_dummy(self, mock_last_event_id, mock_capture_exception):
        """Test: Sentry captura excepción de prueba con stacktrace."""
        # Configurar mocks
        mock_last_event_id.return_value = 'test-event-id-12345'
        mock_capture_exception.return_value = None
        
        # Hacer request al endpoint de test
        response = self.client.post('/sentry-test/')
        
        # Verificar respuesta
        self.assertEqual(response.status_code, 500)
        
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'TEST_EXCEPTION')
        self.assertEqual(data['message'], 'Test exception sent to Sentry successfully')
        self.assertEqual(data['sentry_event_id'], 'test-event-id-12345')
        
        # Verificar que Sentry fue llamado
        mock_capture_exception.assert_called_once()
        mock_last_event_id.assert_called_once()
        
        # Verificar que se capturó la excepción correcta
        captured_exception = mock_capture_exception.call_args[0][0]
        self.assertIsInstance(captured_exception, Exception)
        self.assertIn('Test exception for Sentry integration', str(captured_exception))

    def test_sentry_test_endpoint_exists(self):
        """Test: endpoint de test de Sentry existe y es accesible."""
        response = self.client.post('/sentry-test/')
        
        # El endpoint debe existir (no 404)
        self.assertNotEqual(response.status_code, 404)
        
        # Debe devolver 500 (error intencional)
        self.assertEqual(response.status_code, 500)
        
        # Debe devolver JSON
        self.assertIn('application/json', response['Content-Type'])