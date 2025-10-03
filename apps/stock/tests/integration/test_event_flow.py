"""
Tests de integración para el flujo completo de eventos del dominio Stock.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from django.test import TransactionTestCase
from django.contrib.auth.models import User
from django.db import transaction

from apps.catalog.models import Product
from apps.stock.models import StockLot, Movement, Warehouse
from apps.stock.services import (
    request_stock_entry,
    request_stock_exit,
    validate_stock_availability,
    validate_warehouse
)
from apps.stock.events import (
    StockEntryRequested,
    StockExitRequested,
    StockValidationRequested,
    WarehouseValidationRequested
)
from apps.stock.event_handlers import (
    StockEntryHandler,
    StockExitHandler,
    StockIntegrationHandler,
    WarehouseValidationHandler
)
from core.events.manager import EventSystemManager


@pytest.mark.integration
@pytest.mark.django_db
class TestStockEventFlow(TransactionTestCase):
    """Tests de integración para el flujo completo de eventos de stock."""
    
    def setUp(self):
        """Setup para cada test."""
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.warehouse = Warehouse.objects.create(name="Test Warehouse", is_active=True)
        self.product = Product.objects.create(
            code="TEST-001",
            name="Test Product",
            price=Decimal("10.00"),
            tax_rate=Decimal("21.00"),
            is_active=True,
            min_stock=Decimal("5.00")
        )
        
        # Configurar event system manager
        self.event_manager = EventSystemManager()
        
        # Registrar handlers
        self.entry_handler = StockEntryHandler()
        self.exit_handler = StockExitHandler()
        self.integration_handler = StockIntegrationHandler()
        self.warehouse_handler = WarehouseValidationHandler()

    def test_complete_stock_entry_flow(self):
        """Test del flujo completo de entrada de stock."""
        # Arrange
        entry_data = {
            "product_id": str(self.product.id),
            "lot_code": "LOT-001",
            "expiry_date": date.today() + timedelta(days=30),
            "quantity": Decimal("20.00"),
            "unit_cost": Decimal("8.00"),
            "warehouse_id": str(self.warehouse.id),
            "created_by_id": str(self.user.id),
            "reason": "purchase"
        }
        
        # Act - solicitar entrada de stock
        with patch('apps.stock.services.publish_event') as mock_publish:
            result = request_stock_entry(**entry_data)
        
        # Assert - verificar que se publicó el evento
        assert result["success"] is True
        mock_publish.assert_called_once()
        
        # Simular procesamiento del evento por el handler
        event = mock_publish.call_args[0][0]
        assert isinstance(event, StockEntryRequested)
        
        # Procesar evento con handler
        handler_result = self.entry_handler.handle(event)
        assert handler_result.success is True
        
        # Verificar estado final
        stock_lot = StockLot.objects.get(lot_code="LOT-001")
        assert stock_lot.qty_on_hand == Decimal("20.00")
        assert stock_lot.product == self.product
        
        movement = Movement.objects.get(lot=stock_lot)
        assert movement.type == Movement.Type.ENTRY
        assert movement.qty == Decimal("20.00")

    def test_complete_stock_exit_flow(self):
        """Test del flujo completo de salida de stock."""
        # Arrange - crear stock inicial
        stock_lot = StockLot.objects.create(
            product=self.product,
            lot_code="LOT-002",
            expiry_date=date.today() + timedelta(days=30),
            qty_on_hand=Decimal("15.00"),
            unit_cost=Decimal("8.00"),
            warehouse=self.warehouse
        )
        
        exit_data = {
            "product_id": str(self.product.id),
            "quantity": Decimal("5.00"),
            "warehouse_id": str(self.warehouse.id),
            "created_by_id": str(self.user.id),
            "reason": "sale"
        }
        
        # Act - solicitar salida de stock
        with patch('apps.stock.services.publish_event') as mock_publish:
            result = request_stock_exit(**exit_data)
        
        # Assert - verificar que se publicó el evento
        assert result["success"] is True
        mock_publish.assert_called_once()
        
        # Simular procesamiento del evento por el handler
        event = mock_publish.call_args[0][0]
        assert isinstance(event, StockExitRequested)
        
        # Procesar evento con handler
        handler_result = self.exit_handler.handle(event)
        assert handler_result.success is True
        
        # Verificar estado final
        stock_lot.refresh_from_db()
        assert stock_lot.qty_on_hand == Decimal("10.00")  # 15 - 5
        
        exit_movement = Movement.objects.get(type=Movement.Type.EXIT)
        assert exit_movement.qty == Decimal("5.00")

    def test_stock_validation_flow(self):
        """Test del flujo de validación de stock."""
        # Arrange - crear stock disponible
        StockLot.objects.create(
            product=self.product,
            lot_code="LOT-003",
            expiry_date=date.today() + timedelta(days=30),
            qty_on_hand=Decimal("12.00"),
            unit_cost=Decimal("8.00"),
            warehouse=self.warehouse
        )
        
        # Act - validar disponibilidad
        with patch('apps.stock.services.publish_event') as mock_publish:
            result = validate_stock_availability(
                product_id=str(self.product.id),
                quantity=Decimal("8.00"),
                warehouse_id=str(self.warehouse.id)
            )
        
        # Assert - verificar que se publicó el evento
        assert result["success"] is True
        mock_publish.assert_called_once()
        
        # Simular procesamiento del evento por el handler
        event = mock_publish.call_args[0][0]
        assert isinstance(event, StockValidationRequested)
        
        # Procesar evento con handler
        handler_result = self.integration_handler.handle(event)
        assert handler_result.success is True

    def test_warehouse_validation_flow(self):
        """Test del flujo de validación de warehouse."""
        # Act - validar warehouse
        with patch('apps.stock.services.publish_event') as mock_publish:
            result = validate_warehouse(warehouse_id=str(self.warehouse.id))
        
        # Assert - verificar que se publicó el evento
        assert result["success"] is True
        mock_publish.assert_called_once()
        
        # Simular procesamiento del evento por el handler
        event = mock_publish.call_args[0][0]
        assert isinstance(event, WarehouseValidationRequested)
        
        # Procesar evento con handler
        handler_result = self.warehouse_handler.handle(event)
        assert handler_result.success is True

    def test_insufficient_stock_flow(self):
        """Test del flujo con stock insuficiente."""
        # Arrange - crear stock limitado
        StockLot.objects.create(
            product=self.product,
            lot_code="LOT-004",
            expiry_date=date.today() + timedelta(days=30),
            qty_on_hand=Decimal("3.00"),
            unit_cost=Decimal("8.00"),
            warehouse=self.warehouse
        )
        
        exit_data = {
            "product_id": str(self.product.id),
            "quantity": Decimal("5.00"),  # Más del disponible
            "warehouse_id": str(self.warehouse.id),
            "created_by_id": str(self.user.id),
            "reason": "sale"
        }
        
        # Act - intentar salida con stock insuficiente
        with patch('apps.stock.services.publish_event') as mock_publish:
            result = request_stock_exit(**exit_data)
        
        # Assert - verificar que se publicó el evento
        assert result["success"] is True
        mock_publish.assert_called_once()
        
        # Simular procesamiento del evento por el handler
        event = mock_publish.call_args[0][0]
        assert isinstance(event, StockExitRequested)
        
        # Procesar evento con handler - debería fallar
        handler_result = self.exit_handler.handle(event)
        assert handler_result.success is False
        assert "Insufficient stock" in handler_result.message

    def test_multiple_lots_fefo_flow(self):
        """Test del flujo FEFO con múltiples lotes."""
        # Arrange - crear múltiples lotes con diferentes fechas de vencimiento
        lot1 = StockLot.objects.create(
            product=self.product,
            lot_code="LOT-OLD",
            expiry_date=date.today() + timedelta(days=10),  # Vence antes
            qty_on_hand=Decimal("5.00"),
            unit_cost=Decimal("8.00"),
            warehouse=self.warehouse
        )
        
        lot2 = StockLot.objects.create(
            product=self.product,
            lot_code="LOT-NEW",
            expiry_date=date.today() + timedelta(days=30),  # Vence después
            qty_on_hand=Decimal("10.00"),
            unit_cost=Decimal("8.00"),
            warehouse=self.warehouse
        )
        
        exit_data = {
            "product_id": str(self.product.id),
            "quantity": Decimal("8.00"),  # Requiere ambos lotes
            "warehouse_id": str(self.warehouse.id),
            "created_by_id": str(self.user.id),
            "reason": "sale"
        }
        
        # Act - solicitar salida que requiere múltiples lotes
        with patch('apps.stock.services.publish_event') as mock_publish:
            result = request_stock_exit(**exit_data)
        
        # Assert
        assert result["success"] is True
        
        # Simular procesamiento del evento por el handler
        event = mock_publish.call_args[0][0]
        handler_result = self.exit_handler.handle(event)
        assert handler_result.success is True
        
        # Verificar que se aplicó FEFO correctamente
        lot1.refresh_from_db()
        lot2.refresh_from_db()
        
        # El lote más antiguo debería agotarse primero
        assert lot1.qty_on_hand == Decimal("0.00")  # 5 - 5 = 0
        assert lot2.qty_on_hand == Decimal("7.00")   # 10 - 3 = 7

    def test_concurrent_operations_flow(self):
        """Test del flujo con operaciones concurrentes."""
        # Arrange - crear stock inicial
        StockLot.objects.create(
            product=self.product,
            lot_code="LOT-CONCURRENT",
            expiry_date=date.today() + timedelta(days=30),
            qty_on_hand=Decimal("10.00"),
            unit_cost=Decimal("8.00"),
            warehouse=self.warehouse
        )
        
        # Act - simular operaciones concurrentes
        with transaction.atomic():
            # Primera operación: entrada
            with patch('apps.stock.services.publish_event') as mock_publish_entry:
                entry_result = request_stock_entry(
                    product_id=str(self.product.id),
                    lot_code="LOT-CONCURRENT",
                    expiry_date=date.today() + timedelta(days=30),
                    quantity=Decimal("5.00"),
                    unit_cost=Decimal("8.00"),
                    warehouse_id=str(self.warehouse.id),
                    created_by_id=str(self.user.id),
                    reason="purchase"
                )
            
            # Segunda operación: salida
            with patch('apps.stock.services.publish_event') as mock_publish_exit:
                exit_result = request_stock_exit(
                    product_id=str(self.product.id),
                    quantity=Decimal("3.00"),
                    warehouse_id=str(self.warehouse.id),
                    created_by_id=str(self.user.id),
                    reason="sale"
                )
        
        # Assert - ambas operaciones deberían ser exitosas
        assert entry_result["success"] is True
        assert exit_result["success"] is True
        
        # Verificar que se publicaron ambos eventos
        mock_publish_entry.assert_called_once()
        mock_publish_exit.assert_called_once()


@pytest.mark.integration
@pytest.mark.django_db
class TestStockEventPerformance(TransactionTestCase):
    """Tests de performance para el sistema de eventos de stock."""
    
    def setUp(self):
        """Setup para tests de performance."""
        self.user = User.objects.create_user(username="perfuser", password="testpass")
        self.warehouse = Warehouse.objects.create(name="Perf Warehouse", is_active=True)
        self.products = []
        
        # Crear múltiples productos para tests de performance
        for i in range(10):
            product = Product.objects.create(
                code=f"PERF-{i:03d}",
                name=f"Performance Product {i}",
                price=Decimal("10.00"),
                tax_rate=Decimal("21.00"),
                is_active=True
            )
            self.products.append(product)

    @patch('apps.stock.services.publish_event')
    def test_bulk_stock_operations_performance(self, mock_publish):
        """Test de performance para operaciones masivas de stock."""
        import time
        
        # Arrange
        operations_count = 50
        
        # Act - medir tiempo de operaciones masivas
        start_time = time.time()
        
        for i in range(operations_count):
            product = self.products[i % len(self.products)]
            
            # Entrada de stock
            request_stock_entry(
                product_id=str(product.id),
                lot_code=f"BULK-LOT-{i:03d}",
                expiry_date=date.today() + timedelta(days=30),
                quantity=Decimal("10.00"),
                unit_cost=Decimal("8.00"),
                warehouse_id=str(self.warehouse.id),
                created_by_id=str(self.user.id),
                reason="bulk_import"
            )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Assert - verificar que las operaciones se completaron en tiempo razonable
        assert execution_time < 5.0  # Menos de 5 segundos para 50 operaciones
        assert mock_publish.call_count == operations_count
        
        # Verificar que todos los eventos son del tipo correcto
        for call in mock_publish.call_args_list:
            event = call[0][0]
            assert isinstance(event, StockEntryRequested)

    @patch('apps.stock.services.publish_event')
    def test_event_publishing_overhead(self, mock_publish):
        """Test del overhead de publicación de eventos."""
        import time
        
        # Arrange
        product = self.products[0]
        
        # Act - medir tiempo de publicación de eventos
        start_time = time.time()
        
        for i in range(100):
            validate_stock_availability(
                product_id=str(product.id),
                quantity=Decimal("1.00"),
                warehouse_id=str(self.warehouse.id)
            )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Assert - verificar overhead mínimo
        assert execution_time < 2.0  # Menos de 2 segundos para 100 validaciones
        assert mock_publish.call_count == 100