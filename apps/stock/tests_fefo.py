# apps/stock/tests_fefo.py
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.catalog.models import Product
from apps.stock.models import StockLot, Warehouse
from apps.stock.services import get_lot_options, allocate_lots_fefo, StockError

User = get_user_model()


class FEFOServiceTests(TestCase):
    """Tests para el servicio FEFO de asignación de lotes."""
    
    def setUp(self):
        """Configuración inicial para los tests."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.warehouse = Warehouse.objects.create(name='Almacén Principal')
        
        self.product = Product.objects.create(
            code='TEST001',
            name='Producto Test',
            price=Decimal('10.00')
        )
        
        # Crear lotes de prueba
        today = date.today()
        
        # Lote A: vence antes (en 10 días)
        self.lot_a = StockLot.objects.create(
            product=self.product,
            lot_code='LOT-A',
            expiry_date=today + timedelta(days=10),
            qty_on_hand=Decimal('2.000'),
            unit_cost=Decimal('8.00'),
            warehouse=self.warehouse
        )
        
        # Lote B: vence después (en 30 días)
        self.lot_b = StockLot.objects.create(
            product=self.product,
            lot_code='LOT-B',
            expiry_date=today + timedelta(days=30),
            qty_on_hand=Decimal('10.000'),
            unit_cost=Decimal('9.00'),
            warehouse=self.warehouse
        )
    
    def test_u_a1_fefo_puro(self):
        """U-A1: FEFO puro - con A(vence antes), B(vence después) → elige A."""
        options = get_lot_options(self.product, Decimal('1.000'))
        
        # Debe devolver lotes ordenados por FEFO
        self.assertEqual(len(options), 2)
        self.assertEqual(options[0].lot_id, self.lot_a.id)  # A primero (vence antes)
        self.assertEqual(options[1].lot_id, self.lot_b.id)  # B segundo
        
        # Asignación FEFO pura
        plan = allocate_lots_fefo(self.product, Decimal('1.000'))
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0].lot_id, self.lot_a.id)
        self.assertEqual(plan[0].qty_allocated, Decimal('1.000'))
    
    def test_u_a2_parcial(self):
        """U-A2: Parcial - A(2u), B(10u), piden 5u → plan = A:2 + B:3."""
        plan = allocate_lots_fefo(self.product, Decimal('5.000'))
        
        self.assertEqual(len(plan), 2)
        
        # Primer lote: A completo (2 unidades)
        self.assertEqual(plan[0].lot_id, self.lot_a.id)
        self.assertEqual(plan[0].qty_allocated, Decimal('2.000'))
        
        # Segundo lote: B parcial (3 unidades)
        self.assertEqual(plan[1].lot_id, self.lot_b.id)
        self.assertEqual(plan[1].qty_allocated, Decimal('3.000'))
    
    def test_u_a3_sin_stock(self):
        """U-A3: Sin stock - no hay lotes válidos → error."""
        # Solicitar más cantidad de la disponible
        with self.assertRaises(StockError) as context:
            allocate_lots_fefo(self.product, Decimal('15.000'))
        
        self.assertEqual(context.exception.code, "INSUFFICIENT_STOCK")
        self.assertIn("Stock insuficiente", str(context.exception))
    
    def test_u_a4_override_valido(self):
        """U-A4: Override válido - piden B → toma B."""
        plan = allocate_lots_fefo(
            self.product, 
            Decimal('3.000'), 
            chosen_lot_id=self.lot_b.id
        )
        
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0].lot_id, self.lot_b.id)
        self.assertEqual(plan[0].qty_allocated, Decimal('3.000'))
    
    def test_u_a5_override_invalido(self):
        """U-A5: Override inválido - lot_id inexistente/0 stock → error."""
        # Lote inexistente
        with self.assertRaises(StockError) as context:
            allocate_lots_fefo(self.product, Decimal('1.000'), chosen_lot_id=99999)
        
        self.assertEqual(context.exception.code, "INVALID_LOT")
        
        # Lote sin stock
        self.lot_a.qty_on_hand = Decimal('0')
        self.lot_a.save()
        
        with self.assertRaises(StockError) as context:
            allocate_lots_fefo(self.product, Decimal('1.000'), chosen_lot_id=self.lot_a.id)
        
        self.assertEqual(context.exception.code, "INVALID_LOT")
    
    def test_u_a6_vida_util_minima(self):
        """U-A6: Vida útil mínima - si min_shelf_life_days=30, filtra lotes que no cumplen."""
        # Solicitar lotes con mínimo 25 días de vida útil
        # Lote A (10 días) debe ser excluido, solo Lote B (30 días) debe aparecer
        options = get_lot_options(self.product, Decimal('1.000'), min_shelf_life_days=25)
        
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0].lot_id, self.lot_b.id)
        
        # Asignación con vida útil mínima
        plan = allocate_lots_fefo(self.product, Decimal('5.000'), min_shelf_life_days=25)
        
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0].lot_id, self.lot_b.id)
        self.assertEqual(plan[0].qty_allocated, Decimal('5.000'))
    
    def test_lotes_cuarentena_reservados(self):
        """Test que lotes en cuarentena o reservados son excluidos."""
        # Marcar lote A como cuarentena
        self.lot_a.is_quarantined = True
        self.lot_a.save()
        
        options = get_lot_options(self.product, Decimal('1.000'))
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0].lot_id, self.lot_b.id)
        
        # Marcar lote B como reservado
        self.lot_b.is_reserved = True
        self.lot_b.save()
        
        options = get_lot_options(self.product, Decimal('1.000'))
        self.assertEqual(len(options), 0)
    
    def test_override_parcial_completa_con_fefo(self):
        """Test que override parcial se completa con FEFO."""
        # Modificar lote B para que tenga menos stock del solicitado
        self.lot_b.qty_on_hand = Decimal('8.000')
        self.lot_b.save()
        
        # Override de lote B con 8 unidades, pero pedir 10 total
        # Debe tomar 8 de B y 2 de A (FEFO para el resto)
        plan = allocate_lots_fefo(
            self.product, 
            Decimal('10.000'), 
            chosen_lot_id=self.lot_b.id
        )
        
        self.assertEqual(len(plan), 2)
        
        # Primer plan: B (override) - 8 unidades disponibles
        self.assertEqual(plan[0].lot_id, self.lot_b.id)
        self.assertEqual(plan[0].qty_allocated, Decimal('8.000'))
        
        # Segundo plan: A (FEFO) - 2 unidades restantes
        self.assertEqual(plan[1].lot_id, self.lot_a.id)
        self.assertEqual(plan[1].qty_allocated, Decimal('2.000'))
    
    def test_orden_fefo_estable(self):
        """Test que el orden FEFO es estable (expiry_date, id)."""
        # Crear lote C con misma fecha de vencimiento que A pero ID mayor
        lot_c = StockLot.objects.create(
            product=self.product,
            lot_code='LOT-C',
            expiry_date=self.lot_a.expiry_date,  # Misma fecha que A
            qty_on_hand=Decimal('5.000'),
            unit_cost=Decimal('7.50'),
            warehouse=self.warehouse
        )
        
        options = get_lot_options(self.product, Decimal('1.000'))
        
        # Orden esperado: A (menor ID), C (mayor ID), B (fecha posterior)
        self.assertEqual(len(options), 3)
        self.assertEqual(options[0].lot_id, self.lot_a.id)
        self.assertEqual(options[1].lot_id, lot_c.id)
        self.assertEqual(options[2].lot_id, self.lot_b.id)