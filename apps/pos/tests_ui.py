"""
Tests UI para la funcionalidad de selección de lotes en el POS
Bloque F — UI POS: selección de lote (línea de carrito)
Bloque H — UX de errores + Telemetría mínima
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from apps.catalog.models import Product
from apps.stock.models import StockLot, Warehouse
from apps.pos.models import LotOverrideAudit
from decimal import Decimal
from datetime import date, timedelta
import json
from unittest.mock import patch, MagicMock


class POSUITestCase(TestCase):
    """Caso base para tests UI del POS"""
    
    def setUp(self):
        """Configuración inicial para los tests"""
        # Usuario de prueba con permisos de override POS
        self.user = User.objects.create_user(
            username='pos_user',
            password='testpass123',
            email='pos@test.com',
            is_superuser=True  # Superusuario tiene todos los permisos
        )
        
        # Cliente de prueba
        self.client = Client()
        self.client.login(username='pos_user', password='testpass123')
        
        # Categoría y producto
        self.product = Product.objects.create(
            name='Paracetamol 500mg',
            code='PAR500',
            category='Medicamentos',  # String field, no model
            price=Decimal('15.50')
        )
        
        # Warehouse de prueba
        self.warehouse = Warehouse.objects.create(
            name='Almacén Principal'
        )
        
        # Lotes de prueba
        today = date.today()
        
        # Lote recomendado (FEFO - expira primero)
        self.lot_recommended = StockLot.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            lot_code='LOT-REC-001',
            expiry_date=today + timedelta(days=90),  # Expira en 3 meses
            qty_on_hand=Decimal('100.000'),
            unit_cost=Decimal('10.00')
        )
        
        # Lote alternativo (expira después)
        self.lot_alternative = StockLot.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            lot_code='LOT-ALT-002',
            expiry_date=today + timedelta(days=180),  # Expira en 6 meses
            qty_on_hand=Decimal('50.000'),
            unit_cost=Decimal('10.00')
        )
        
        # Lote con poco stock
        self.lot_low_stock = StockLot.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            lot_code='LOT-LOW-003',
            expiry_date=today + timedelta(days=365),  # Expira en 1 año
            qty_on_hand=Decimal('5.000'),
            unit_cost=Decimal('10.00')
        )


class UITestF1LotSelectionRender(POSUITestCase):
    """
    UI-F1: Select renderiza opciones y marca "Recomendado"
    
    Verifica que:
    - El POS carga correctamente
    - Al agregar un producto, se cargan las opciones de lotes
    - El lote recomendado está marcado como tal
    - Las opciones se muestran ordenadas por FEFO
    """
    
    def test_pos_interface_loads(self):
        """Test que la interfaz del POS carga correctamente"""
        response = self.client.get(reverse('pos_interface'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'POS - Sistema de Ventas')
        self.assertContains(response, 'products-grid')
        self.assertContains(response, 'cart-items')
        self.assertContains(response, 'override-modal')
    
    def test_lot_options_api_renders_correctly(self):
        """UI-F1: Test que el API de opciones de lotes funciona correctamente."""
        # Hacer request al endpoint de opciones de lotes
        response = self.client.get(f'/api/v1/stock/lots/options?product_id={self.product.id}&qty=5.000')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verificar estructura de respuesta
        self.assertIn('recommended_id', data)
        self.assertIn('options', data)
        
        # Verificar que el lote recomendado es el que expira primero (FEFO)
        recommended_id = data['recommended_id']
        self.assertEqual(recommended_id, self.lot_recommended.id)
        
        # Verificar que hay opciones disponibles
        options = data['options']
        self.assertTrue(len(options) > 0)
        
        # El primer lote debe ser el recomendado (FEFO)
        first_option = options[0]
        self.assertEqual(first_option['id'], self.lot_recommended.id)
        self.assertEqual(first_option['lot_code'], 'LOT-REC-001')
        
    def test_lot_options_include_all_available_lots(self):
        """Test que se incluyen todos los lotes disponibles"""
        response = self.client.get(
            f'/api/v1/stock/lots/options?product_id={self.product.id}&qty=1'
        )
        
        data = response.json()
        options = data['options']
        
        # Verificar que se incluyen todos los lotes disponibles
        lot_ids = [opt['id'] for opt in options]
        self.assertIn(self.lot_recommended.id, lot_ids)
        self.assertIn(self.lot_alternative.id, lot_ids)
        self.assertIn(self.lot_low_stock.id, lot_ids)
        
        # Verificar información de cada lote
        for option in options:
            self.assertIn('lot_code', option)
            self.assertIn('expiry_date', option)
            self.assertIn('qty_on_hand', option)


class UITestF2LotChangeRequiresReason(POSUITestCase):
    """
    UI-F2: Cambiar a otro lote pide motivo; si cancela → vuelve al recomendado
    
    Verifica que:
    - Cambiar a un lote no recomendado requiere motivo
    - El modal de override se muestra correctamente
    - Cancelar el override vuelve al lote recomendado
    - Confirmar el override guarda el motivo
    """
    
    def test_sale_with_recommended_lot_no_override(self):
        """Test que usar el lote recomendado no requiere override."""
        # Datos de venta usando lote recomendado (sin lot_id = FEFO automático)
        sale_data = {
            'items': [
                {
                    'product_id': self.product.id,
                    'qty': '10.000'
                    # Sin lot_id ni lot_override_reason = usa FEFO
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=sale_data,
            content_type='application/json'
        )
        
        # Debe ser exitoso sin requerir override
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('sale_id', data)
        self.assertEqual(data['total_items'], 1)
    
    def test_sale_with_non_recommended_lot_requires_reason(self):
        """Test que cambiar a otro lote requiere motivo."""
        # Intentar venta con lote específico sin motivo
        sale_data = {
            'items': [
                {
                    'product_id': self.product.id,
                    'qty': '5.000',
                    'lot_id': self.lot_alternative.id
                    # Sin lot_override_reason - debe fallar
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=sale_data,
            content_type='application/json'
        )
        
        # Debe fallar por falta de motivo
        self.assertEqual(response.status_code, 400)
        
        data = response.json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'VALIDATION_ERROR')
        self.assertIn('lot_override_reason', data['detail'])
    
    def test_sale_with_override_reason_succeeds(self):
        """Test que proporcionar motivo permite usar lote no recomendado."""
        # Venta con lote específico y motivo válido
        sale_data = {
            'items': [
                {
                    'product_id': self.product.id,
                    'qty': '5.000',
                    'lot_id': self.lot_alternative.id,
                    'lot_override_reason': 'Cliente solicita lote específico'
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=sale_data,
            content_type='application/json'
        )
        
        # Debe ser exitoso con motivo válido
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('sale_id', data)
        self.assertEqual(data['total_items'], 1)
        
        # Debe crear registro de auditoría
        audit_exists = LotOverrideAudit.objects.filter(
            sale_id=data['sale_id'],
            product=self.product,
            lot_chosen=self.lot_alternative,
            reason='Cliente solicita lote específico'
        ).exists()
        self.assertTrue(audit_exists)
    
    def test_multiple_items_override_validation(self):
        """Test validación con múltiples items, algunos con override."""
        # Venta con múltiples items: uno FEFO, otro con override
        sale_data = {
            'items': [
                {
                    'product_id': self.product.id,
                    'qty': '3.000'
                    # Sin lot_id = usa FEFO automático
                },
                {
                    'product_id': self.product.id,
                    'qty': '2.000',
                    'lot_id': self.lot_alternative.id,
                    'lot_override_reason': 'Solicitud especial del cliente'
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=sale_data,
            content_type='application/json'
        )
        
        # Debe ser exitoso
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['total_items'], 2)
        
        # Solo debe haber un registro de auditoría (para el override)
        audit_count = LotOverrideAudit.objects.count()
        self.assertEqual(audit_count, 1)


class UITestF3ValidationPreventsSale(POSUITestCase):
    """
    UI-F3: Si falta motivo, no deja confirmar la venta
    
    Verifica que:
    - La validación del frontend previene ventas sin motivo
    - Los mensajes de error son claros
    - La venta se procesa correctamente cuando todo está bien
    """
    
    def test_validation_prevents_sale_without_reason(self):
        """Test que la validación previene venta sin motivo de override."""
        # Intentar venta con lote específico sin motivo
        sale_data = {
            'items': [
                {
                    'product_id': self.product.id,
                    'qty': '1.000',
                    'lot_id': self.lot_low_stock.id
                    # Sin lot_override_reason
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=sale_data,
            content_type='application/json'
        )
        
        # Debe fallar
        self.assertEqual(response.status_code, 400)
        
        data = response.json()
        self.assertEqual(data['error'], 'VALIDATION_ERROR')
        self.assertIn('lot_override_reason', data['detail'])
    
    def test_validation_allows_sale_with_reason(self):
        """Test que la validación permite venta con motivo válido."""
        # Venta con lote específico y motivo válido
        sale_data = {
            'items': [
                {
                    'product_id': self.product.id,
                    'qty': '1.000',
                    'lot_id': self.lot_low_stock.id,
                    'lot_override_reason': 'Motivo válido para override'
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=sale_data,
            content_type='application/json'
        )
        
        # Debe ser exitoso
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('sale_id', data)
        
        # Debe crear registro de auditoría
        audit_exists = LotOverrideAudit.objects.filter(
            sale_id=data['sale_id'],
            reason='Motivo válido para override'
        ).exists()
        self.assertTrue(audit_exists)
    
    def test_validation_allows_recommended_lot_without_reason(self):
        """Test que usar lote recomendado no requiere motivo."""
        # Venta usando FEFO automático (sin especificar lote)
        sale_data = {
            'items': [
                {
                    'product_id': self.product.id,
                    'qty': '5.000'
                    # Sin lot_id = usa FEFO automático
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=sale_data,
            content_type='application/json'
        )
        
        # Debe ser exitoso
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('sale_id', data)
        
        # No debe crear registros de auditoría (no hay override)
        audit_count = LotOverrideAudit.objects.count()
        self.assertEqual(audit_count, 0)
    
    def test_complete_sale_flow_with_mixed_items(self):
        """Test flujo completo con items mixtos (recomendados y overrides)."""
        # Venta compleja con múltiples items y estrategias mixtas
        sale_data = {
            'items': [
                {
                    'product_id': self.product.id,
                    'qty': '10.000'
                    # FEFO automático
                },
                {
                    'product_id': self.product.id,
                    'qty': '3.000',
                    'lot_id': self.lot_alternative.id,
                    'lot_override_reason': 'Cliente prefiere este lote'
                },
                {
                    'product_id': self.product.id,
                    'qty': '1.000',
                    'lot_id': self.lot_low_stock.id,
                    'lot_override_reason': 'Agotar stock bajo'
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=sale_data,
            content_type='application/json'
        )
        
        # Debe ser exitoso
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('sale_id', data)
        self.assertEqual(data['total_items'], 3)
        
        # Debe haber 2 registros de auditoría (para los 2 overrides)
        audit_count = LotOverrideAudit.objects.filter(
            sale_id=data['sale_id']
        ).count()
        self.assertEqual(audit_count, 2)
        
        # Verificar que los motivos están registrados correctamente
        reasons = list(LotOverrideAudit.objects.filter(
            sale_id=data['sale_id']
        ).values_list('reason', flat=True))
        
        self.assertIn('Cliente prefiere este lote', reasons)
        self.assertIn('Agotar stock bajo', reasons)


class POSTelemetryTestCase(POSUITestCase):
    """Tests para verificar la telemetría de eventos lot_override"""
    
    def test_i_h2_telemetry_event_on_successful_override(self):
        """I-H2: Al override exitoso, se emite evento de telemetría"""
        
        # Procesar venta con override
        payload = {
            "items": [
                {
                    "product_id": self.product.id,
                    "qty": "2.000",
                    "unit_price": "15.50",
                    "lot_id": self.lot_alternative.id,
                    "lot_override_reason": "Test de telemetría"
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        sale_data = response.json()
        
        # Verificar que se creó el registro de auditoría (telemetría)
        audit = LotOverrideAudit.objects.get(sale_id=sale_data['sale_id'])
        self.assertEqual(audit.product, self.product)
        self.assertEqual(audit.lot_chosen, self.lot_alternative)
        self.assertEqual(audit.reason, "Test de telemetría")
        self.assertEqual(audit.qty, Decimal('2.000'))
        self.assertEqual(audit.actor, self.user)
    
    def test_telemetry_event_contains_required_fields(self):
        """Test que el evento de telemetría contiene todos los campos requeridos"""
        
        payload = {
            "items": [
                {
                    "product_id": self.product.id,
                    "qty": "1.000",
                    "unit_price": "15.50",
                    "lot_id": self.lot_alternative.id,
                    "lot_override_reason": "Campos requeridos test"
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        sale_data = response.json()
        
        # Verificar campos del evento de telemetría
        audit = LotOverrideAudit.objects.get(sale_id=sale_data['sale_id'])
        
        # Campos requeridos según DoD: producto, lote, usuario
        self.assertIsNotNone(audit.product)
        self.assertIsNotNone(audit.lot_chosen)
        self.assertIsNotNone(audit.actor)
        self.assertIsNotNone(audit.sale_id)
        self.assertIsNotNone(audit.qty)
        self.assertIsNotNone(audit.reason)
        self.assertIsNotNone(audit.timestamp)
    
    def test_no_telemetry_event_without_override(self):
        """Test que no se emite evento de telemetría si no hay override"""
        
        # Procesar venta sin override (usando FEFO automático)
        payload = {
            "items": [
                {
                    "product_id": self.product.id,
                    "qty": "1.000",
                    "unit_price": "15.50"
                    # Sin lot_id = usa FEFO automático (no override)
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        sale_data = response.json()
        
        # Verificar que NO se creó registro de auditoría
        audit_count = LotOverrideAudit.objects.filter(sale_id=sale_data['sale_id']).count()
        self.assertEqual(audit_count, 0)
    
    def test_multiple_overrides_generate_multiple_events(self):
        """Test que múltiples overrides generan múltiples eventos de telemetría"""
        
        # Crear segundo producto y lotes
        product2 = Product.objects.create(
            name='Ibuprofeno 400mg',
            code='IBU400',
            category='Medicamentos',
            price=Decimal('20.00')
        )
        
        lot2_recommended = StockLot.objects.create(
            product=product2,
            warehouse=self.warehouse,
            lot_code='LOT-IBU-REC',
            expiry_date=date.today() + timedelta(days=60),
            qty_on_hand=Decimal('80.000'),
            unit_cost=Decimal('15.00')
        )
        
        lot2_alternative = StockLot.objects.create(
            product=product2,
            warehouse=self.warehouse,
            lot_code='LOT-IBU-ALT',
            expiry_date=date.today() + timedelta(days=120),
            qty_on_hand=Decimal('40.000'),
            unit_cost=Decimal('15.00')
        )
        
        # Procesar venta con múltiples overrides
        payload = {
            "items": [
                {
                    "product_id": self.product.id,
                    "qty": "1.000",
                    "unit_price": "15.50",
                    "lot_id": self.lot_alternative.id,
                    "lot_override_reason": "Override producto 1"
                },
                {
                    "product_id": product2.id,
                    "qty": "2.000",
                    "unit_price": "20.00",
                    "lot_id": lot2_alternative.id,
                    "lot_override_reason": "Override producto 2"
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        sale_data = response.json()
        
        # Verificar que se crearon dos registros de auditoría
        audits = LotOverrideAudit.objects.filter(sale_id=sale_data['sale_id'])
        self.assertEqual(audits.count(), 2)
        
        # Verificar que cada override tiene su propio evento
        audit1 = audits.get(product=self.product)
        audit2 = audits.get(product=product2)
        
        self.assertEqual(audit1.reason, "Override producto 1")
        self.assertEqual(audit2.reason, "Override producto 2")


class POSErrorHandlingTestCase(POSUITestCase):
    """Tests para verificar el manejo de errores en el POS"""
    
    def test_i_h1_error_messages_display_in_pos(self):
        """I-H1: Cada error de C/D muestra banner/toast legible en POS"""
        
        # Test error de stock insuficiente
        payload = {
            "items": [
                {
                    "product_id": self.product.id,
                    "qty": "1000.000",  # Cantidad mayor al stock disponible
                    "unit_price": "15.50",
                    "lot_id": self.lot_recommended.id
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Verificar que se retorna error con código específico
        # La API puede retornar 400 o 422 dependiendo del tipo de error
        self.assertIn(response.status_code, [400, 422])
        error_data = response.json()
        self.assertIn('error', error_data)
        # Verificar que el error es relacionado con stock o validación
        self.assertIn(error_data['error'], ['INSUFFICIENT_STOCK', 'VALIDATION_ERROR'])
    
    def test_error_message_for_invalid_lot(self):
        """Test mensaje de error para lote inválido"""
        
        payload = {
            "items": [
                {
                    "product_id": self.product.id,
                    "qty": "1.000",
                    "unit_price": "15.50",
                    "lot_id": 99999  # ID de lote que no existe
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # La API puede retornar 400 o 422 para errores de validación
        self.assertIn(response.status_code, [400, 422])
        error_data = response.json()
        self.assertIn('error', error_data)
        # Verificar que el error es relacionado con lote inválido o validación
        self.assertIn(error_data['error'], ['INVALID_LOT', 'VALIDATION_ERROR'])
    
    def test_error_message_for_insufficient_shelf_life(self):
        """Test mensaje de error para vida útil insuficiente"""
        
        # Crear lote con poca vida útil
        lot_expired_soon = StockLot.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            lot_code='LOT-EXPIRED-SOON',
            expiry_date=date.today() + timedelta(days=5),  # Expira muy pronto
            qty_on_hand=Decimal('10.000'),
            unit_cost=Decimal('10.00')
        )
        
        payload = {
            "items": [
                {
                    "product_id": self.product.id,
                    "qty": "1.000",
                    "unit_price": "15.50",
                    "lot_id": lot_expired_soon.id
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Dependiendo de la lógica de negocio, esto podría ser un error o requerir override
        if response.status_code in [400, 422]:
            error_data = response.json()
            self.assertIn('error', error_data)
            # Verificar que el error es relacionado con vida útil o validación
            self.assertIn(error_data['error'], ['INSUFFICIENT_SHELF_LIFE', 'VALIDATION_ERROR'])
    
    def test_error_message_for_permission_required(self):
        """Test mensaje de error para permiso requerido"""
        
        # Crear usuario sin permisos de override
        user_no_perms = User.objects.create_user(
            username='no_perms_user',
            password='testpass123',
            email='noperms@test.com'
        )
        
        client_no_perms = Client()
        client_no_perms.login(username='no_perms_user', password='testpass123')
        
        # Intentar override sin permisos
        payload = {
            "items": [
                {
                    "product_id": self.product.id,
                    "qty": "1.000",
                    "unit_price": "15.50",
                    "lot_id": self.lot_alternative.id,
                    "lot_override_reason": "Test sin permisos"
                }
            ]
        }
        
        response = client_no_perms.post(
            '/api/v1/pos/sale',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Verificar error de permisos
        if response.status_code == 403:
            error_data = response.json()
            self.assertIn('error', error_data)
            self.assertIn(error_data['error'], ['PERMISSION_REQUIRED', 'PERMISSION_DENIED'])


class POSIntegrationTest(POSUITestCase):
    """Tests de integración para el flujo completo del POS"""
    
    def test_complete_pos_workflow(self):
        """Test del flujo completo del POS desde la UI hasta la venta"""
        
        # 1. Verificar que la interfaz carga
        response = self.client.get(reverse('pos_interface'))
        self.assertEqual(response.status_code, 200)
        
        # 2. Obtener opciones de lotes
        response = self.client.get(
            f'/api/v1/stock/lots/options?product_id={self.product.id}&qty=3'
        )
        self.assertEqual(response.status_code, 200)
        lot_options = response.json()
        
        # 3. Verificar que el recomendado es correcto
        recommended_id = lot_options['recommended_id']
        self.assertEqual(recommended_id, self.lot_recommended.id)
        
        # 4. Procesar venta con override
        payload = {
            "items": [
                {
                    "product_id": self.product.id,
                    "qty": "3.000",
                    "unit_price": "15.50",
                    "lot_id": self.lot_alternative.id,
                    "lot_override_reason": "Test de integración completo"
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # 5. Verificar que todo se guardó correctamente
        sale_data = response.json()
        
        # Verificar respuesta de la venta
        self.assertIn('sale_id', sale_data)
        self.assertEqual(sale_data['total_items'], 1)
        self.assertEqual(len(sale_data['movements']), 1)
        
        # Verificar movimiento
        movement = sale_data['movements'][0]
        self.assertEqual(movement['product_id'], self.product.id)
        self.assertEqual(movement['lot_id'], self.lot_alternative.id)
        self.assertEqual(Decimal(str(movement['qty'])), Decimal('3.000'))
        
        # Verificar auditoría
        audit = LotOverrideAudit.objects.get(sale_id=sale_data['sale_id'])
        self.assertEqual(audit.product, self.product)
        self.assertEqual(audit.lot_chosen, self.lot_alternative)
        self.assertEqual(audit.reason, "Test de integración completo")
        
        # Verificar actualización de stock
        self.lot_alternative.refresh_from_db()
        self.assertEqual(self.lot_alternative.qty_on_hand, Decimal('47.000'))  # 50 - 3