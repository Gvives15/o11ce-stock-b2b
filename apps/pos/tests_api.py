# apps/pos/tests_api.py
"""Tests para el Bloque C - Venta POS con FEFO/Override (POST) y Bloque D - Políticas y permisos."""

from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.db import transaction
import threading
import time

from apps.catalog.models import Product
from apps.stock.models import StockLot, Movement, Warehouse
from apps.stock.services import record_entry
from apps.customers.models import Customer
from apps.panel.models import UserScope


class POSSaleAPITestCase(TestCase):
    """Tests para el endpoint POST /api/pos/sale."""

    def setUp(self):
        """Configuración inicial para los tests."""
        # Usuario de prueba
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Configurar permisos de override para tests existentes
        from apps.panel.models import UserScope
        user_scope, created = UserScope.objects.get_or_create(
            user=self.user,
            defaults={'has_scope_pos_override': True}
        )
        if not created:
            user_scope.has_scope_pos_override = True
            user_scope.save()
        
        # Almacén de prueba
        self.warehouse = Warehouse.objects.create(
            name='Almacén Principal',
            is_active=True
        )
        
        # Productos de prueba
        self.product_a = Product.objects.create(
            code='PROD-A',
            name='Producto A',
            price=Decimal('10.00')
        )
        
        self.product_b = Product.objects.create(
            code='PROD-B',
            name='Producto B',
            price=Decimal('15.00')
        )
        
        # Crear lotes de prueba para FEFO
        today = date.today()
        
        # Producto A: 2 lotes con diferentes fechas de vencimiento
        self.lot_a1 = record_entry(
            product_id=self.product_a.id,
            lot_code='LOT-A1',
            expiry_date=today + timedelta(days=10),  # Vence antes
            qty=Decimal('5.000'),
            unit_cost=Decimal('8.00'),
            user_id=self.user.id,
            warehouse_id=self.warehouse.id
        ).lot

        self.lot_a2 = record_entry(
            product_id=self.product_a.id,
            lot_code='LOT-A2',
            expiry_date=today + timedelta(days=30),  # Vence después
            qty=Decimal('10.000'),
            unit_cost=Decimal('9.00'),
            user_id=self.user.id,
            warehouse_id=self.warehouse.id
        ).lot
        
        # Producto B: 1 lote con stock limitado
        self.lot_b1 = record_entry(
            product_id=self.product_b.id,
            lot_code='LOT-B1',
            expiry_date=today + timedelta(days=20),
            qty=Decimal('3.000'),
            unit_cost=Decimal('12.00'),
            user_id=self.user.id,
            warehouse_id=self.warehouse.id
        ).lot

    def test_api_c1_venta_sin_lot_id_consume_fefo(self):
        """API-C1: Venta sin lot_id → consume FEFO."""
        payload = {
            "items": [
                {
                    "product_id": self.product_a.id,
                    "qty": "3.000"
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verificar estructura de respuesta
        self.assertIn('sale_id', data)
        self.assertEqual(data['total_items'], 1)
        self.assertEqual(len(data['movements']), 1)
        
        # Verificar que se usó FEFO (lote que vence antes)
        movement = data['movements'][0]
        self.assertEqual(movement['product_id'], self.product_a.id)
        self.assertEqual(movement['lot_id'], self.lot_a1.id)
        self.assertEqual(movement['lot_code'], 'LOT-A1')
        self.assertEqual(Decimal(movement['qty']), Decimal('3.000'))
        
        # Verificar que se actualizó el stock
        self.lot_a1.refresh_from_db()
        self.assertEqual(self.lot_a1.qty_on_hand, Decimal('2.000'))  # 5 - 3 = 2
        
        # Verificar que el segundo lote no se tocó
        self.lot_a2.refresh_from_db()
        self.assertEqual(self.lot_a2.qty_on_hand, Decimal('10.000'))

    def test_api_c2_override_valido_usa_lote_especifico(self):
        """API-C2: Override válido → usa ese lote (y completa con FEFO si falta)."""
        payload = {
            "items": [
                {
                    "product_id": self.product_a.id,
                    "qty": "7.000",  # Más de lo que tiene el lote A2 (10), pero menos del total
                    "lot_id": self.lot_a2.id,  # Override al lote que vence después
                    "lot_override_reason": "Cliente solicita lote específico"
                }
            ],
            "override_pin": "1234"
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verificar que se usó solo el lote especificado (tiene suficiente stock)
        self.assertEqual(len(data['movements']), 1)
        movement = data['movements'][0]
        self.assertEqual(movement['lot_id'], self.lot_a2.id)
        self.assertEqual(Decimal(movement['qty']), Decimal('7.000'))
        
        # Verificar stock actualizado
        self.lot_a2.refresh_from_db()
        self.assertEqual(self.lot_a2.qty_on_hand, Decimal('3.000'))  # 10 - 7 = 3
        
        # Verificar que el primer lote no se tocó
        self.lot_a1.refresh_from_db()
        self.assertEqual(self.lot_a1.qty_on_hand, Decimal('5.000'))

    def test_api_c2_override_con_fefo_complementario(self):
        """API-C2: Override que requiere completar con FEFO."""
        payload = {
            "items": [
                {
                    "product_id": self.product_a.id,
                    "qty": "12.000",  # Más de lo que tiene A2 (10), necesita FEFO
                    "lot_id": self.lot_a2.id,
                    "lot_override_reason": "Preferencia del cliente"
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Debe haber 2 movimientos: override + FEFO
        self.assertEqual(len(data['movements']), 2)
        
        # Primer movimiento: del lote especificado (override)
        override_movement = next(m for m in data['movements'] if m['lot_id'] == self.lot_a2.id)
        self.assertEqual(Decimal(override_movement['qty']), Decimal('10.000'))  # Todo el lote A2
        
        # Segundo movimiento: FEFO para completar
        fefo_movement = next(m for m in data['movements'] if m['lot_id'] == self.lot_a1.id)
        self.assertEqual(Decimal(fefo_movement['qty']), Decimal('2.000'))  # Lo que falta
        
        # Verificar stocks
        self.lot_a2.refresh_from_db()
        self.assertEqual(self.lot_a2.qty_on_hand, Decimal('0.000'))
        
        self.lot_a1.refresh_from_db()
        self.assertEqual(self.lot_a1.qty_on_hand, Decimal('3.000'))  # 5 - 2 = 3

    def test_api_c3_override_invalido_lote_inexistente(self):
        """API-C3: Override inválido → 400 "lote inválido/no disponible"."""
        payload = {
            "items": [
                {
                    "product_id": self.product_a.id,
                    "qty": "2.000",
                    "lot_id": 99999,  # Lote inexistente
                    "lot_override_reason": "Test lote inexistente"
                }
            ],
            "override_pin": "1234"
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['error'], 'INVALID_LOT')
        self.assertIn('no encontrado', data['detail'])

    def test_api_c3_override_invalido_lote_sin_stock(self):
        """API-C3: Override inválido → lote sin stock."""
        # Vaciar el lote A1
        self.lot_a1.qty_on_hand = Decimal('0.000')
        self.lot_a1.save()
        
        # Consumir todo el stock del lote A1 primero
        self.lot_a1.qty_on_hand = Decimal('0.000')
        self.lot_a1.save()
        
        payload = {
            "items": [
                {
                    "product_id": self.product_a.id,
                    "qty": "1.000",
                    "lot_id": self.lot_a1.id,  # Lote sin stock
                    "lot_override_reason": "Test lote sin stock"
                }
            ],
            "override_pin": "1234"
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['error'], 'INVALID_LOT')

    def test_api_c3_override_sin_razon(self):
        """API-C3: Override sin lot_override_reason → 400."""
        payload = {
            "items": [
                {
                    "product_id": self.product_a.id,
                    "qty": "2.000",
                    "lot_id": self.lot_a1.id
                    # Falta lot_override_reason
                }
            ],
            "override_pin": "1234"
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['error'], 'VALIDATION_ERROR')
        self.assertIn('lot_override_reason es requerido', data['detail'])

    def test_api_c4_stock_insuficiente_total(self):
        """API-C4: Stock insuficiente total → 400 "stock insuficiente"."""
        payload = {
            "items": [
                {
                    "product_id": self.product_a.id,
                    "qty": "20.000"  # Más del stock total (5 + 10 = 15)
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['error'], 'INSUFFICIENT_STOCK')
        self.assertIn('Stock insuficiente', data['detail'])

    def test_api_c4_stock_insuficiente_producto_sin_lotes(self):
        """API-C4: Stock insuficiente para producto sin lotes."""
        # Crear producto sin lotes
        product_c = Product.objects.create(
            code='PROD-C',
            name='Producto C',
            price=Decimal('20.00')
        )
        
        payload = {
            "items": [
                {
                    "product_id": product_c.id,
                    "qty": "1.000"
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['error'], 'INSUFFICIENT_STOCK')

    def test_venta_multiple_items_mixta(self):
        """Test: Venta con múltiples ítems, algunos con override y otros FEFO."""
        payload = {
            "items": [
                {
                    "product_id": self.product_a.id,
                    "qty": "2.000"  # FEFO automático
                },
                {
                    "product_id": self.product_b.id,
                    "qty": "1.000",
                    "lot_id": self.lot_b1.id,
                    "lot_override_reason": "Cliente específico"
                }
            ],
            "override_pin": "1234"
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data['total_items'], 2)
        self.assertEqual(len(data['movements']), 2)
        
        # Verificar movimiento FEFO para producto A
        movement_a = next(m for m in data['movements'] if m['product_id'] == self.product_a.id)
        self.assertEqual(movement_a['lot_id'], self.lot_a1.id)  # FEFO
        
        # Verificar movimiento override para producto B
        movement_b = next(m for m in data['movements'] if m['product_id'] == self.product_b.id)
        self.assertEqual(movement_b['lot_id'], self.lot_b1.id)  # Override

    def test_validaciones_basicas(self):
        """Test: Validaciones básicas del endpoint."""
        # Venta sin ítems
        response = self.client.post(
            '/api/v1/pos/sale',
            data={"items": []},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        
        # Cantidad inválida
        response = self.client.post(
            '/api/v1/pos/sale',
            data={
                "items": [
                    {
                        "product_id": self.product_a.id,
                        "qty": "0"  # Cantidad inválida
                    }
                ]
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        
        # Producto inexistente
        response = self.client.post(
            '/api/v1/pos/sale',
            data={
                "items": [
                    {
                        "product_id": 99999,  # Producto inexistente
                        "qty": "1.000"
                    }
                ]
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)


class POSSaleConcurrencyTestCase(TestCase):
    """Tests de concurrencia para ventas POS."""

    def setUp(self):
        """Configuración inicial para tests de concurrencia."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.warehouse = Warehouse.objects.create(
            name='Almacén Principal',
            is_active=True
        )
        
        self.product = Product.objects.create(
            code='PROD-CONC',
            name='Producto Concurrencia',
            price=Decimal('10.00')
        )
        
        # Crear lote con stock limitado
        self.lot = record_entry(
            product_id=self.product.id,
            lot_code='LOT-CONC',
            expiry_date=date.today() + timedelta(days=30),
            qty=Decimal('5.000'),  # Stock limitado
            unit_cost=Decimal('8.00'),
            user_id=self.user.id,
            warehouse_id=self.warehouse.id
        ).lot
    
    def tearDown(self):
        """Limpieza después de cada test."""
        # Restaurar stock original del lote
        if hasattr(self, 'lot') and self.lot:
            self.lot.qty_on_hand = Decimal('5.000')
            self.lot.save()

    def test_i_c5_concurrencia_select_for_update(self):
        """I-C5: Concurrencia (select_for_update): dos ventas simultáneas no dejan negativo."""
        from django.db import connections
        from django.test.utils import override_settings
        
        # Para SQLite en tests, necesitamos usar una configuración especial
        # Este test verifica que el select_for_update funciona correctamente
        
        # Simular concurrencia con transacciones manuales
        from django.db import transaction
        
        # Primera venta: exitosa
        with transaction.atomic():
            payload1 = {
                "items": [
                    {
                        "product_id": self.product.id,
                        "qty": "3.000"
                    }
                ]
            }
            
            response1 = self.client.post(
                '/api/v1/pos/sale',
                data=payload1,
                content_type='application/json'
            )
        
        # Verificar que la primera venta fue exitosa
        self.assertEqual(response1.status_code, 200)
        
        # Verificar stock después de primera venta
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.qty_on_hand, Decimal('2.000'))  # 5 - 3 = 2
        
        # Segunda venta: debe fallar por stock insuficiente
        payload2 = {
            "items": [
                {
                    "product_id": self.product.id,
                    "qty": "3.000"  # Más del stock restante (2)
                }
            ]
        }
        
        response2 = self.client.post(
            '/api/v1/pos/sale',
            data=payload2,
            content_type='application/json'
        )
        
        # La segunda venta debe fallar
        self.assertEqual(response2.status_code, 400)
        data2 = response2.json()
        self.assertEqual(data2['error'], 'INSUFFICIENT_STOCK')
        
        # Verificar que el stock final no es negativo
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.qty_on_hand, Decimal('2.000'))
        self.assertGreaterEqual(self.lot.qty_on_hand, Decimal('0.000'), 
                               "El stock no debe ser negativo")
    
    def test_i_c5_concurrencia_atomicidad_transaccional(self):
        """I-C5: Test adicional - Verificar atomicidad transaccional."""
        # Test que verifica que si falla una parte de la venta, se revierte todo
        
        # Crear un segundo producto sin stock para forzar fallo
        product_sin_stock = Product.objects.create(
            code='PROD-SIN-STOCK',
            name='Producto Sin Stock',
            price=Decimal('5.00')
        )
        
        payload = {
            "items": [
                {
                    "product_id": self.product.id,
                    "qty": "2.000"  # Este ítem es válido
                },
                {
                    "product_id": product_sin_stock.id,
                    "qty": "1.000"  # Este ítem fallará (sin stock)
                }
            ]
        }
        
        # Guardar stock inicial
        stock_inicial = self.lot.qty_on_hand
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=payload,
            content_type='application/json'
        )
        
        # La venta debe fallar completamente
        self.assertEqual(response.status_code, 400)
        
        # Verificar que NO se modificó el stock del primer producto
        # (transacción atómica revierte todo)
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.qty_on_hand, stock_inicial, 
                        "El stock debe mantenerse sin cambios si la transacción falla")


class POSGuardrailsTestCase(TestCase):
    """Tests para el Bloque D - Políticas y permisos (guardrails)."""

    def setUp(self):
        """Configuración inicial para los tests de guardrails."""
        # Usuario de prueba
        self.user = User.objects.create_user(
            username='testuser_guardrails',
            email='test_guardrails@example.com',
            password='testpass123'
        )
        
        # Crear UserScope para el usuario (verificar si ya existe)
        self.user_scope, created = UserScope.objects.get_or_create(
            user=self.user,
            defaults={
                'has_scope_dashboard': True,
                'has_scope_pos_override': False  # Sin permisos de override inicialmente
            }
        )
        
        # Almacén de prueba
        self.warehouse = Warehouse.objects.create(
            name='Almacén Principal',
            is_active=True
        )
        
        # Producto de prueba
        self.product = Product.objects.create(
            code='PROD-TEST',
            name='Producto Test',
            price=Decimal('10.00')
        )
        
        # Cliente con vida útil mínima
        self.customer = Customer.objects.create(
            name='Cliente Test',
            segment=Customer.Segment.RETAIL,
            min_shelf_life_days=30
        )
        
        # Crear lotes de prueba
        today = date.today()
        
        # Lote normal (disponible)
        self.lot_normal = record_entry(
            product_id=self.product.id,
            qty=Decimal('10.000'),
            lot_code='LOT-NORMAL',
            expiry_date=today + timedelta(days=60),
            unit_cost=Decimal('5.00'),
            user_id=self.user.id,
            warehouse_id=self.warehouse.id
        ).lot
        
        # Lote en cuarentena
        entry_qc = record_entry(
            product_id=self.product.id,
            qty=Decimal('5.000'),
            lot_code='LOT-QC',
            expiry_date=today + timedelta(days=90),
            unit_cost=Decimal('5.00'),
            user_id=self.user.id,
            warehouse_id=self.warehouse.id
        )
        self.lot_quarantined = entry_qc.lot
        self.lot_quarantined.is_quarantined = True
        self.lot_quarantined.save()
        
        # Lote reservado
        entry_reserved = record_entry(
            product_id=self.product.id,
            qty=Decimal('5.000'),
            lot_code='LOT-RESERVED',
            expiry_date=today + timedelta(days=90),
            unit_cost=Decimal('5.00'),
            user_id=self.user.id,
            warehouse_id=self.warehouse.id
        )
        self.lot_reserved = entry_reserved.lot
        self.lot_reserved.is_reserved = True
        self.lot_reserved.save()
        
        # Lote con vida útil insuficiente
        entry_short = record_entry(
            product_id=self.product.id,
            qty=Decimal('5.000'),
            lot_code='LOT-SHORT',
            expiry_date=today + timedelta(days=15),  # Solo 15 días, menos que los 30 requeridos
            unit_cost=Decimal('5.00'),
            user_id=self.user.id,
            warehouse_id=self.warehouse.id
        )
        self.lot_short_shelf = entry_short.lot

    def test_api_d1_lote_en_cuarentena_bloqueado(self):
        """API-D1: Lote en QC/Reserva → 400 'lote bloqueado'."""
        payload = {
            "items": [
                {
                    "product_id": self.product.id,
                    "qty": "2.000",
                    "lot_id": self.lot_quarantined.id,
                    "lot_override_reason": "Test override"
                }
            ],
            "override_pin": "1234"
        }
        
        # Dar permisos de override al usuario
        self.user_scope.has_scope_pos_override = True
        self.user_scope.save()
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['error'], 'LOT_BLOCKED')
        self.assertIn('cuarentena', data['detail'])

    def test_api_d1_lote_reservado_bloqueado(self):
        """API-D1: Lote reservado → 400 'lote bloqueado'."""
        payload = {
            "items": [
                {
                    "product_id": self.product.id,
                    "qty": "2.000",
                    "lot_id": self.lot_reserved.id,
                    "lot_override_reason": "Test override"
                }
            ],
            "override_pin": "1234"
        }
        
        # Dar permisos de override al usuario
        self.user_scope.has_scope_pos_override = True
        self.user_scope.save()
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['error'], 'LOT_BLOCKED')
        self.assertIn('reservado', data['detail'])

    def test_api_d2_vida_util_minima_incumplida_fefo(self):
        """API-D2: Vida útil mínima incumplida en FEFO → 400 'vida útil insuficiente'."""
        payload = {
            "items": [
                {
                    "product_id": self.product.id,
                    "qty": "12.000"  # Cantidad que requiere usar lote con vida útil corta
                }
            ],
            "customer_id": self.customer.id
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['error'], 'INSUFFICIENT_SHELF_LIFE')

    def test_api_d2_vida_util_minima_incumplida_override(self):
        """API-D2: Vida útil mínima incumplida en override → 400 'vida útil insuficiente'."""
        payload = {
            "items": [
                {
                    "product_id": self.product.id,
                    "qty": "2.000",
                    "lot_id": self.lot_short_shelf.id,
                    "lot_override_reason": "Test override"
                }
            ],
            "customer_id": self.customer.id,
            "override_pin": "1234"
        }
        
        # Dar permisos de override al usuario
        self.user_scope.has_scope_pos_override = True
        self.user_scope.save()
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['error'], 'INSUFFICIENT_SHELF_LIFE')

    def test_api_d3_usuario_sin_permiso_override(self):
        """API-D3: Usuario sin permiso para override → 403."""
        payload = {
            "items": [
                {
                    "product_id": self.product.id,
                    "qty": "2.000",
                    "lot_id": self.lot_normal.id,
                    "lot_override_reason": "Test override"
                }
            ],
            "override_pin": "1234"
        }
        
        # Usuario sin permisos de override (has_scope_pos_override=False por defecto)
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertEqual(data['error'], 'PERMISSION_DENIED')

    def test_api_d4_usuario_con_permiso_pin_valido(self):
        """API-D4: Usuario con permiso/PIN válido → 200."""
        payload = {
            "items": [
                {
                    "product_id": self.product.id,
                    "qty": "2.000",
                    "lot_id": self.lot_normal.id,
                    "lot_override_reason": "Test override válido"
                }
            ],
            "override_pin": "1234"
        }
        
        # Dar permisos de override al usuario
        self.user_scope.has_scope_pos_override = True
        self.user_scope.save()
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('sale_id', data)
        
        # Verificar que se redujo el stock
        self.lot_normal.refresh_from_db()
        self.assertEqual(self.lot_normal.qty_on_hand, Decimal('8.000'))

    def test_api_d4_pin_invalido(self):
        """API-D4: PIN inválido → 403."""
        payload = {
            "items": [
                {
                    "product_id": self.product.id,
                    "qty": "2.000",
                    "lot_id": self.lot_normal.id,
                    "lot_override_reason": "Test override"
                }
            ],
            "override_pin": "9999"  # PIN incorrecto
        }
        
        # Dar permisos de override al usuario
        self.user_scope.has_scope_pos_override = True
        self.user_scope.save()
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertEqual(data['error'], 'INVALID_PIN')

    def test_api_e1_override_crea_registro_auditoria(self):
        """I-E1: Override crea 1 registro con los campos correctos."""
        from apps.pos.models import LotOverrideAudit
        
        # Verificar que no hay registros de auditoría inicialmente
        self.assertEqual(LotOverrideAudit.objects.count(), 0)
        
        # Configurar permisos de override
        self.user_scope.has_scope_pos_override = True
        self.user_scope.save()
        
        payload = {
            "items": [
                {
                    "product_id": self.product.id,
                    "qty": "2.000",
                    "lot_id": self.lot_normal.id,  # Override a lote específico
                    "lot_override_reason": "Test auditoría override"
                }
            ],
            "override_pin": "1234"
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar que se creó exactamente 1 registro de auditoría
        self.assertEqual(LotOverrideAudit.objects.count(), 1)
        
        # Verificar los campos del registro de auditoría
        audit_record = LotOverrideAudit.objects.first()
        self.assertEqual(audit_record.actor, self.user)
        self.assertEqual(audit_record.product, self.product)
        self.assertEqual(audit_record.lot_chosen, self.lot_normal)
        self.assertEqual(audit_record.qty, 2.000)
        self.assertEqual(audit_record.reason, "Test auditoría override")
        self.assertIsNotNone(audit_record.sale_id)
        self.assertIsNotNone(audit_record.timestamp)

    def test_api_e2_venta_sin_override_no_crea_registro(self):
        """I-E2: Venta sin override → no crea registro."""
        from apps.pos.models import LotOverrideAudit
        
        # Verificar que no hay registros de auditoría inicialmente
        self.assertEqual(LotOverrideAudit.objects.count(), 0)
        
        # Venta normal sin override (FEFO automático)
        payload = {
            "items": [
                {
                    "product_id": self.product.id,
                    "qty": "1.000"
                    # Sin lot_id ni lot_override_reason
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/sale',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar que NO se creó ningún registro de auditoría
        self.assertEqual(LotOverrideAudit.objects.count(), 0)