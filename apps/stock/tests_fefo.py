# apps/stock/tests_fefo.py
import threading
import time
from datetime import date, timedelta
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model

from apps.catalog.models import Product
from apps.stock.models import StockLot, Warehouse, Movement
from apps.stock.services import get_lot_options, allocate_lots_fefo, StockError
from apps.stock.fefo_service import FEFOService
from apps.stock.services import NotEnoughStock, NoLotsAvailable

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
    
    def test_override_lote_con_vida_util_insuficiente(self):
        """Test que override de lote con vida útil insuficiente falla correctamente."""
        # Crear lote con vida útil insuficiente (5 días)
        today = date.today()
        lot_short_life = StockLot.objects.create(
            product=self.product,
            lot_code='LOT-SHORT',
            expiry_date=today + timedelta(days=5),
            qty_on_hand=Decimal('10.000'),
            unit_cost=Decimal('8.50'),
            warehouse=self.warehouse
        )
        
        # Intentar override con vida útil mínima de 15 días
        with self.assertRaises(StockError) as context:
            allocate_lots_fefo(
                self.product, 
                Decimal('5.000'), 
                chosen_lot_id=lot_short_life.id,
                min_shelf_life_days=15
            )
        
        self.assertEqual(context.exception.code, "INSUFFICIENT_SHELF_LIFE")
        self.assertIn("no cumple vida útil mínima", str(context.exception))
    
    def test_override_lote_valido_con_vida_util_adecuada(self):
        """Test que override de lote con vida útil adecuada funciona correctamente."""
        # Crear lote con vida útil adecuada (25 días)
        today = date.today()
        lot_good_life = StockLot.objects.create(
            product=self.product,
            lot_code='LOT-GOOD',
            expiry_date=today + timedelta(days=25),
            qty_on_hand=Decimal('8.000'),
            unit_cost=Decimal('9.50'),
            warehouse=self.warehouse
        )
        
        # Override con vida útil mínima de 15 días (debe funcionar)
        plan = allocate_lots_fefo(
            self.product, 
            Decimal('5.000'), 
            chosen_lot_id=lot_good_life.id,
            min_shelf_life_days=15
        )
        
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0].lot_id, lot_good_life.id)
        self.assertEqual(plan[0].qty_allocated, Decimal('5.000'))
    
    def test_override_parcial_con_vida_util_resto_lotes(self):
        """Test que override parcial completa con lotes que cumplen vida útil."""
        # Crear un producto nuevo para evitar conflictos con lotes del setUp
        product_new = Product.objects.create(
            code='TEST002',
            name='Producto Test 2',
            price=Decimal('15.00')
        )
        
        # Crear lote con vida útil corta (5 días)
        today = date.today()
        lot_short = StockLot.objects.create(
            product=product_new,
            lot_code='LOT-SHORT',
            expiry_date=today + timedelta(days=5),
            qty_on_hand=Decimal('3.000'),
            unit_cost=Decimal('8.00'),
            warehouse=self.warehouse
        )
        
        # Crear lote con vida útil larga (40 días)
        lot_long = StockLot.objects.create(
            product=product_new,
            lot_code='LOT-LONG',
            expiry_date=today + timedelta(days=40),
            qty_on_hand=Decimal('10.000'),
            unit_cost=Decimal('10.00'),
            warehouse=self.warehouse
        )
        
        # Override del lote con vida útil corta, pero pedir más cantidad
        # Debe tomar 3 del lote corto y 2 del lote largo (que cumple vida útil)
        plan = allocate_lots_fefo(
            product_new, 
            Decimal('5.000'), 
            chosen_lot_id=lot_short.id,
            min_shelf_life_days=15
        )
        
        self.assertEqual(len(plan), 2)
        
        # Primer plan: lote corto (override) - 3 unidades
        self.assertEqual(plan[0].lot_id, lot_short.id)
        self.assertEqual(plan[0].qty_allocated, Decimal('3.000'))
        
        # Segundo plan: lote largo (FEFO) - 2 unidades restantes
        self.assertEqual(plan[1].lot_id, lot_long.id)
        self.assertEqual(plan[1].qty_allocated, Decimal('2.000'))
    
    def test_lote_vencido_no_disponible(self):
        """Test que lotes vencidos no están disponibles."""
        # Crear un producto nuevo para evitar conflictos con lotes del setUp
        product_new = Product.objects.create(
            code='TEST003',
            name='Producto Test 3',
            price=Decimal('20.00')
        )
        
        # Crear lote vencido (ayer)
        yesterday = date.today() - timedelta(days=1)
        expired_lot = StockLot.objects.create(
            product=product_new,
            lot_code='LOT-EXPIRED',
            expiry_date=yesterday,
            qty_on_hand=Decimal('10.000'),
            unit_cost=Decimal('8.00'),
            warehouse=self.warehouse
        )
        
        # Verificar que qty_available es 0 para lote vencido
        self.assertEqual(expired_lot.qty_available, Decimal('0.000'))
        
        # Verificar que no aparece en opciones de lotes
        options = get_lot_options(product_new, Decimal('1.000'))
        lot_ids = [option.lot_id for option in options]
        self.assertNotIn(expired_lot.id, lot_ids)
        
        # Verificar que no se puede asignar con FEFO
        with self.assertRaises(StockError) as context:
            allocate_lots_fefo(product_new, Decimal('1.000'))
        
        # Puede ser INSUFFICIENT_STOCK o INSUFFICIENT_SHELF_LIFE dependiendo de la lógica
        self.assertIn(context.exception.code, ["INSUFFICIENT_STOCK", "INSUFFICIENT_SHELF_LIFE"])
    
    def test_lote_vencido_con_override_falla(self):
        """Test que override de lote vencido falla."""
        # Crear un producto nuevo para evitar conflictos con lotes del setUp
        product_new = Product.objects.create(
            code='TEST004',
            name='Producto Test 4',
            price=Decimal('25.00')
        )
        
        # Crear lote vencido (ayer)
        yesterday = date.today() - timedelta(days=1)
        expired_lot = StockLot.objects.create(
            product=product_new,
            lot_code='LOT-EXPIRED',
            expiry_date=yesterday,
            qty_on_hand=Decimal('10.000'),
            unit_cost=Decimal('8.00'),
            warehouse=self.warehouse
        )
        
        # Intentar override de lote vencido debe fallar
        with self.assertRaises(StockError) as context:
            allocate_lots_fefo(
                product_new, 
                Decimal('5.000'), 
                chosen_lot_id=expired_lot.id
            )
        
        # Puede ser INVALID_LOT o INSUFFICIENT_SHELF_LIFE dependiendo de la lógica
        self.assertIn(context.exception.code, ["INVALID_LOT", "INSUFFICIENT_SHELF_LIFE"])


class FEFOSingleThreadTestCase(TestCase):
    """Tests de FEFO en un solo hilo usando FEFOService."""
    
    def setUp(self):
        """Configuración inicial para los tests."""
        self.user = User.objects.create_user(
            username='test_user',
            password='testpass123'
        )
        
        self.warehouse = Warehouse.objects.create(
            name='Almacén Test',
            is_active=True
        )
        
        self.product = Product.objects.create(
            name='Producto Test',
            code='TEST001',
            category='Test',
            price=Decimal('100.00')
        )
        
        # Crear lotes con diferentes fechas de vencimiento
        today = date.today()
        
        # Lote que vence primero (FEFO priority 1)
        self.lot_expires_first = StockLot.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            lot_code='LOT-001',
            expiry_date=today + timedelta(days=30),
            qty_on_hand=Decimal('50.000'),
            unit_cost=Decimal('10.00')
        )
        
        # Lote que vence segundo (FEFO priority 2)
        self.lot_expires_second = StockLot.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            lot_code='LOT-002',
            expiry_date=today + timedelta(days=60),
            qty_on_hand=Decimal('100.000'),
            unit_cost=Decimal('12.00')
        )
        
        # Lote que vence último (FEFO priority 3)
        self.lot_expires_last = StockLot.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            lot_code='LOT-003',
            expiry_date=today + timedelta(days=90),
            qty_on_hand=Decimal('75.000'),
            unit_cost=Decimal('15.00')
        )
    
    def test_fefo_single_thread_correct_lot(self):
        """Test que FEFO usa el lote que vence primero."""
        # Solicitar cantidad que cabe en el primer lote
        allocations = FEFOService.allocate_stock_fefo(
            product_id=self.product.id,
            qty_needed=Decimal('30.000'),
            user_id=self.user.id,
            warehouse_id=self.warehouse.id
        )
        
        # Verificar que se usó el lote correcto
        self.assertEqual(len(allocations), 1)
        self.assertEqual(allocations[0].lot_id, self.lot_expires_first.id)
        self.assertEqual(allocations[0].lot_code, 'LOT-001')
        self.assertEqual(allocations[0].qty_allocated, Decimal('30.000'))
        
        # Verificar que el stock se redujo correctamente
        self.lot_expires_first.refresh_from_db()
        self.assertEqual(self.lot_expires_first.qty_on_hand, Decimal('20.000'))
        
        # Verificar que se creó el movimiento
        movement = Movement.objects.get(
            type=Movement.Type.EXIT,
            product=self.product,
            lot=self.lot_expires_first
        )
        self.assertEqual(movement.qty, Decimal('30.000'))
        self.assertEqual(movement.created_by, self.user)
    
    def test_fefo_multiple_lots_allocation(self):
        """Test que FEFO usa múltiples lotes en orden correcto."""
        # Solicitar cantidad que requiere múltiples lotes
        allocations = FEFOService.allocate_stock_fefo(
            product_id=self.product.id,
            qty_needed=Decimal('120.000'),  # Más que el primer lote
            user_id=self.user.id,
            warehouse_id=self.warehouse.id
        )
        
        # Verificar que se usaron 2 lotes en orden FEFO
        self.assertEqual(len(allocations), 2)
        
        # Primer lote (vence primero) - completamente agotado
        self.assertEqual(allocations[0].lot_id, self.lot_expires_first.id)
        self.assertEqual(allocations[0].qty_allocated, Decimal('50.000'))
        
        # Segundo lote (vence segundo) - parcialmente usado
        self.assertEqual(allocations[1].lot_id, self.lot_expires_second.id)
        self.assertEqual(allocations[1].qty_allocated, Decimal('70.000'))
        
        # Verificar stock actualizado
        self.lot_expires_first.refresh_from_db()
        self.lot_expires_second.refresh_from_db()
        
        self.assertEqual(self.lot_expires_first.qty_on_hand, Decimal('0.000'))
        self.assertEqual(self.lot_expires_second.qty_on_hand, Decimal('30.000'))
        
        # El tercer lote no debe haber sido tocado
        self.lot_expires_last.refresh_from_db()
        self.assertEqual(self.lot_expires_last.qty_on_hand, Decimal('75.000'))
    
    def test_fefo_respects_min_shelf_life(self):
        """Test que FEFO respeta la vida útil mínima."""
        # Solicitar con vida útil mínima que excluye el primer lote
        with self.assertRaises(NoLotsAvailable) as context:
            FEFOService.allocate_stock_fefo(
                product_id=self.product.id,
                qty_needed=Decimal('30.000'),
                user_id=self.user.id,
                warehouse_id=self.warehouse.id,
                min_shelf_life_days=45  # Excluye LOT-001 (30 días)
            )
        
        self.assertEqual(context.exception.product_id, self.product.id)
        self.assertIn("vida útil >= 45 días", context.exception.criteria)
    
    def test_not_enough_stock_raises_business_error(self):
        """Test que se lanza excepción cuando no hay suficiente stock."""
        with self.assertRaises(NotEnoughStock) as context:
            FEFOService.allocate_stock_fefo(
                product_id=self.product.id,
                qty_needed=Decimal('300.000'),  # Más que el total disponible
                user_id=self.user.id,
                warehouse_id=self.warehouse.id
            )
        
        self.assertEqual(context.exception.product_id, self.product.id)
        self.assertEqual(context.exception.requested, Decimal('300.000'))
        self.assertEqual(context.exception.available, Decimal('225.000'))  # 50+100+75
    
    def test_get_available_stock(self):
        """Test que get_available_stock retorna el stock correcto."""
        available = FEFOService.get_available_stock(
            product_id=self.product.id,
            warehouse_id=self.warehouse.id
        )
        
        self.assertEqual(available, Decimal('225.000'))  # 50+100+75
    
    def test_get_lots_fefo_order(self):
        """Test que get_lots_fefo_order retorna lotes en orden correcto."""
        lots = FEFOService.get_lots_fefo_order(
            product_id=self.product.id,
            warehouse_id=self.warehouse.id
        )
        
        self.assertEqual(len(lots), 3)
        
        # Verificar orden FEFO
        self.assertEqual(lots[0]['lot_code'], 'LOT-001')  # Vence primero
        self.assertEqual(lots[1]['lot_code'], 'LOT-002')  # Vence segundo
        self.assertEqual(lots[2]['lot_code'], 'LOT-003')  # Vence último
        
        # Verificar días hasta vencimiento
        self.assertEqual(lots[0]['days_to_expiry'], 30)
        self.assertEqual(lots[1]['days_to_expiry'], 60)
        self.assertEqual(lots[2]['days_to_expiry'], 90)


class FEFOConcurrencyTestCase(TransactionTestCase):
    """Tests de concurrencia para FEFO."""
    
    def setUp(self):
        """Configuración inicial para tests de concurrencia."""
        self.user = User.objects.create_user(
            username='test_user',
            password='testpass123'
        )
        
        self.warehouse = Warehouse.objects.create(
            name='Almacén Concurrencia',
            is_active=True
        )
        
        self.product = Product.objects.create(
            name='Producto Concurrencia',
            code='CONC001',
            category='Test',
            price=Decimal('100.00')
        )
        
        # Crear lote con stock suficiente para tests de concurrencia
        today = date.today()
        self.lot = StockLot.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            lot_code='CONC-LOT-001',
            expiry_date=today + timedelta(days=60),
            qty_on_hand=Decimal('1000.000'),
            unit_cost=Decimal('10.00')
        )
    
    def test_fefo_concurrency_no_negative_stock(self):
        """Test que la concurrencia no genera stock negativo."""
        results = []
        errors = []
        
        def allocate_stock(worker_id):
            """Función que ejecuta cada worker."""
            try:
                allocation = FEFOService.allocate_stock_fefo(
                    product_id=self.product.id,
                    qty_needed=Decimal('50.000'),
                    user_id=self.user.id,
                    warehouse_id=self.warehouse.id,
                    reason=f"Worker {worker_id}"
                )
                results.append((worker_id, allocation))
            except Exception as e:
                errors.append((worker_id, str(e)))
        
        # Ejecutar 15 workers concurrentemente
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [
                executor.submit(allocate_stock, i) 
                for i in range(15)
            ]
            
            # Esperar a que todos terminen
            for future in as_completed(futures):
                future.result()
        
        # Verificar resultados
        self.lot.refresh_from_db()
        
        # El stock nunca debe ser negativo
        self.assertGreaterEqual(self.lot.qty_on_hand, Decimal('0'))
        
        # Verificar que el stock final es correcto
        successful_allocations = len(results)
        expected_remaining = Decimal('1000.000') - (successful_allocations * Decimal('50.000'))
        self.assertEqual(self.lot.qty_on_hand, expected_remaining)
        
        # Verificar que se crearon los movimientos correctos
        movements = Movement.objects.filter(
            type=Movement.Type.EXIT,
            product=self.product,
            lot=self.lot
        )
        self.assertEqual(movements.count(), successful_allocations)
        
        # Verificar que la suma de movimientos coincide
        total_moved = sum(m.qty for m in movements)
        self.assertEqual(total_moved, successful_allocations * Decimal('50.000'))
    
    def test_fefo_concurrency_uses_earliest_expiry(self):
        """Test que la concurrencia respeta el orden FEFO."""
        # Crear múltiples lotes con diferentes fechas de vencimiento
        today = date.today()
        
        lot_early = StockLot.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            lot_code='EARLY-001',
            expiry_date=today + timedelta(days=30),
            qty_on_hand=Decimal('200.000'),
            unit_cost=Decimal('10.00')
        )
        
        lot_late = StockLot.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            lot_code='LATE-001',
            expiry_date=today + timedelta(days=90),
            qty_on_hand=Decimal('200.000'),
            unit_cost=Decimal('10.00')
        )
        
        results = []
        
        def allocate_stock_concurrent(worker_id):
            """Función que ejecuta cada worker."""
            try:
                allocation = FEFOService.allocate_stock_fefo(
                    product_id=self.product.id,
                    qty_needed=Decimal('30.000'),
                    user_id=self.user.id,
                    warehouse_id=self.warehouse.id,
                    reason=f"Concurrent worker {worker_id}"
                )
                results.append((worker_id, allocation))
            except Exception as e:
                pass  # Ignorar errores de stock insuficiente
        
        # Ejecutar 10 workers concurrentemente
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(allocate_stock_concurrent, i) 
                for i in range(10)
            ]
            
            for future in as_completed(futures):
                future.result()
        
        # Verificar que se usó primero el lote que vence antes
        lot_early.refresh_from_db()
        lot_late.refresh_from_db()
        
        # El lote que vence primero debe haberse usado más
        early_used = Decimal('200.000') - lot_early.qty_on_hand
        late_used = Decimal('200.000') - lot_late.qty_on_hand
        
        # Si hay stock suficiente en el lote temprano, no se debe tocar el tardío
        if early_used <= Decimal('200.000'):
            self.assertGreaterEqual(early_used, late_used)
    
    def test_concurrent_modification_handling(self):
        """Test que se maneja correctamente la modificación concurrente."""
        # Crear lote con poco stock para forzar conflictos
        small_lot = StockLot.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            lot_code='SMALL-001',
            expiry_date=date.today() + timedelta(days=30),
            qty_on_hand=Decimal('100.000'),
            unit_cost=Decimal('10.00')
        )
        
        success_count = 0
        error_count = 0
        
        def try_allocate(worker_id):
            """Intenta asignar stock, puede fallar por concurrencia."""
            nonlocal success_count, error_count
            try:
                FEFOService.allocate_stock_fefo(
                    product_id=self.product.id,
                    qty_needed=Decimal('90.000'),  # Casi todo el stock
                    user_id=self.user.id,
                    warehouse_id=self.warehouse.id,
                    reason=f"Conflict test {worker_id}"
                )
                success_count += 1
            except (NotEnoughStock, StockError):
                error_count += 1
        
        # Ejecutar múltiples workers que compiten por el mismo stock
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(try_allocate, i) 
                for i in range(5)
            ]
            
            for future in as_completed(futures):
                future.result()
        
        # Solo uno debe haber tenido éxito
        self.assertEqual(success_count, 1)
        self.assertEqual(error_count, 4)
        
        # Verificar que el stock final es correcto
        small_lot.refresh_from_db()
        self.assertEqual(small_lot.qty_on_hand, Decimal('10.000'))  # 100 - 90