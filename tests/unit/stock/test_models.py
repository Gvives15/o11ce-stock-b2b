"""Tests for stock models."""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from apps.stock.models import StockLot, Movement, Warehouse
from apps.catalog.models import Product
from django.contrib.auth.models import User


@pytest.mark.django_db
class TestStockLot:
    """Tests for StockLot model."""
    
    @pytest.fixture
    def product(self):
        """Create a test product."""
        return Product.objects.create(
            code="TEST-001",
            name="Test Product",
            price=Decimal("10.50"),
            tax_rate=Decimal("21.00")
        )
    
    @pytest.fixture
    def warehouse(self):
        """Create a test warehouse."""
        return Warehouse.objects.create(
            name="Test Warehouse",
            is_active=True
        )
    
    def test_stocklot_creation_success(self, product, warehouse):
        """Test successful stock lot creation."""
        lot = StockLot.objects.create(
            product=product,
            lot_code="LOT-001",
            expiry_date=date.today() + timedelta(days=30),
            qty_on_hand=Decimal("100.00"),
            unit_cost=Decimal("8.00"),
            warehouse=warehouse
        )
        assert lot.id is not None
        assert lot.lot_code == "LOT-001"
        assert lot.qty_on_hand == Decimal("100.00")
        assert lot.is_quarantined is False
    
    def test_stocklot_qty_cannot_be_negative(self, product, warehouse):
        """Test that qty_on_hand cannot be negative."""
        with pytest.raises((ValidationError, IntegrityError)):
            lot = StockLot(
                product=product,
                lot_code="LOT-002",
                expiry_date=date.today() + timedelta(days=30),
                qty_on_hand=Decimal("-10.00"),
                unit_cost=Decimal("8.00"),
                warehouse=warehouse
            )
            lot.full_clean()
    
    def test_stocklot_unit_cost_cannot_be_negative(self, product, warehouse):
        """Test that unit_cost cannot be negative."""
        with pytest.raises((ValidationError, IntegrityError)):
            lot = StockLot(
                product=product,
                lot_code="LOT-003",
                expiry_date=date.today() + timedelta(days=30),
                qty_on_hand=Decimal("100.00"),
                unit_cost=Decimal("-5.00"),
                warehouse=warehouse
            )
            lot.full_clean()
    
    def test_stocklot_unique_constraint(self, product, warehouse):
        """Test unique constraint on (product, lot_code, warehouse)."""
        StockLot.objects.create(
            product=product,
            lot_code="UNIQUE-LOT",
            expiry_date=date.today() + timedelta(days=30),
            qty_on_hand=Decimal("100.00"),
            unit_cost=Decimal("8.00"),
            warehouse=warehouse
        )
        
        with pytest.raises(IntegrityError):
            StockLot.objects.create(
                product=product,
                lot_code="UNIQUE-LOT",
                expiry_date=date.today() + timedelta(days=60),
                qty_on_hand=Decimal("50.00"),
                unit_cost=Decimal("9.00"),
                warehouse=warehouse
            )
    
    def test_stocklot_index_product_expiry(self, product, warehouse):
        """Test that index on (product_id, expiry_date) works efficiently."""
        # Create multiple lots with different expiry dates
        for i in range(5):
            StockLot.objects.create(
                product=product,
                lot_code=f"LOT-{i:03d}",
                expiry_date=date.today() + timedelta(days=i*10),
                qty_on_hand=Decimal("100.00"),
                unit_cost=Decimal("8.00"),
                warehouse=warehouse
            )
        
        # Query should be efficient with index
        lots = StockLot.objects.filter(
            product=product,
            expiry_date__lte=date.today() + timedelta(days=25)
        ).order_by('expiry_date')
        
        assert lots.count() == 3


@pytest.mark.django_db
class TestMovement:
    """Tests for Movement model."""
    
    @pytest.fixture
    def product(self):
        """Create a test product."""
        return Product.objects.create(
            code="TEST-001",
            name="Test Product",
            price=Decimal("10.50"),
            tax_rate=Decimal("21.00")
        )
    
    @pytest.fixture
    def warehouse(self):
        """Create a test warehouse."""
        return Warehouse.objects.create(
            name="Test Warehouse",
            is_active=True
        )
    
    @pytest.fixture
    def stock_lot(self, product, warehouse):
        """Create a test stock lot."""
        return StockLot.objects.create(
            product=product,
            lot_code="LOT-001",
            expiry_date=date.today() + timedelta(days=30),
            qty_on_hand=Decimal("100.00"),
            unit_cost=Decimal("8.00"),
            warehouse=warehouse
        )
    
    @pytest.fixture
    def user(self):
        """Create a test user."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        return User.objects.create_user(
            username=f"testuser_{unique_id}",
            email=f"test_{unique_id}@example.com"
        )
    
    def test_movement_creation_success(self, product, user):
        """Test successful movement creation."""
        warehouse = Warehouse.objects.create(name="Test Warehouse Movement", is_active=True)
        stock_lot = StockLot.objects.create(
            product=product,
            lot_code="LOT-MOVEMENT-001",
            expiry_date=date.today() + timedelta(days=30),
            qty_on_hand=Decimal("100.00"),
            unit_cost=Decimal("8.00"),
            warehouse=warehouse
        )
        
        movement = Movement.objects.create(
            type="entry",
            product=product,
            lot=stock_lot,
            qty=Decimal("50.00"),
            unit_cost=Decimal("8.00"),
            reason="purchase",
            created_by=user
        )
        assert movement.id is not None
        assert movement.type == "entry"
        assert movement.qty == Decimal("50.00")
        assert movement.created_at is not None
    
    def test_movement_qty_cannot_be_zero(self, product, user):
        """Test that movement qty cannot be zero."""
        warehouse = Warehouse.objects.create(name="Test Warehouse Zero", is_active=True)
        stock_lot = StockLot.objects.create(
            product=product,
            lot_code="LOT-MOVEMENT-002",
            expiry_date=date.today() + timedelta(days=30),
            qty_on_hand=Decimal("100.00"),
            unit_cost=Decimal("8.00"),
            warehouse=warehouse
        )
        
        with pytest.raises((ValidationError, IntegrityError)):
            movement = Movement(
                type="entry",
                product=product,
                lot=stock_lot,
                qty=Decimal("0.00"),
                reason="purchase",
                created_by=user
            )
            movement.full_clean()
    
    def test_movement_qty_cannot_be_negative(self, product, user):
        """Test that movement qty cannot be negative."""
        warehouse = Warehouse.objects.create(name="Test Warehouse Negative", is_active=True)
        stock_lot = StockLot.objects.create(
            product=product,
            lot_code="LOT-MOVEMENT-003",
            expiry_date=date.today() + timedelta(days=30),
            qty_on_hand=Decimal("100.00"),
            unit_cost=Decimal("8.00"),
            warehouse=warehouse
        )
        
        with pytest.raises((ValidationError, IntegrityError)):
            movement = Movement(
                type="entry",
                product=product,
                lot=stock_lot,
                qty=Decimal("-10.00"),
                reason="purchase",
                created_by=user
            )
            movement.full_clean()
    
    def test_movement_type_choices(self, product, user):
        """Test that movement type must be valid choice."""
        # Create different lots for each movement to avoid unique constraint
        warehouse = Warehouse.objects.create(name="Test Warehouse Types", is_active=True)
        
        # Valid types should work
        for i, movement_type in enumerate(["entry", "exit"]):
            lot = StockLot.objects.create(
                product=product,
                lot_code=f"LOT-TYPE-{i:03d}",
                expiry_date=date.today() + timedelta(days=30),
                qty_on_hand=Decimal("100.00"),
                unit_cost=Decimal("8.00"),
                warehouse=warehouse
            )
            movement = Movement.objects.create(
                type=movement_type,
                product=product,
                lot=lot,
                qty=Decimal("10.00"),
                unit_cost=Decimal("8.00") if movement_type == "entry" else None,
                reason="purchase" if movement_type == "entry" else "sale",
                created_by=user
            )
            assert movement.type == movement_type
    
    def test_movement_unit_cost_optional(self, product, user):
        """Test that unit_cost is optional for exit movements."""
        warehouse = Warehouse.objects.create(name="Test Warehouse Optional", is_active=True)
        lot = StockLot.objects.create(
            product=product,
            lot_code="LOT-OPTIONAL",
            expiry_date=date.today() + timedelta(days=30),
            qty_on_hand=Decimal("100.00"),
            unit_cost=Decimal("8.00"),
            warehouse=warehouse
        )
        movement = Movement.objects.create(
            type="exit",
            product=product,
            lot=lot,
            qty=Decimal("10.00"),
            reason="sale",
            created_by=user
        )
        assert movement.unit_cost is None
    
    def test_movement_reason_required(self, product, user):
        """Test that reason has a default value."""
        warehouse = Warehouse.objects.create(name="Test Warehouse Default", is_active=True)
        lot = StockLot.objects.create(
            product=product,
            lot_code="LOT-DEFAULT",
            expiry_date=date.today() + timedelta(days=30),
            qty_on_hand=Decimal("100.00"),
            unit_cost=Decimal("8.00"),
            warehouse=warehouse
        )
        movement = Movement.objects.create(
            type="entry",
            product=product,
            lot=lot,
            qty=Decimal("10.00"),
            unit_cost=Decimal("8.00"),
            created_by=user
            # reason will use default value
        )
        assert movement.reason == "adjustment"  # Default value


@pytest.mark.django_db
class TestWarehouse:
    """Tests for Warehouse model."""
    
    def test_warehouse_creation_success(self):
        """Test successful warehouse creation."""
        warehouse = Warehouse.objects.create(
            name="Main Warehouse",
            is_active=True
        )
        assert warehouse.id is not None
        assert warehouse.name == "Main Warehouse"
        assert warehouse.is_active is True
    
    def test_warehouse_name_required(self):
        """Test that warehouse name is required."""
        with pytest.raises((ValidationError, IntegrityError)):
            warehouse = Warehouse(is_active=True)
            warehouse.full_clean()
    
    def test_warehouse_default_active_status(self):
        """Test that warehouse is active by default."""
        warehouse = Warehouse.objects.create(name="Test Warehouse")
        assert warehouse.is_active is True