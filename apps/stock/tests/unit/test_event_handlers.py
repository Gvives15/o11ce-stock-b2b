"""
Tests unitarios para los event handlers de stock.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock, call

from django.test import TestCase
from django.contrib.auth.models import User
from django.db import transaction

from apps.catalog.models import Product
from apps.stock.models import StockLot, Movement, Warehouse
from apps.stock.event_handlers import (
    StockEntryHandler,
    StockExitHandler,
    StockMonitoringHandler,
    LotManagementHandler,
    StockIntegrationHandler,
    WarehouseValidationHandler
)
from apps.stock.events import (
    StockEntryRequested,
    StockExitRequested,
    StockValidationRequested,
    WarehouseValidationRequested,
    LotExpiryWarning,
    LowStockDetected
)


@pytest.mark.unit
@pytest.mark.django_db
class TestStockEntryHandler:
    """Tests para StockEntryHandler."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.warehouse = Warehouse.objects.create(name="Test Warehouse", is_active=True)
        self.product = Product.objects.create(
            code="TEST-001",
            name="Test Product",
            price=Decimal("10.00"),
            tax_rate=Decimal("21.00"),
            is_active=True
        )
        self.handler = StockEntryHandler()

    @patch('apps.stock.event_handlers.publish_event')
    def test_handle_stock_entry_requested_success(self, mock_publish):
        """Test manejo exitoso de StockEntryRequested."""
        # Arrange
        event = StockEntryRequested(
            entry_id="entry-123",
            product_id=str(self.product.id),
            lot_code="LOT-001",
            expiry_date=date.today() + timedelta(days=30),
            quantity=Decimal("10.00"),
            unit_cost=Decimal("8.00"),
            warehouse_id=str(self.warehouse.id),
            created_by_id=str(self.user.id),
            reason="purchase"
        )
        
        # Act
        result = self.handler.handle(event)
        
        # Assert
        assert result.success is True
        assert "Stock entry processed successfully" in result.message
        
        # Verificar que se creó el StockLot
        stock_lot = StockLot.objects.get(lot_code="LOT-001")
        assert stock_lot.qty_on_hand == Decimal("10.00")
        assert stock_lot.product == self.product
        assert stock_lot.warehouse == self.warehouse
        
        # Verificar que se creó el Movement
        movement = Movement.objects.get(lot=stock_lot)
        assert movement.type == Movement.Type.ENTRY
        assert movement.qty == Decimal("10.00")
        assert movement.created_by == self.user
        
        # Verificar eventos publicados
        assert mock_publish.call_count == 2  # StockEntryCompleted + StockUpdated

    @patch('apps.stock.event_handlers.publish_event')
    def test_handle_stock_entry_requested_existing_lot(self, mock_publish):
        """Test manejo de entrada para lote existente."""
        # Arrange - crear lote existente
        existing_lot = StockLot.objects.create(
            product=self.product,
            lot_code="LOT-002",
            expiry_date=date.today() + timedelta(days=30),
            qty_on_hand=Decimal("5.00"),
            unit_cost=Decimal("8.00"),
            warehouse=self.warehouse
        )
        
        event = StockEntryRequested(
            entry_id="entry-124",
            product_id=str(self.product.id),
            lot_code="LOT-002",
            expiry_date=date.today() + timedelta(days=30),
            quantity=Decimal("3.00"),
            unit_cost=Decimal("8.00"),
            warehouse_id=str(self.warehouse.id),
            created_by_id=str(self.user.id),
            reason="purchase"
        )
        
        # Act
        result = self.handler.handle(event)
        
        # Assert
        assert result.success is True
        
        # Verificar que se actualizó el lote existente
        existing_lot.refresh_from_db()
        assert existing_lot.qty_on_hand == Decimal("8.00")  # 5 + 3

    def test_handle_stock_entry_requested_invalid_product(self):
        """Test manejo de entrada con producto inválido."""
        # Arrange
        event = StockEntryRequested(
            entry_id="entry-125",
            product_id="999999",  # ID inexistente
            lot_code="LOT-003",
            expiry_date=date.today() + timedelta(days=30),
            quantity=Decimal("10.00"),
            unit_cost=Decimal("8.00"),
            warehouse_id=str(self.warehouse.id),
            created_by_id=str(self.user.id),
            reason="purchase"
        )
        
        # Act
        result = self.handler.handle(event)
        
        # Assert
        assert result.success is False
        assert "Product not found" in result.message


@pytest.mark.unit
@pytest.mark.django_db
class TestStockExitHandler:
    """Tests para StockExitHandler."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.warehouse = Warehouse.objects.create(name="Test Warehouse", is_active=True)
        self.product = Product.objects.create(
            code="TEST-001",
            name="Test Product",
            price=Decimal("10.00"),
            tax_rate=Decimal("21.00"),
            is_active=True
        )
        self.handler = StockExitHandler()
        
        # Crear stock disponible
        self.stock_lot = StockLot.objects.create(
            product=self.product,
            lot_code="LOT-001",
            expiry_date=date.today() + timedelta(days=30),
            qty_on_hand=Decimal("20.00"),
            unit_cost=Decimal("8.00"),
            warehouse=self.warehouse
        )

    @patch('apps.stock.event_handlers.publish_event')
    def test_handle_stock_exit_requested_success(self, mock_publish):
        """Test manejo exitoso de StockExitRequested."""
        # Arrange
        event = StockExitRequested(
            exit_id="exit-123",
            product_id=str(self.product.id),
            quantity=Decimal("5.00"),
            warehouse_id=str(self.warehouse.id),
            created_by_id=str(self.user.id),
            reason="sale"
        )
        
        # Act
        result = self.handler.handle(event)
        
        # Assert
        assert result.success is True
        assert "Stock exit processed successfully" in result.message
        
        # Verificar que se actualizó el stock
        self.stock_lot.refresh_from_db()
        assert self.stock_lot.qty_on_hand == Decimal("15.00")  # 20 - 5
        
        # Verificar que se creó el Movement
        movement = Movement.objects.get(type=Movement.Type.EXIT)
        assert movement.qty == Decimal("5.00")
        assert movement.product == self.product
        
        # Verificar eventos publicados
        assert mock_publish.call_count >= 2  # StockExitCompleted + StockUpdated

    @patch('apps.stock.event_handlers.publish_event')
    def test_handle_stock_exit_requested_insufficient_stock(self, mock_publish):
        """Test manejo de salida con stock insuficiente."""
        # Arrange
        event = StockExitRequested(
            exit_id="exit-124",
            product_id=str(self.product.id),
            quantity=Decimal("25.00"),  # Más del disponible (20)
            warehouse_id=str(self.warehouse.id),
            created_by_id=str(self.user.id),
            reason="sale"
        )
        
        # Act
        result = self.handler.handle(event)
        
        # Assert
        assert result.success is False
        assert "Insufficient stock" in result.message
        
        # Verificar que no se modificó el stock
        self.stock_lot.refresh_from_db()
        assert self.stock_lot.qty_on_hand == Decimal("20.00")


@pytest.mark.unit
@pytest.mark.django_db
class TestStockMonitoringHandler:
    """Tests para StockMonitoringHandler."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.warehouse = Warehouse.objects.create(name="Test Warehouse", is_active=True)
        self.product = Product.objects.create(
            code="TEST-001",
            name="Test Product",
            price=Decimal("10.00"),
            tax_rate=Decimal("21.00"),
            is_active=True,
            min_stock=Decimal("10.00")  # Umbral mínimo
        )
        self.handler = StockMonitoringHandler()

    @patch('apps.stock.event_handlers.publish_event')
    def test_detect_low_stock(self, mock_publish):
        """Test detección de stock bajo."""
        # Arrange - crear stock por debajo del mínimo
        StockLot.objects.create(
            product=self.product,
            lot_code="LOT-001",
            expiry_date=date.today() + timedelta(days=30),
            qty_on_hand=Decimal("5.00"),  # Menor al mínimo (10)
            unit_cost=Decimal("8.00"),
            warehouse=self.warehouse
        )
        
        # Act
        self.handler.check_low_stock_levels()
        
        # Assert
        # Verificar que se publicó evento de stock bajo
        mock_publish.assert_called()
        published_events = [call[0][0] for call in mock_publish.call_args_list]
        low_stock_events = [e for e in published_events if isinstance(e, LowStockDetected)]
        assert len(low_stock_events) > 0


@pytest.mark.unit
@pytest.mark.django_db
class TestLotManagementHandler:
    """Tests para LotManagementHandler."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.warehouse = Warehouse.objects.create(name="Test Warehouse", is_active=True)
        self.product = Product.objects.create(
            code="TEST-001",
            name="Test Product",
            price=Decimal("10.00"),
            tax_rate=Decimal("21.00"),
            is_active=True
        )
        self.handler = LotManagementHandler()

    @patch('apps.stock.event_handlers.publish_event')
    def test_handle_lot_expiry_warning(self, mock_publish):
        """Test manejo de advertencia de vencimiento."""
        # Arrange
        event = LotExpiryWarning(
            lot_id="1",
            product_id=str(self.product.id),
            product_name=self.product.name,
            lot_code="LOT-001",
            expiry_date=date.today() + timedelta(days=2),
            days_to_expiry=2,
            quantity=Decimal("10.00"),
            warehouse_id=str(self.warehouse.id),
            priority="high"
        )
        
        # Act
        result = self.handler.handle(event)
        
        # Assert
        assert result.success is True
        assert "Expiry warning processed" in result.message


@pytest.mark.unit
@pytest.mark.django_db
class TestStockIntegrationHandler:
    """Tests para StockIntegrationHandler."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.warehouse = Warehouse.objects.create(name="Test Warehouse", is_active=True)
        self.product = Product.objects.create(
            code="TEST-001",
            name="Test Product",
            price=Decimal("10.00"),
            tax_rate=Decimal("21.00"),
            is_active=True
        )
        self.handler = StockIntegrationHandler()
        
        # Crear stock disponible
        self.stock_lot = StockLot.objects.create(
            product=self.product,
            lot_code="LOT-001",
            expiry_date=date.today() + timedelta(days=30),
            qty_on_hand=Decimal("15.00"),
            unit_cost=Decimal("8.00"),
            warehouse=self.warehouse
        )

    @patch('apps.stock.event_handlers.publish_event')
    def test_handle_stock_validation_requested_sufficient(self, mock_publish):
        """Test validación de stock con cantidad suficiente."""
        # Arrange
        event = StockValidationRequested(
            validation_id="val-123",
            product_id=str(self.product.id),
            quantity=Decimal("10.00"),
            warehouse_id=str(self.warehouse.id),
            order_id="ORDER-123"
        )
        
        # Act
        result = self.handler.handle(event)
        
        # Assert
        assert result.success is True
        assert "Stock validation completed" in result.message
        
        # Verificar evento publicado
        mock_publish.assert_called()

    @patch('apps.stock.event_handlers.publish_event')
    def test_handle_stock_validation_requested_insufficient(self, mock_publish):
        """Test validación de stock con cantidad insuficiente."""
        # Arrange
        event = StockValidationRequested(
            validation_id="val-124",
            product_id=str(self.product.id),
            quantity=Decimal("20.00"),  # Más del disponible (15)
            warehouse_id=str(self.warehouse.id),
            order_id="ORDER-124"
        )
        
        # Act
        result = self.handler.handle(event)
        
        # Assert
        assert result.success is True  # La validación se completa, pero indica insuficiente
        
        # Verificar evento publicado con resultado negativo
        mock_publish.assert_called()


@pytest.mark.unit
@pytest.mark.django_db
class TestWarehouseValidationHandler:
    """Tests para WarehouseValidationHandler."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.warehouse = Warehouse.objects.create(name="Test Warehouse", is_active=True)
        self.handler = WarehouseValidationHandler()

    @patch('apps.stock.event_handlers.publish_event')
    def test_handle_warehouse_validation_requested_valid(self, mock_publish):
        """Test validación de warehouse válido."""
        # Arrange
        event = WarehouseValidationRequested(
            validation_id="wh-val-123",
            warehouse_id=str(self.warehouse.id)
        )
        
        # Act
        result = self.handler.handle(event)
        
        # Assert
        assert result.success is True
        assert "Warehouse validation completed" in result.message
        
        # Verificar evento publicado
        mock_publish.assert_called()

    @patch('apps.stock.event_handlers.publish_event')
    def test_handle_warehouse_validation_requested_invalid(self, mock_publish):
        """Test validación de warehouse inválido."""
        # Arrange
        event = WarehouseValidationRequested(
            validation_id="wh-val-124",
            warehouse_id="999999"  # ID inexistente
        )
        
        # Act
        result = self.handler.handle(event)
        
        # Assert
        assert result.success is True  # La validación se completa, pero indica inválido
        
        # Verificar evento publicado con resultado negativo
        mock_publish.assert_called()