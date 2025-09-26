"""Minimal unit tests for stock models - creación básica + defaults + __str__."""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from apps.catalog.models import Product
from apps.stock.models import Warehouse, StockLot, Movement

User = get_user_model()


@pytest.mark.unit
@pytest.mark.django_db
class TestWarehouseMinimal:
    """Minimal tests for Warehouse model."""
    
    def test_warehouse_creation_basic(self):
        """Test basic warehouse creation with minimal fields."""
        warehouse = Warehouse.objects.create(
            name="Test Warehouse"
        )
        assert warehouse.id is not None
        assert warehouse.name == "Test Warehouse"
    
    def test_warehouse_defaults(self):
        """Test warehouse default values."""
        warehouse = Warehouse.objects.create(
            name="Test Warehouse 2"
        )
        # Test default values
        assert warehouse.is_active is True
    
    def test_warehouse_str_representation(self):
        """Test warehouse string representation."""
        warehouse = Warehouse.objects.create(
            name="Test Warehouse 3"
        )
        assert str(warehouse) == "Test Warehouse 3"


@pytest.mark.unit
@pytest.mark.django_db
class TestStockLotMinimal:
    """Minimal tests for StockLot model."""
    
    def test_stock_lot_creation_basic(self):
        """Test basic stock lot creation with minimal fields."""
        # Create dependencies
        product = Product.objects.create(
            code="TEST-001",
            name="Test Product",
            price=Decimal("10.00"),
            tax_rate=Decimal("21.00")
        )
        warehouse = Warehouse.objects.create(name="Test Warehouse")
        
        stock_lot = StockLot.objects.create(
            product=product,
            lot_code="LOT-001",
            expiry_date=date.today() + timedelta(days=30),
            unit_cost=Decimal("8.00"),
            warehouse=warehouse
        )
        assert stock_lot.id is not None
        assert stock_lot.product == product
        assert stock_lot.lot_code == "LOT-001"
        assert stock_lot.unit_cost == Decimal("8.00")
        assert stock_lot.warehouse == warehouse
    
    def test_stock_lot_defaults(self):
        """Test stock lot default values."""
        # Create dependencies
        product = Product.objects.create(
            code="TEST-002",
            name="Test Product 2",
            price=Decimal("10.00"),
            tax_rate=Decimal("21.00")
        )
        warehouse = Warehouse.objects.create(name="Test Warehouse 2")
        
        stock_lot = StockLot.objects.create(
            product=product,
            lot_code="LOT-002",
            expiry_date=date.today() + timedelta(days=30),
            unit_cost=Decimal("8.00"),
            warehouse=warehouse
        )
        # Test default values
        assert stock_lot.qty_on_hand == Decimal("0")
        assert stock_lot.is_quarantined is False
        assert stock_lot.is_reserved is False
    
    def test_stock_lot_str_representation(self):
        """Test stock lot string representation."""
        # Create dependencies
        product = Product.objects.create(
            code="TEST-003",
            name="Test Product 3",
            price=Decimal("10.00"),
            tax_rate=Decimal("21.00")
        )
        warehouse = Warehouse.objects.create(name="Test Warehouse 3")
        
        stock_lot = StockLot.objects.create(
            product=product,
            lot_code="LOT-003",
            expiry_date=date.today() + timedelta(days=30),
            unit_cost=Decimal("8.00"),
            warehouse=warehouse
        )
        # The actual format is "{product_id}-{lot_code}"
        expected_str = f"{product.id}-LOT-003"
        assert str(stock_lot) == expected_str


@pytest.mark.unit
@pytest.mark.django_db
class TestMovementMinimal:
    """Minimal tests for Movement model."""
    
    def test_movement_creation_basic(self):
        """Test basic movement creation with minimal fields."""
        # Create dependencies
        product = Product.objects.create(
            code="TEST-004",
            name="Test Product 4",
            price=Decimal("10.00"),
            tax_rate=Decimal("21.00")
        )
        warehouse = Warehouse.objects.create(name="Test Warehouse 4")
        user = User.objects.create_user(username="testuser", password="testpass")
        
        # Create a stock lot for entry movement
        stock_lot = StockLot.objects.create(
            product=product,
            lot_code="LOT-004",
            expiry_date=date.today() + timedelta(days=30),
            unit_cost=Decimal("8.00"),
            warehouse=warehouse
        )
        
        movement = Movement.objects.create(
            product=product,
            lot=stock_lot,
            type=Movement.Type.ENTRY,
            reason=Movement.Reason.PURCHASE,
            qty=Decimal("10.00"),
            unit_cost=Decimal("8.00"),
            created_by=user
        )
        assert movement.id is not None
        assert movement.product == product
        assert movement.lot == stock_lot
        assert movement.type == Movement.Type.ENTRY
        assert movement.qty == Decimal("10.00")
    
    def test_movement_str_representation(self):
        """Test movement string representation."""
        # Create dependencies
        product = Product.objects.create(
            code="TEST-005",
            name="Test Product 5",
            price=Decimal("10.00"),
            tax_rate=Decimal("21.00")
        )
        warehouse = Warehouse.objects.create(name="Test Warehouse 5")
        user = User.objects.create_user(username="testuser2", password="testpass")
        
        # Create a stock lot for exit movement
        stock_lot = StockLot.objects.create(
            product=product,
            lot_code="LOT-005",
            expiry_date=date.today() + timedelta(days=30),
            unit_cost=Decimal("8.00"),
            warehouse=warehouse
        )
        
        movement = Movement.objects.create(
            product=product,
            lot=stock_lot,
            type=Movement.Type.EXIT,
            reason=Movement.Reason.SALE,
            qty=Decimal("5.00"),
            created_by=user
        )
        # The actual format is "{type.title()} · {product.code} · {qty}"
        expected_str = f"Exit · {product.code} · 5.00"
        assert str(movement) == expected_str