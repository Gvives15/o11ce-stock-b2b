"""Tests for stock services with FEFO, validations, and concurrency."""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.test import TransactionTestCase
from django.db import transaction
from django.contrib.auth.models import User
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from unittest.mock import patch, MagicMock

from apps.catalog.models import Product
from apps.stock.models import Warehouse, StockLot, Movement
from apps.stock.services import (
    # Legacy services
    create_entry, create_exit, pick_lots_fefo,
    StockError, NotEnoughStock, NoLotsAvailable,
    # Event-driven services
    request_stock_entry, request_stock_exit,
    validate_stock_availability, validate_warehouse
)
from apps.stock.events import (
    StockEntryRequested, StockExitRequested,
    StockValidationRequested, WarehouseValidationRequested
)


@pytest.mark.django_db
class TestStockValidations:
    """Tests para validaciones básicas del sistema de stock."""
    
    def setup_method(self):
        """Setup test data."""
        self.user = User.objects.create_user(username='testuser')
        self.warehouse = Warehouse.objects.create(name='Main Warehouse', is_active=True)
        self.product = Product.objects.create(
            code='TEST-001',
            name='Test Product',
            price=Decimal('10.00'),
            tax_rate=Decimal('21.00'),
            is_active=True
        )
    
    def test_create_entry_positive_qty_validation(self):
        """Test que no se puede crear entrada con cantidad <= 0."""
        with pytest.raises(StockError) as exc_info:
            create_entry(
                product=self.product,
                lot_code='LOT001',
                expiry_date=date.today() + timedelta(days=30),
                qty=Decimal('0'),
                unit_cost=Decimal('5.00'),
                warehouse=self.warehouse,
                created_by=self.user
            )
        assert exc_info.value.code == "VALIDATION_ERROR"
        assert "cantidad debe ser mayor a 0" in str(exc_info.value)
    
    def test_create_entry_positive_unit_cost_validation(self):
        """Test que no se puede crear entrada con unit_cost <= 0."""
        with pytest.raises(StockError) as exc_info:
            create_entry(
                product=self.product,
                lot_code='LOT001',
                expiry_date=date.today() + timedelta(days=30),
                qty=Decimal('10'),
                unit_cost=Decimal('0'),
                warehouse=self.warehouse,
                created_by=self.user
            )
        assert exc_info.value.code == "VALIDATION_ERROR"
        assert "costo unitario debe ser mayor a 0" in str(exc_info.value)
    
    def test_create_entry_lot_consistency_validation(self):
        """Test que no se puede crear entrada con fecha inconsistente en lote existente."""
        # Crear lote inicial
        create_entry(
            product=self.product,
            lot_code='LOT001',
            expiry_date=date.today() + timedelta(days=30),
            qty=Decimal('10'),
            unit_cost=Decimal('5.00'),
            warehouse=self.warehouse,
            created_by=self.user
        )
        
        # Intentar crear entrada con fecha diferente
        with pytest.raises(StockError) as exc_info:
            create_entry(
                product=self.product,
                lot_code='LOT001',
                expiry_date=date.today() + timedelta(days=60),  # Fecha diferente
                qty=Decimal('5'),
                unit_cost=Decimal('5.00'),
                warehouse=self.warehouse,
                created_by=self.user
            )
        assert exc_info.value.code == "INCONSISTENT_LOT"
    
    def test_create_exit_positive_qty_validation(self):
        """Test que no se puede crear salida con cantidad <= 0."""
        with pytest.raises(StockError) as exc_info:
            create_exit(
                product=self.product,
                qty_total=Decimal('0'),
                warehouse=self.warehouse,
                created_by=self.user
            )
        assert exc_info.value.code == "VALIDATION_ERROR"
        assert "cantidad debe ser mayor a 0" in str(exc_info.value)


@pytest.mark.django_db
class TestFEFOLogic:
    """Tests para la lógica FEFO (First Expired, First Out)."""
    
    def setup_method(self):
        """Setup test data with multiple lots."""
        self.user = User.objects.create_user(username='testuser')
        self.warehouse = Warehouse.objects.create(name='Main Warehouse', is_active=True)
        self.product = Product.objects.create(
            code='TEST-001',
            name='Test Product',
            price=Decimal('10.00'),
            tax_rate=Decimal('21.00'),
            is_active=True
        )
        
        # Crear lotes con diferentes fechas de vencimiento
        today = date.today()
        
        # Lote que vence en 10 días (debe salir primero)
        create_entry(
            product=self.product,
            lot_code='LOT-EARLY',
            expiry_date=today + timedelta(days=10),
            qty=Decimal('5'),
            unit_cost=Decimal('4.00'),
            warehouse=self.warehouse,
            created_by=self.user
        )
        
        # Lote que vence en 30 días (debe salir segundo)
        create_entry(
            product=self.product,
            lot_code='LOT-LATE',
            expiry_date=today + timedelta(days=30),
            qty=Decimal('8'),
            unit_cost=Decimal('5.00'),
            warehouse=self.warehouse,
            created_by=self.user
        )
    
    def test_fefo_single_lot_sufficient(self):
        """Test FEFO cuando un solo lote es suficiente."""
        movements = create_exit(
            product=self.product,
            qty_total=Decimal('3'),
            warehouse=self.warehouse,
            created_by=self.user
        )
        
        assert len(movements) == 1
        assert movements[0].lot.lot_code == 'LOT-EARLY'  # Debe usar el que vence primero
        assert movements[0].qty == Decimal('3')
        
        # Verificar que se descontó del lote correcto
        lot_early = StockLot.objects.get(lot_code='LOT-EARLY')
        assert lot_early.qty_on_hand == Decimal('2')  # 5 - 3 = 2
    
    def test_fefo_multiple_lots_required(self):
        """Test FEFO cuando se necesitan múltiples lotes."""
        movements = create_exit(
            product=self.product,
            qty_total=Decimal('10'),  # Necesita ambos lotes
            warehouse=self.warehouse,
            created_by=self.user
        )
        
        assert len(movements) == 2
        
        # Primer movimiento debe ser del lote que vence primero
        assert movements[0].lot.lot_code == 'LOT-EARLY'
        assert movements[0].qty == Decimal('5')  # Todo el lote
        
        # Segundo movimiento del lote que vence después
        assert movements[1].lot.lot_code == 'LOT-LATE'
        assert movements[1].qty == Decimal('5')  # Parte del lote
        
        # Verificar cantidades finales
        lot_early = StockLot.objects.get(lot_code='LOT-EARLY')
        lot_late = StockLot.objects.get(lot_code='LOT-LATE')
        assert lot_early.qty_on_hand == Decimal('0')
        assert lot_late.qty_on_hand == Decimal('3')  # 8 - 5 = 3
    
    def test_fefo_respects_quarantine_and_reserved(self):
        """Test que FEFO respeta lotes en cuarentena y reservados."""
        # Poner el lote que vence primero en cuarentena
        lot_early = StockLot.objects.get(lot_code='LOT-EARLY')
        lot_early.is_quarantined = True
        lot_early.save()
        
        movements = create_exit(
            product=self.product,
            qty_total=Decimal('3'),
            warehouse=self.warehouse,
            created_by=self.user
        )
        
        # Debe usar el segundo lote (no en cuarentena)
        assert len(movements) == 1
        assert movements[0].lot.lot_code == 'LOT-LATE'
        assert movements[0].qty == Decimal('3')
    
    def test_not_enough_stock_error(self):
        """Test error cuando no hay suficiente stock disponible."""
        with pytest.raises(NotEnoughStock) as exc_info:
            create_exit(
                product=self.product,
                qty_total=Decimal('20'),  # Más de lo disponible (5 + 8 = 13)
                warehouse=self.warehouse,
                created_by=self.user
            )
        
        assert exc_info.value.product_id == self.product.id
        assert exc_info.value.requested == Decimal('20')
        assert exc_info.value.available == Decimal('13')
    
    def test_no_lots_available_error(self):
        """Test error cuando no hay lotes disponibles."""
        # Poner todos los lotes en cuarentena
        StockLot.objects.filter(product=self.product).update(is_quarantined=True)
        
        with pytest.raises(NotEnoughStock):  # Se convierte en NotEnoughStock porque available=0
            create_exit(
                product=self.product,
                qty_total=Decimal('1'),
                warehouse=self.warehouse,
                created_by=self.user
            )


class TestStockConcurrency(TransactionTestCase):
    """Tests para concurrencia usando TransactionTestCase."""
    
    def setUp(self):
        """Setup test data."""
        self.user = User.objects.create_user(username='testuser')
        self.warehouse = Warehouse.objects.create(name='Main Warehouse', is_active=True)
        self.product = Product.objects.create(
            code='TEST-001',
            name='Test Product',
            price=Decimal('10.00'),
            tax_rate=Decimal('21.00'),
            is_active=True
        )
        
        # Crear un lote con stock limitado
        create_entry(
            product=self.product,
            lot_code='LOT-CONCURRENT',
            expiry_date=date.today() + timedelta(days=30),
            qty=Decimal('10'),
            unit_cost=Decimal('5.00'),
            warehouse=self.warehouse,
            created_by=self.user
        )
    
    def test_concurrent_exits_no_negative_stock(self):
        """Test que salidas concurrentes no dejan stock negativo."""
        results = []
        errors = []
        
        def create_exit_worker(qty):
            """Worker function para crear salidas concurrentes."""
            try:
                with transaction.atomic():
                    movements = create_exit(
                        product=self.product,
                        qty_total=Decimal(str(qty)),
                        warehouse=self.warehouse,
                        created_by=self.user
                    )
                    results.append(sum(mv.qty for mv in movements))
            except Exception as e:
                errors.append(e)
        
        # Ejecutar 5 salidas concurrentes de 3 unidades cada una
        # Solo deberían pasar 3 (total 9), las otras 2 deberían fallar
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_exit_worker, 3) for _ in range(5)]
            for future in as_completed(futures):
                future.result()  # Esperar a que termine
        
        # Verificar resultados
        total_successful_qty = sum(results)
        assert total_successful_qty <= 10  # No puede exceder el stock inicial
        assert len(errors) >= 2  # Al menos 2 operaciones deben fallar
        
        # Verificar que el stock final no es negativo
        lot = StockLot.objects.get(lot_code='LOT-CONCURRENT')
        assert lot.qty_on_hand >= 0
        assert lot.qty_on_hand == 10 - total_successful_qty


@pytest.mark.django_db
class TestStockEdgeCases:
    """Tests para casos edge del sistema de stock."""
    
    def setup_method(self):
        """Setup test data."""
        self.user = User.objects.create_user(username='testuser')
        self.warehouse = Warehouse.objects.create(name='Main Warehouse', is_active=True)
        self.product = Product.objects.create(
            code='TEST-001',
            name='Test Product',
            price=Decimal('10.00'),
            tax_rate=Decimal('21.00'),
            is_active=True
        )
    
    def test_create_entry_updates_existing_lot(self):
        """Test que crear entrada actualiza lote existente correctamente."""
        # Primera entrada
        movement1 = create_entry(
            product=self.product,
            lot_code='LOT001',
            expiry_date=date.today() + timedelta(days=30),
            qty=Decimal('10'),
            unit_cost=Decimal('5.00'),
            warehouse=self.warehouse,
            created_by=self.user
        )
        
        # Segunda entrada al mismo lote
        movement2 = create_entry(
            product=self.product,
            lot_code='LOT001',
            expiry_date=date.today() + timedelta(days=30),  # Misma fecha
            qty=Decimal('5'),
            unit_cost=Decimal('5.00'),
            warehouse=self.warehouse,
            created_by=self.user
        )
        
        # Deben usar el mismo lote
        assert movement1.lot.id == movement2.lot.id
        
        # El lote debe tener la suma de cantidades
        lot = StockLot.objects.get(id=movement1.lot.id)
        assert lot.qty_on_hand == Decimal('15')
    
    def test_exit_with_exact_lot_quantity(self):
        """Test salida que agota exactamente un lote."""
        # Crear entrada
        create_entry(
            product=self.product,
            lot_code='LOT001',
            expiry_date=date.today() + timedelta(days=30),
            qty=Decimal('10'),
            unit_cost=Decimal('5.00'),
            warehouse=self.warehouse,
            created_by=self.user
        )
        
        # Salida que agota exactamente el lote
        movements = create_exit(
            product=self.product,
            qty_total=Decimal('10'),
            warehouse=self.warehouse,
            created_by=self.user
        )
        
        assert len(movements) == 1
        assert movements[0].qty == Decimal('10')
        
        # El lote debe quedar en 0
        lot = StockLot.objects.get(lot_code='LOT001')
        assert lot.qty_on_hand == Decimal('0')
    
    def test_movement_reason_choices(self):
        """Test que los motivos de movimiento usan las opciones correctas."""
        # Entrada con motivo de compra
        movement_entry = create_entry(
            product=self.product,
            lot_code='LOT001',
            expiry_date=date.today() + timedelta(days=30),
            qty=Decimal('10'),
            unit_cost=Decimal('5.00'),
            warehouse=self.warehouse,
            reason=Movement.Reason.PURCHASE,
            created_by=self.user
        )
        
        assert movement_entry.reason == Movement.Reason.PURCHASE
        
        # Salida con motivo de venta
        movements_exit = create_exit(
            product=self.product,
            qty_total=Decimal('5'),
            warehouse=self.warehouse,
            reason=Movement.Reason.SALE,
            created_by=self.user
        )
        
        assert movements_exit[0].reason == Movement.Reason.SALE
    
    def test_pick_lots_fefo_helper(self):
        """Test del helper pick_lots_fefo independientemente."""
        today = date.today()
        
        # Crear múltiples lotes
        create_entry(
            product=self.product,
            lot_code='LOT-1',
            expiry_date=today + timedelta(days=10),
            qty=Decimal('5'),
            unit_cost=Decimal('4.00'),
            warehouse=self.warehouse,
            created_by=self.user
        )
        
        create_entry(
            product=self.product,
            lot_code='LOT-2',
            expiry_date=today + timedelta(days=5),  # Vence antes
            qty=Decimal('3'),
            unit_cost=Decimal('4.50'),
            warehouse=self.warehouse,
            created_by=self.user
        )
        
        # Usar el helper
        allocation_plan = pick_lots_fefo(
            product=self.product,
            qty_needed=Decimal('6'),
            warehouse=self.warehouse
        )
        
        assert len(allocation_plan) == 2
        
        # Primer lote debe ser el que vence antes
        lot_2 = StockLot.objects.get(lot_code='LOT-2')
        assert allocation_plan[0]['lot_id'] == lot_2.id
        assert allocation_plan[0]['qty_to_take'] == Decimal('3')
        
        # Segundo lote debe ser el siguiente
        lot_1 = StockLot.objects.get(lot_code='LOT-1')
        assert allocation_plan[1]['lot_id'] == lot_1.id
        assert allocation_plan[1]['qty_to_take'] == Decimal('3')  # 6 - 3 = 3


# ============================================================================
# EVENT-DRIVEN SERVICES TESTS
# ============================================================================

@pytest.mark.django_db
class TestEventDrivenStockServices:
    """Tests para los nuevos servicios event-driven de stock."""
    
    def setup_method(self):
        """Setup test data."""
        self.user = User.objects.create_user(username='eventuser', password='testpass')
        self.warehouse = Warehouse.objects.create(name='Event Warehouse', is_active=True)
        self.product = Product.objects.create(
            code='EVENT-001',
            name='Event Product',
            price=Decimal('10.00'),
            tax_rate=Decimal('21.00'),
            is_active=True
        )

    @patch('apps.stock.services.publish_event')
    def test_request_stock_entry_publishes_event(self, mock_publish):
        """Test que request_stock_entry publica el evento correcto."""
        # Arrange
        entry_data = {
            "product_id": str(self.product.id),
            "lot_code": "EVENT-LOT-001",
            "expiry_date": date.today() + timedelta(days=30),
            "quantity": Decimal("15.00"),
            "unit_cost": Decimal("8.50"),
            "warehouse_id": str(self.warehouse.id),
            "created_by_id": str(self.user.id),
            "reason": "purchase"
        }
        
        # Act
        result = request_stock_entry(**entry_data)
        
        # Assert
        assert result["success"] is True
        assert "entry_id" in result
        mock_publish.assert_called_once()
        
        # Verificar el evento publicado
        published_event = mock_publish.call_args[0][0]
        assert isinstance(published_event, StockEntryRequested)
        assert published_event.product_id == str(self.product.id)
        assert published_event.lot_code == "EVENT-LOT-001"
        assert published_event.quantity == Decimal("15.00")

    @patch('apps.stock.services.publish_event')
    def test_request_stock_exit_publishes_event(self, mock_publish):
        """Test que request_stock_exit publica el evento correcto."""
        # Arrange
        exit_data = {
            "product_id": str(self.product.id),
            "quantity": Decimal("5.00"),
            "warehouse_id": str(self.warehouse.id),
            "created_by_id": str(self.user.id),
            "reason": "sale"
        }
        
        # Act
        result = request_stock_exit(**exit_data)
        
        # Assert
        assert result["success"] is True
        assert "exit_id" in result
        mock_publish.assert_called_once()
        
        # Verificar el evento publicado
        published_event = mock_publish.call_args[0][0]
        assert isinstance(published_event, StockExitRequested)
        assert published_event.product_id == str(self.product.id)
        assert published_event.quantity == Decimal("5.00")

    @patch('apps.stock.services.publish_event')
    def test_validate_stock_availability_publishes_event(self, mock_publish):
        """Test que validate_stock_availability publica el evento correcto."""
        # Act
        result = validate_stock_availability(
            product_id=str(self.product.id),
            quantity=Decimal("10.00"),
            warehouse_id=str(self.warehouse.id)
        )
        
        # Assert
        assert result["success"] is True
        assert "validation_id" in result
        mock_publish.assert_called_once()
        
        # Verificar el evento publicado
        published_event = mock_publish.call_args[0][0]
        assert isinstance(published_event, StockValidationRequested)
        assert published_event.product_id == str(self.product.id)
        assert published_event.quantity == Decimal("10.00")

    @patch('apps.stock.services.publish_event')
    def test_validate_warehouse_publishes_event(self, mock_publish):
        """Test que validate_warehouse publica el evento correcto."""
        # Act
        result = validate_warehouse(warehouse_id=str(self.warehouse.id))
        
        # Assert
        assert result["success"] is True
        assert "validation_id" in result
        mock_publish.assert_called_once()
        
        # Verificar el evento publicado
        published_event = mock_publish.call_args[0][0]
        assert isinstance(published_event, WarehouseValidationRequested)
        assert published_event.warehouse_id == str(self.warehouse.id)

    @patch('apps.stock.services.publish_event')
    def test_request_stock_entry_with_optional_parameters(self, mock_publish):
        """Test request_stock_entry con parámetros opcionales."""
        # Act
        result = request_stock_entry(
            product_id=str(self.product.id),
            lot_code="OPT-LOT-001",
            expiry_date=date.today() + timedelta(days=60),
            quantity=Decimal("25.00"),
            unit_cost=Decimal("12.00"),
            warehouse_id=str(self.warehouse.id),
            created_by_id=str(self.user.id),
            reason="adjustment",
            notes="Test adjustment"
        )
        
        # Assert
        assert result["success"] is True
        mock_publish.assert_called_once()
        
        published_event = mock_publish.call_args[0][0]
        assert published_event.reason == "adjustment"
        assert published_event.notes == "Test adjustment"

    @patch('apps.stock.services.publish_event')
    def test_validate_stock_availability_with_order_id(self, mock_publish):
        """Test validate_stock_availability con order_id."""
        # Act
        result = validate_stock_availability(
            product_id=str(self.product.id),
            quantity=Decimal("7.00"),
            warehouse_id=str(self.warehouse.id),
            order_id="ORDER-12345"
        )
        
        # Assert
        assert result["success"] is True
        mock_publish.assert_called_once()
        
        published_event = mock_publish.call_args[0][0]
        assert published_event.order_id == "ORDER-12345"

    def test_request_stock_entry_validation_errors(self):
        """Test validaciones de entrada en request_stock_entry."""
        # Test cantidad negativa
        with pytest.raises(ValueError, match="Quantity must be positive"):
            request_stock_entry(
                product_id=str(self.product.id),
                lot_code="INVALID-LOT",
                expiry_date=date.today() + timedelta(days=30),
                quantity=Decimal("-5.00"),  # Negativo
                unit_cost=Decimal("8.00"),
                warehouse_id=str(self.warehouse.id),
                created_by_id=str(self.user.id)
            )
        
        # Test costo unitario negativo
        with pytest.raises(ValueError, match="Unit cost must be positive"):
            request_stock_entry(
                product_id=str(self.product.id),
                lot_code="INVALID-LOT",
                expiry_date=date.today() + timedelta(days=30),
                quantity=Decimal("5.00"),
                unit_cost=Decimal("-8.00"),  # Negativo
                warehouse_id=str(self.warehouse.id),
                created_by_id=str(self.user.id)
            )

    def test_request_stock_exit_validation_errors(self):
        """Test validaciones de salida en request_stock_exit."""
        # Test cantidad negativa
        with pytest.raises(ValueError, match="Quantity must be positive"):
            request_stock_exit(
                product_id=str(self.product.id),
                quantity=Decimal("-3.00"),  # Negativo
                warehouse_id=str(self.warehouse.id),
                created_by_id=str(self.user.id)
            )

    def test_validate_stock_availability_validation_errors(self):
        """Test validaciones en validate_stock_availability."""
        # Test cantidad negativa
        with pytest.raises(ValueError, match="Quantity must be positive"):
            validate_stock_availability(
                product_id=str(self.product.id),
                quantity=Decimal("-1.00"),  # Negativo
                warehouse_id=str(self.warehouse.id)
            )


@pytest.mark.django_db
class TestEventDrivenCompatibility:
    """Tests para verificar compatibilidad entre servicios legacy y event-driven."""
    
    def setup_method(self):
        """Setup test data."""
        self.user = User.objects.create_user(username='compatuser', password='testpass')
        self.warehouse = Warehouse.objects.create(name='Compat Warehouse', is_active=True)
        self.product = Product.objects.create(
            code='COMPAT-001',
            name='Compatibility Product',
            price=Decimal('15.00'),
            tax_rate=Decimal('21.00'),
            is_active=True
        )

    @patch('apps.stock.services.publish_event')
    def test_legacy_and_event_driven_coexistence(self, mock_publish):
        """Test que los servicios legacy y event-driven pueden coexistir."""
        # Usar servicio legacy para crear entrada
        legacy_movement = create_entry(
            product=self.product,
            lot_code='LEGACY-LOT',
            expiry_date=date.today() + timedelta(days=30),
            qty=Decimal('20'),
            unit_cost=Decimal('10.00'),
            warehouse=self.warehouse,
            created_by=self.user
        )
        
        # Usar servicio event-driven para solicitar salida
        event_result = request_stock_exit(
            product_id=str(self.product.id),
            quantity=Decimal("5.00"),
            warehouse_id=str(self.warehouse.id),
            created_by_id=str(self.user.id),
            reason="sale"
        )
        
        # Assert - ambos deberían funcionar
        assert legacy_movement.type == Movement.Type.ENTRY
        assert legacy_movement.qty == Decimal('20')
        
        assert event_result["success"] is True
        mock_publish.assert_called_once()
        
        # Verificar que el stock creado por legacy está disponible
        stock_lot = StockLot.objects.get(lot_code='LEGACY-LOT')
        assert stock_lot.qty_on_hand == Decimal('20')

    def test_legacy_services_still_functional(self):
        """Test que los servicios legacy siguen funcionando correctamente."""
        # Test create_entry legacy
        movement = create_entry(
            product=self.product,
            lot_code='LEGACY-TEST',
            expiry_date=date.today() + timedelta(days=45),
            qty=Decimal('30'),
            unit_cost=Decimal('12.00'),
            warehouse=self.warehouse,
            created_by=self.user
        )
        
        assert movement.type == Movement.Type.ENTRY
        assert movement.qty == Decimal('30')
        
        # Test create_exit legacy
        exit_movements = create_exit(
            product=self.product,
            qty_total=Decimal('10'),
            warehouse=self.warehouse,
            created_by=self.user
        )
        
        assert len(exit_movements) == 1
        assert exit_movements[0].type == Movement.Type.EXIT
        assert exit_movements[0].qty == Decimal('10')
        
        # Verificar stock final
        stock_lot = StockLot.objects.get(lot_code='LEGACY-TEST')
        assert stock_lot.qty_on_hand == Decimal('20')  # 30 - 10