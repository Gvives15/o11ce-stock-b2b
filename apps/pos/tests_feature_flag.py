"""
Tests para el Bloque I — Feature Flag
FEATURE_LOT_OVERRIDE=true/false oculta select en UI y backend ignora lot_id si está en false.
"""

from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from apps.catalog.models import Product
from apps.stock.models import StockLot, Warehouse
from apps.stock.services import record_entry
from apps.customers.models import Customer
from decimal import Decimal
from datetime import date, timedelta
import json


class FeatureFlagTestCase(TestCase):
    """Caso base para tests del feature flag FEATURE_LOT_OVERRIDE"""
    
    def setUp(self):
        """Configuración inicial para los tests"""
        # Usuario de prueba
        self.user = User.objects.create_user(
            username='pos_user',
            password='testpass123',
            email='pos@test.com',
            is_superuser=True
        )
        
        # Cliente de prueba
        self.client = Client()
        self.client.login(username='pos_user', password='testpass123')
        
        # Warehouse de prueba
        self.warehouse = Warehouse.objects.create(
            name='Almacén Principal',
            is_active=True
        )
        
        # Producto P1 según fixture mínimo
        self.product_p1 = Product.objects.create(
            name='Producto P1',
            code='P1',
            category='Test',
            price=Decimal('10.00')
        )
        
        # Cliente C1 con min_shelf_life_days=30
        self.customer_c1 = Customer.objects.create(
            name='Cliente C1',
            segment=Customer.Segment.RETAIL,
            min_shelf_life_days=30
        )
        
        # Crear lotes según fixture mínimo
        today = date.today()
        
        # Lote L1: vence "2025-10-01", stock 5
        self.lot_l1 = record_entry(
            product_id=self.product_p1.id,
            lot_code='L1',
            expiry_date=date(2025, 10, 1),
            qty=Decimal('5.000'),
            unit_cost=Decimal('8.00'),
            user_id=self.user.id,
            warehouse_id=self.warehouse.id
        ).lot
        
        # Lote L2: vence "2026-01-01", stock 10
        self.lot_l2 = record_entry(
            product_id=self.product_p1.id,
            lot_code='L2',
            expiry_date=date(2026, 1, 1),
            qty=Decimal('10.000'),
            unit_cost=Decimal('8.00'),
            user_id=self.user.id,
            warehouse_id=self.warehouse.id
        ).lot
        
        # Lote L3 (QC/reservado) para tests de bloqueo
        entry_l3 = record_entry(
            product_id=self.product_p1.id,
            lot_code='L3',
            expiry_date=date(2026, 6, 1),
            qty=Decimal('8.000'),
            unit_cost=Decimal('8.00'),
            user_id=self.user.id,
            warehouse_id=self.warehouse.id
        )
        self.lot_l3 = entry_l3.lot
        self.lot_l3.is_quarantined = True
        self.lot_l3.save()


@override_settings(FEATURE_LOT_OVERRIDE=False)
class TestI1FlagOFF(FeatureFlagTestCase):
    """I-I1: Flag OFF - UI sin select; backend ignora lot_id → FEFO"""
    
    def test_ui_without_lot_select_flag_off(self):
        """Test que la UI no muestra select de lotes cuando flag=False"""
        response = self.client.get(reverse('pos_interface'))
        
        self.assertEqual(response.status_code, 200)
        # Verificar que el feature flag se pasa correctamente al template
        self.assertContains(response, 'window.FEATURE_LOT_OVERRIDE = false')
        
    def test_backend_ignores_lot_id_flag_off(self):
        """Test que el backend ignora lot_id cuando flag=False y usa FEFO"""
        # Intentar venta especificando L2 (que no es FEFO)
        payload = {
            "items": [
                {
                    "product_id": self.product_p1.id,
                    "qty": "2.000",
                    "unit_price": "10.00",
                    "lot_id": self.lot_l2.id  # Especificamos L2, pero debería usar L1 (FEFO)
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
        
        # Verificar que se usó L1 (FEFO) en lugar de L2
        movement = sale_data['movements'][0]
        self.assertEqual(movement['lot_id'], self.lot_l1.id)
        self.assertEqual(movement['lot_code'], 'L1')
        
        # Verificar que el stock se redujo del lote correcto
        self.lot_l1.refresh_from_db()
        self.lot_l2.refresh_from_db()
        self.assertEqual(self.lot_l1.qty_on_hand, Decimal('3.000'))  # 5 - 2
        self.assertEqual(self.lot_l2.qty_on_hand, Decimal('10.000'))  # Sin cambios
        
    def test_fefo_logic_preserved_flag_off(self):
        """Test que la lógica FEFO se mantiene cuando flag=False"""
        # Venta sin especificar lot_id
        payload = {
            "items": [
                {
                    "product_id": self.product_p1.id,
                    "qty": "3.000",
                    "unit_price": "10.00"
                    # Sin lot_id
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
        
        # Verificar que se usó L1 (FEFO - expira primero)
        movement = sale_data['movements'][0]
        self.assertEqual(movement['lot_id'], self.lot_l1.id)
        self.assertEqual(movement['lot_code'], 'L1')


@override_settings(FEATURE_LOT_OVERRIDE=True)
class TestI2FlagON(FeatureFlagTestCase):
    """I-I2: Flag ON - UI con select; override permitido (según permisos)"""
    
    def test_ui_with_lot_select_flag_on(self):
        """Test que la UI muestra select de lotes cuando flag=True"""
        response = self.client.get(reverse('pos_interface'))
        
        self.assertEqual(response.status_code, 200)
        # Verificar que el feature flag se pasa correctamente al template
        self.assertContains(response, 'window.FEATURE_LOT_OVERRIDE = true')
        
    def test_backend_respects_lot_id_flag_on(self):
        """Test que el backend respeta lot_id cuando flag=True"""
        # Venta especificando L2 (override de FEFO)
        payload = {
            "items": [
                {
                    "product_id": self.product_p1.id,
                    "qty": "2.000",
                    "unit_price": "10.00",
                    "lot_id": self.lot_l2.id,
                    "lot_override_reason": "Test de override con flag ON"
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
        
        # Verificar que se usó L2 como se especificó
        movement = sale_data['movements'][0]
        self.assertEqual(movement['lot_id'], self.lot_l2.id)
        self.assertEqual(movement['lot_code'], 'L2')
        
        # Verificar que el stock se redujo del lote correcto
        self.lot_l1.refresh_from_db()
        self.lot_l2.refresh_from_db()
        self.assertEqual(self.lot_l1.qty_on_hand, Decimal('5.000'))  # Sin cambios
        self.assertEqual(self.lot_l2.qty_on_hand, Decimal('8.000'))  # 10 - 2
        
    def test_fefo_still_works_without_lot_id_flag_on(self):
        """Test que FEFO sigue funcionando sin lot_id cuando flag=True"""
        # Venta sin especificar lot_id
        payload = {
            "items": [
                {
                    "product_id": self.product_p1.id,
                    "qty": "1.000",
                    "unit_price": "10.00"
                    # Sin lot_id - debería usar FEFO
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
        
        # Verificar que se usó L1 (FEFO)
        movement = sale_data['movements'][0]
        self.assertEqual(movement['lot_id'], self.lot_l1.id)
        self.assertEqual(movement['lot_code'], 'L1')
        
    def test_blocked_lot_cannot_be_overridden_flag_on(self):
        """Test que lotes bloqueados (QC/reservado) no pueden ser usados en override"""
        # Intentar venta con lote L3 (en cuarentena)
        payload = {
            "items": [
                {
                    "product_id": self.product_p1.id,
                    "qty": "1.000",
                    "unit_price": "10.00",
                    "lot_id": self.lot_l3.id,
                    "lot_override_reason": "Intentando usar lote en cuarentena"
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Debería fallar
        self.assertIn(response.status_code, [400, 422])
        error_data = response.json()
        self.assertIn('error', error_data)


@override_settings(FEATURE_LOT_OVERRIDE=False)
class TestFlagTransitionStability(FeatureFlagTestCase):
    """Test que cambiar el flag no rompe flujos FEFO"""
    
    def test_flag_change_does_not_break_fefo(self):
        """Test que cambiar el flag no afecta la lógica FEFO básica"""
        # Primera venta con flag OFF
        payload = {
            "items": [
                {
                    "product_id": self.product_p1.id,
                    "qty": "1.000",
                    "unit_price": "10.00"
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
        
        # Verificar que se usó L1 (FEFO)
        movement = sale_data['movements'][0]
        self.assertEqual(movement['lot_id'], self.lot_l1.id)
        
        # Cambiar a flag ON y hacer otra venta sin lot_id
        with override_settings(FEATURE_LOT_OVERRIDE=True):
            response2 = self.client.post(
                '/api/v1/pos/sale',
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            self.assertEqual(response2.status_code, 200)
            sale_data2 = response2.json()
            
            # Debería seguir usando FEFO (L1 tiene stock restante)
            movement2 = sale_data2['movements'][0]
            self.assertEqual(movement2['lot_id'], self.lot_l1.id)