from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from apps.catalog.models import Product
from apps.stock.models import StockLot, Movement, Warehouse
from apps.stock.services import record_entry, record_exit_fefo, EntryError, ExitError


class StockServicesTestCase(TestCase):
    """Tests para los servicios de stock: entrada y salida FEFO."""

    def setUp(self):
        """Configuración inicial para los tests."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.product = Product.objects.create(
            code='TEST001',
            name='Producto de Test',
            price=Decimal('100.00')
        )
        
        self.warehouse = Warehouse.objects.create(
            name='Almacén Principal',
            is_active=True
        )

    def test_entry_creates_new_lot(self):
        """Test: entrada correcta crea un nuevo lote."""
        movement = record_entry(
            product_id=self.product.id,
            lot_code='LOTE001',
            expiry_date=date.today() + timedelta(days=30),
            qty=Decimal('10.000'),
            unit_cost=Decimal('50.00'),
            user_id=self.user.id,
            warehouse_id=self.warehouse.id
        )
        
        # Verificar que se creó el movimiento
        self.assertEqual(movement.type, Movement.Type.ENTRY)
        self.assertEqual(movement.qty, Decimal('10.000'))
        self.assertEqual(movement.unit_cost, Decimal('50.00'))
        
        # Verificar que se creó el lote
        lot = StockLot.objects.get(product=self.product, lot_code='LOTE001')
        self.assertEqual(lot.qty_on_hand, Decimal('10.000'))
        self.assertEqual(lot.unit_cost, Decimal('50.00'))
        self.assertEqual(lot.warehouse, self.warehouse)

    def test_entry_updates_existing_lot(self):
        """Test: entrada a lote existente actualiza cantidad."""
        # Crear lote inicial
        expiry = date.today() + timedelta(days=30)
        record_entry(
            product_id=self.product.id,
            lot_code='LOTE001',
            expiry_date=expiry,
            qty=Decimal('10.000'),
            unit_cost=Decimal('50.00'),
            user_id=self.user.id,
            warehouse_id=self.warehouse.id
        )
        
        # Segunda entrada al mismo lote
        record_entry(
            product_id=self.product.id,
            lot_code='LOTE001',
            expiry_date=expiry,  # Misma fecha de vencimiento
            qty=Decimal('5.000'),
            unit_cost=Decimal('55.00'),  # Diferente costo
            user_id=self.user.id,
            warehouse_id=self.warehouse.id
        )
        
        # Verificar que se actualizó la cantidad
        lot = StockLot.objects.get(product=self.product, lot_code='LOTE001')
        self.assertEqual(lot.qty_on_hand, Decimal('15.000'))
        
        # Verificar que hay 2 movimientos
        movements = Movement.objects.filter(lot=lot, type=Movement.Type.ENTRY)
        self.assertEqual(movements.count(), 2)

    def test_entry_lot_mismatch_error(self):
        """Test: entrada con fecha de vencimiento diferente falla."""
        # Crear lote inicial
        record_entry(
            product_id=self.product.id,
            lot_code='LOTE001',
            expiry_date=date.today() + timedelta(days=30),
            qty=Decimal('10.000'),
            unit_cost=Decimal('50.00'),
            user_id=self.user.id
        )
        
        # Intentar entrada con diferente fecha de vencimiento
        with self.assertRaises(EntryError) as cm:
            record_entry(
                product_id=self.product.id,
                lot_code='LOTE001',
                expiry_date=date.today() + timedelta(days=60),  # Diferente fecha
                qty=Decimal('5.000'),
                unit_cost=Decimal('50.00'),
                user_id=self.user.id
            )
        
        self.assertEqual(cm.exception.code, 'LOT_MISMATCH')

    def test_entry_validation_error_negative_qty(self):
        """Test: entrada con cantidad negativa falla."""
        with self.assertRaises(EntryError) as cm:
            record_entry(
                product_id=self.product.id,
                lot_code='LOTE001',
                expiry_date=date.today() + timedelta(days=30),
                qty=Decimal('-5.000'),  # Cantidad negativa
                unit_cost=Decimal('50.00'),
                user_id=self.user.id
            )
        
        self.assertEqual(cm.exception.code, 'VALIDATION_ERROR')

    def test_exit_fefo_single_lot(self):
        """Test: salida FEFO con un solo lote."""
        # Crear lote
        record_entry(
            product_id=self.product.id,
            lot_code='LOTE001',
            expiry_date=date.today() + timedelta(days=30),
            qty=Decimal('10.000'),
            unit_cost=Decimal('50.00'),
            user_id=self.user.id
        )
        
        # Realizar salida
        movements = record_exit_fefo(
            product_id=self.product.id,
            qty=Decimal('3.000'),
            user_id=self.user.id
        )
        
        # Verificar movimiento de salida
        self.assertEqual(len(movements), 1)
        movement = movements[0]
        self.assertEqual(movement.type, Movement.Type.EXIT)
        self.assertEqual(movement.qty, Decimal('3.000'))
        
        # Verificar que se actualizó el stock
        lot = StockLot.objects.get(product=self.product, lot_code='LOTE001')
        self.assertEqual(lot.qty_on_hand, Decimal('7.000'))

    def test_exit_fefo_multiple_lots(self):
        """Test: salida FEFO con múltiples lotes (orden FEFO)."""
        today = date.today()
        
        # Crear lotes con diferentes fechas de vencimiento
        # Lote más próximo a vencer
        record_entry(
            product_id=self.product.id,
            lot_code='LOTE_VIEJO',
            expiry_date=today + timedelta(days=10),
            qty=Decimal('5.000'),
            unit_cost=Decimal('40.00'),
            user_id=self.user.id
        )
        
        # Lote intermedio
        record_entry(
            product_id=self.product.id,
            lot_code='LOTE_MEDIO',
            expiry_date=today + timedelta(days=20),
            qty=Decimal('8.000'),
            unit_cost=Decimal('45.00'),
            user_id=self.user.id
        )
        
        # Lote más nuevo
        record_entry(
            product_id=self.product.id,
            lot_code='LOTE_NUEVO',
            expiry_date=today + timedelta(days=30),
            qty=Decimal('12.000'),
            unit_cost=Decimal('50.00'),
            user_id=self.user.id
        )
        
        # Realizar salida que requiere múltiples lotes
        movements = record_exit_fefo(
            product_id=self.product.id,
            qty=Decimal('10.000'),  # Más que el primer lote
            user_id=self.user.id
        )
        
        # Verificar que se usaron 2 lotes
        self.assertEqual(len(movements), 2)
        
        # Verificar orden FEFO (primero el más viejo)
        movement1 = movements[0]
        movement2 = movements[1]
        
        # Primer movimiento: todo el lote viejo
        lot_viejo = StockLot.objects.get(lot_code='LOTE_VIEJO')
        self.assertEqual(movement1.lot, lot_viejo)
        self.assertEqual(movement1.qty, Decimal('5.000'))
        self.assertEqual(lot_viejo.qty_on_hand, Decimal('0.000'))
        
        # Segundo movimiento: parte del lote medio
        lot_medio = StockLot.objects.get(lot_code='LOTE_MEDIO')
        self.assertEqual(movement2.lot, lot_medio)
        self.assertEqual(movement2.qty, Decimal('5.000'))
        self.assertEqual(lot_medio.qty_on_hand, Decimal('3.000'))
        
        # Lote nuevo no debe haberse tocado
        lot_nuevo = StockLot.objects.get(lot_code='LOTE_NUEVO')
        self.assertEqual(lot_nuevo.qty_on_hand, Decimal('12.000'))

    def test_exit_insufficient_stock(self):
        """Test: salida con stock insuficiente falla."""
        # Crear lote con stock limitado
        record_entry(
            product_id=self.product.id,
            lot_code='LOTE001',
            expiry_date=date.today() + timedelta(days=30),
            qty=Decimal('5.000'),
            unit_cost=Decimal('50.00'),
            user_id=self.user.id
        )
        
        # Intentar salida mayor al stock disponible
        with self.assertRaises(ExitError) as cm:
            record_exit_fefo(
                product_id=self.product.id,
                qty=Decimal('10.000'),  # Más del disponible
                user_id=self.user.id
            )
        
        self.assertEqual(cm.exception.code, 'INSUFFICIENT_STOCK')
        self.assertIn('Solicitado 10.000, disponible 5.000', str(cm.exception))

    def test_exit_validation_error_negative_qty(self):
        """Test: salida con cantidad negativa falla."""
        with self.assertRaises(ExitError) as cm:
            record_exit_fefo(
                product_id=self.product.id,
                qty=Decimal('-3.000'),  # Cantidad negativa
                user_id=self.user.id
            )
        
        self.assertEqual(cm.exception.code, 'VALIDATION_ERROR')

    def test_exit_fefo_with_warehouse_filter(self):
        """Test: salida FEFO respeta filtro de almacén."""
        warehouse2 = Warehouse.objects.create(name='Almacén 2', is_active=True)
        
        # Crear lotes en diferentes almacenes
        record_entry(
            product_id=self.product.id,
            lot_code='LOTE_ALM1',
            expiry_date=date.today() + timedelta(days=10),
            qty=Decimal('5.000'),
            unit_cost=Decimal('50.00'),
            user_id=self.user.id,
            warehouse_id=self.warehouse.id
        )
        
        record_entry(
            product_id=self.product.id,
            lot_code='LOTE_ALM2',
            expiry_date=date.today() + timedelta(days=5),  # Más próximo a vencer
            qty=Decimal('8.000'),
            unit_cost=Decimal('50.00'),
            user_id=self.user.id,
            warehouse_id=warehouse2.id
        )
        
        # Salida solo del almacén 1
        movements = record_exit_fefo(
            product_id=self.product.id,
            qty=Decimal('3.000'),
            user_id=self.user.id,
            warehouse_id=self.warehouse.id
        )
        
        # Debe usar solo el lote del almacén 1
        self.assertEqual(len(movements), 1)
        lot_usado = movements[0].lot
        self.assertEqual(lot_usado.lot_code, 'LOTE_ALM1')
        self.assertEqual(lot_usado.warehouse, self.warehouse)

    def test_exit_fefo_exact_stock_consumption(self):
        """Test: salida FEFO que consume exactamente todo el stock."""
        # Crear múltiples lotes
        record_entry(
            product_id=self.product.id,
            lot_code='LOTE1',
            expiry_date=date.today() + timedelta(days=10),
            qty=Decimal('3.000'),
            unit_cost=Decimal('50.00'),
            user_id=self.user.id
        )
        
        record_entry(
            product_id=self.product.id,
            lot_code='LOTE2',
            expiry_date=date.today() + timedelta(days=20),
            qty=Decimal('7.000'),
            unit_cost=Decimal('50.00'),
            user_id=self.user.id
        )
        
        # Salida que consume exactamente todo
        movements = record_exit_fefo(
            product_id=self.product.id,
            qty=Decimal('10.000'),
            user_id=self.user.id
        )
        
        # Verificar que se usaron ambos lotes completamente
        self.assertEqual(len(movements), 2)
        
        lot1 = StockLot.objects.get(lot_code='LOTE1')
        lot2 = StockLot.objects.get(lot_code='LOTE2')
        
        self.assertEqual(lot1.qty_on_hand, Decimal('0.000'))
        self.assertEqual(lot2.qty_on_hand, Decimal('0.000'))
        
        # Verificar cantidades de movimientos
        self.assertEqual(movements[0].qty, Decimal('3.000'))
        self.assertEqual(movements[1].qty, Decimal('7.000'))
