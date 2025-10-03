"""
Tests unitarios para los servicios event-driven de stock.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock, call

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

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


@pytest.mark.unit
@pytest.mark.django_db
class TestEventDrivenStockServices:
    """Tests para los servicios event-driven de stock."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.warehouse = Warehouse.objects.create(name="Test Warehouse")
        self.product = Product.objects.create(
            code="TEST-001",
            name="Test Product",
            price=Decimal("10.00"),
            tax_rate=Decimal("21.00")
        )

    @patch('apps.stock.services.EventSystemManager.publish_event')
    def test_request_stock_entry_publishes_event(self, mock_publish):
        """Test que request_stock_entry publica el evento correcto."""
        # Arrange
        entry_data = {
            'product_id': str(self.product.id),
            'lot_code': 'LOT-001',
            'expiry_date': date.today() + timedelta(days=30),
            'quantity': Decimal('10.00'),
            'unit_cost': Decimal('8.00'),
            'warehouse_id': str(self.warehouse.id),
            'created_by_id': str(self.user.id),
            'reason': 'purchase'
        }
        
        # Act
        result = request_stock_entry(**entry_data)
        
        # Assert
        assert result['status'] == 'requested'
        assert 'event_id' in result
        
        mock_publish.assert_called_once()
        published_event = mock_publish.call_args[0][0]
        assert isinstance(published_event, StockEntryRequested)
        assert published_event.product_id == str(self.product.id)
        assert published_event.lot_code == 'LOT-001'
        assert published_event.quantity == Decimal('10.00')
        assert published_event.unit_cost == Decimal('8.00')

    @patch('apps.stock.services.EventSystemManager.publish_event')
    def test_request_stock_exit_publishes_event(self, mock_publish):
        """Test que request_stock_exit publica el evento correcto."""
        # Arrange
        exit_data = {
            'product_id': str(self.product.id),
            'quantity': Decimal('5.00'),
            'warehouse_id': str(self.warehouse.id),
            'created_by_id': str(self.user.id),
            'reason': 'sale',
            'order_id': 'ORDER-123'
        }
        
        # Act
        result = request_stock_exit(**exit_data)
        
        # Assert
        assert result['status'] == 'requested'
        assert 'event_id' in result
        
        mock_publish.assert_called_once()
        published_event = mock_publish.call_args[0][0]
        assert isinstance(published_event, StockExitRequested)
        assert published_event.product_id == str(self.product.id)
        assert published_event.quantity == Decimal('5.00')
        assert published_event.order_id == 'ORDER-123'

    @patch('apps.stock.services.EventSystemManager.publish_event')
    def test_validate_stock_availability_publishes_event(self, mock_publish):
        """Test que validate_stock_availability publica el evento correcto."""
        # Arrange
        validation_data = {
            'product_id': str(self.product.id),
            'quantity': Decimal('3.00'),
            'warehouse_id': str(self.warehouse.id),
            'order_id': 'ORDER-456'
        }
        
        # Act
        result = validate_stock_availability(**validation_data)
        
        # Assert
        assert result['status'] == 'validation_requested'
        assert 'event_id' in result
        
        mock_publish.assert_called_once()
        published_event = mock_publish.call_args[0][0]
        assert isinstance(published_event, StockValidationRequested)
        assert published_event.product_id == str(self.product.id)
        assert published_event.quantity == Decimal('3.00')
        assert published_event.order_id == 'ORDER-456'

    @patch('apps.stock.services.EventSystemManager.publish_event')
    def test_validate_warehouse_publishes_event(self, mock_publish):
        """Test que validate_warehouse publica el evento correcto."""
        # Arrange
        warehouse_id = str(self.warehouse.id)
        
        # Act
        result = validate_warehouse(warehouse_id)
        
        # Assert
        assert result['status'] == 'validation_requested'
        assert 'event_id' in result
        
        mock_publish.assert_called_once()
        published_event = mock_publish.call_args[0][0]
        assert isinstance(published_event, WarehouseValidationRequested)
        assert published_event.warehouse_id == warehouse_id

    @patch('apps.stock.services.EventSystemManager.publish_event')
    def test_request_stock_entry_with_optional_fields(self, mock_publish):
        """Test request_stock_entry con campos opcionales."""
        # Arrange
        entry_data = {
            'product_id': str(self.product.id),
            'lot_code': 'LOT-002',
            'expiry_date': date.today() + timedelta(days=60),
            'quantity': Decimal('15.00'),
            'unit_cost': Decimal('12.00'),
            'warehouse_id': str(self.warehouse.id),
            'created_by_id': str(self.user.id),
            'reason': 'adjustment',
            'notes': 'Inventory adjustment',
            'supplier_id': 'SUPPLIER-123'
        }
        
        # Act
        result = request_stock_entry(**entry_data)
        
        # Assert
        assert result['status'] == 'requested'
        
        published_event = mock_publish.call_args[0][0]
        assert published_event.notes == 'Inventory adjustment'
        assert published_event.supplier_id == 'SUPPLIER-123'

    @patch('apps.stock.services.EventSystemManager.publish_event')
    def test_request_stock_exit_with_lot_overrides(self, mock_publish):
        """Test request_stock_exit con lot_overrides."""
        # Arrange
        exit_data = {
            'product_id': str(self.product.id),
            'quantity': Decimal('8.00'),
            'warehouse_id': str(self.warehouse.id),
            'created_by_id': str(self.user.id),
            'reason': 'sale',
            'lot_overrides': [
                {'lot_id': '1', 'quantity': Decimal('3.00')},
                {'lot_id': '2', 'quantity': Decimal('5.00')}
            ]
        }
        
        # Act
        result = request_stock_exit(**exit_data)
        
        # Assert
        assert result['status'] == 'requested'
        
        published_event = mock_publish.call_args[0][0]
        assert published_event.lot_overrides == exit_data['lot_overrides']

    def test_request_stock_entry_validation_errors(self):
        """Test validaciones de entrada en request_stock_entry."""
        # Test cantidad negativa
        with pytest.raises(ValueError, match="Quantity must be positive"):
            request_stock_entry(
                product_id=str(self.product.id),
                lot_code='LOT-003',
                expiry_date=date.today() + timedelta(days=30),
                quantity=Decimal('-1.00'),
                unit_cost=Decimal('8.00'),
                warehouse_id=str(self.warehouse.id),
                created_by_id=str(self.user.id)
            )
        
        # Test costo unitario negativo
        with pytest.raises(ValueError, match="Unit cost must be positive"):
            request_stock_entry(
                product_id=str(self.product.id),
                lot_code='LOT-004',
                expiry_date=date.today() + timedelta(days=30),
                quantity=Decimal('10.00'),
                unit_cost=Decimal('-5.00'),
                warehouse_id=str(self.warehouse.id),
                created_by_id=str(self.user.id)
            )

    def test_request_stock_exit_validation_errors(self):
        """Test validaciones de salida en request_stock_exit."""
        # Test cantidad negativa
        with pytest.raises(ValueError, match="Quantity must be positive"):
            request_stock_exit(
                product_id=str(self.product.id),
                quantity=Decimal('-2.00'),
                warehouse_id=str(self.warehouse.id),
                created_by_id=str(self.user.id)
            )

    def test_validate_stock_availability_validation_errors(self):
        """Test validaciones en validate_stock_availability."""
        # Test cantidad negativa
        with pytest.raises(ValueError, match="Quantity must be positive"):
            validate_stock_availability(
                product_id=str(self.product.id),
                quantity=Decimal('-1.00'),
                warehouse_id=str(self.warehouse.id)
            )


@pytest.mark.unit
@pytest.mark.django_db
class TestEventDrivenServiceIntegration:
    """Tests de integración para servicios event-driven."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.warehouse = Warehouse.objects.create(name="Test Warehouse")
        self.product = Product.objects.create(
            code="TEST-001",
            name="Test Product",
            price=Decimal("10.00"),
            tax_rate=Decimal("21.00")
        )

    @patch('apps.stock.services.EventSystemManager.publish_event')
    def test_event_driven_workflow_simulation(self, mock_publish):
        """Test simulación de workflow completo event-driven."""
        # 1. Solicitar entrada de stock
        entry_result = request_stock_entry(
            product_id=str(self.product.id),
            lot_code='LOT-WORKFLOW',
            expiry_date=date.today() + timedelta(days=30),
            quantity=Decimal('20.00'),
            unit_cost=Decimal('10.00'),
            warehouse_id=str(self.warehouse.id),
            created_by_id=str(self.user.id)
        )
        
        # 2. Validar disponibilidad
        validation_result = validate_stock_availability(
            product_id=str(self.product.id),
            quantity=Decimal('5.00'),
            warehouse_id=str(self.warehouse.id)
        )
        
        # 3. Solicitar salida de stock
        exit_result = request_stock_exit(
            product_id=str(self.product.id),
            quantity=Decimal('5.00'),
            warehouse_id=str(self.warehouse.id),
            created_by_id=str(self.user.id),
            reason='sale'
        )
        
        # Verificar que se publicaron 3 eventos
        assert mock_publish.call_count == 3
        
        # Verificar tipos de eventos
        published_events = [call[0][0] for call in mock_publish.call_args_list]
        assert isinstance(published_events[0], StockEntryRequested)
        assert isinstance(published_events[1], StockValidationRequested)
        assert isinstance(published_events[2], StockExitRequested)
        
        # Verificar resultados
        assert entry_result['status'] == 'requested'
        assert validation_result['status'] == 'validation_requested'
        assert exit_result['status'] == 'requested'