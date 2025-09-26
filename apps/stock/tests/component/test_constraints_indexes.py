"""Component tests for stock constraints and indexes."""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.db import IntegrityError, connection
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.catalog.models import Product
from apps.stock.models import Warehouse, StockLot, Movement

User = get_user_model()


@pytest.mark.component
@pytest.mark.django_db
class TestStockLotConstraints:
    """Test StockLot constraints."""
    
    @pytest.fixture
    def product(self):
        """Create a test product."""
        return Product.objects.create(
            code="TEST-001",
            name="Test Product",
            price=Decimal("10.00"),
            tax_rate=Decimal("21.00")
        )
    
    @pytest.fixture
    def warehouse(self):
        """Create a test warehouse."""
        return Warehouse.objects.create(name="Test Warehouse")
    
    def test_unique_constraint_product_lot_warehouse(self, product, warehouse):
        """Test unique constraint (product, lot_code, warehouse)."""
        # Create first stock lot
        StockLot.objects.create(
            product=product,
            lot_code="LOT-001",
            expiry_date=date.today() + timedelta(days=30),
            unit_cost=Decimal("8.00"),
            warehouse=warehouse
        )
        
        # Try to create duplicate - should fail
        with pytest.raises(IntegrityError):
            StockLot.objects.create(
                product=product,
                lot_code="LOT-001",  # Same lot_code
                expiry_date=date.today() + timedelta(days=60),
                unit_cost=Decimal("9.00"),
                warehouse=warehouse  # Same warehouse
            )
    
    def test_qty_on_hand_non_negative_constraint(self, product, warehouse):
        """Test qty_on_hand cannot be negative."""
        with pytest.raises((ValidationError, IntegrityError)):
            stock_lot = StockLot(
                product=product,
                lot_code="LOT-002",
                expiry_date=date.today() + timedelta(days=30),
                qty_on_hand=Decimal("-1.000"),  # Negative quantity
                unit_cost=Decimal("8.00"),
                warehouse=warehouse
            )
            stock_lot.full_clean()
    
    def test_unit_cost_positive_constraint(self, product, warehouse):
        """Test unit_cost must be positive."""
        with pytest.raises((ValidationError, IntegrityError)):
            stock_lot = StockLot(
                product=product,
                lot_code="LOT-003",
                expiry_date=date.today() + timedelta(days=30),
                unit_cost=Decimal("0.00"),  # Zero cost should fail
                warehouse=warehouse
            )
            stock_lot.full_clean()


@pytest.mark.component
@pytest.mark.django_db
class TestStockLotIndexes:
    """Test StockLot indexes exist."""
    
    @pytest.fixture
    def product(self):
        """Create a test product."""
        return Product.objects.create(
            code="TEST-001",
            name="Test Product",
            price=Decimal("10.00"),
            tax_rate=Decimal("21.00")
        )
    
    @pytest.fixture
    def warehouse(self):
        """Create a test warehouse."""
        return Warehouse.objects.create(name="Test Warehouse")
    
    def test_product_expiry_date_index_exists(self):
        """Test that index (product_id, expiry_date) exists."""
        with connection.cursor() as cursor:
            # Get all indexes for stock_stocklot table
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND tbl_name='stock_stocklot'
                AND name LIKE '%fefo%'
            """)
            indexes = [row[0] for row in cursor.fetchall()]
            
            # Check that FEFO index exists
            assert any('idx_lot_fefo' in idx for idx in indexes), f"FEFO index not found. Available indexes: {indexes}"
    
    def test_fefo_pick_index_exists(self):
        """Test that FEFO pick optimization index exists."""
        with connection.cursor() as cursor:
            # Get all indexes for stock_stocklot table
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND tbl_name='stock_stocklot'
                AND name LIKE '%fefo_pick%'
            """)
            indexes = [row[0] for row in cursor.fetchall()]
            
            # Check that FEFO pick index exists
            assert any('idx_lot_fefo_pick' in idx for idx in indexes), f"FEFO pick index not found. Available indexes: {indexes}"
    
    @pytest.mark.slow
    def test_fefo_query_performance_with_index(self, product, warehouse):
        """Optional: Test that FEFO query uses index efficiently."""
        # Create multiple stock lots for performance testing
        for i in range(10):
            StockLot.objects.create(
                product=product,
                lot_code=f"LOT-{i:03d}",
                expiry_date=date.today() + timedelta(days=i*10),
                qty_on_hand=Decimal("100.000"),
                unit_cost=Decimal("8.00"),
                warehouse=warehouse
            )
        
        # Test FEFO query (this would be used by the FEFO service)
        with connection.cursor() as cursor:
            cursor.execute("""
                EXPLAIN QUERY PLAN
                SELECT * FROM stock_stocklot 
                WHERE product_id = %s 
                AND warehouse_id = %s 
                AND is_quarantined = 0 
                AND is_reserved = 0
                ORDER BY expiry_date ASC
            """, [product.id, warehouse.id])
            
            query_plan = cursor.fetchall()
            # Check that the query uses an index (not a full table scan)
            plan_text = ' '.join([str(row) for row in query_plan])
            assert 'USING INDEX' in plan_text.upper(), f"Query should use index. Plan: {query_plan}"


@pytest.mark.component
@pytest.mark.django_db
class TestMovementConstraints:
    """Test Movement constraints."""
    
    @pytest.fixture
    def user(self):
        """Create a test user."""
        return User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
    
    @pytest.fixture
    def product(self):
        """Create a test product."""
        return Product.objects.create(
            code="TEST-001",
            name="Test Product",
            price=Decimal("10.00"),
            tax_rate=Decimal("21.00")
        )
    
    @pytest.fixture
    def warehouse(self):
        """Create a test warehouse."""
        return Warehouse.objects.create(name="Test Warehouse")
    
    @pytest.fixture
    def stock_lot(self, product, warehouse):
        """Create a test stock lot."""
        return StockLot.objects.create(
            product=product,
            lot_code="LOT-001",
            expiry_date=date.today() + timedelta(days=30),
            unit_cost=Decimal("8.00"),
            warehouse=warehouse
        )
    
    def test_movement_qty_positive_constraint(self, user, product, stock_lot):
        """Test movement qty must be positive."""
        with pytest.raises((ValidationError, IntegrityError)):
            movement = Movement(
                type=Movement.Type.ENTRY,
                product=product,
                lot=stock_lot,
                qty=Decimal("0.000"),  # Zero quantity should fail
                unit_cost=Decimal("8.00"),
                created_by=user
            )
            movement.full_clean()
    
    def test_entry_requires_lot_and_cost_constraint(self, user, product):
        """Test ENTRY movements require lot and unit_cost."""
        with pytest.raises((ValidationError, IntegrityError)):
            movement = Movement(
                type=Movement.Type.ENTRY,
                product=product,
                lot=None,  # Missing lot for ENTRY
                qty=Decimal("10.000"),
                unit_cost=Decimal("8.00"),
                created_by=user
            )
            movement.full_clean()
    
    def test_exit_requires_lot_constraint(self, user, product):
        """Test EXIT movements require lot."""
        with pytest.raises((ValidationError, IntegrityError)):
            movement = Movement(
                type=Movement.Type.EXIT,
                product=product,
                lot=None,  # Missing lot for EXIT
                qty=Decimal("5.000"),
                created_by=user
            )
            movement.full_clean()
    
    def test_movement_product_lot_consistency(self, user, product, stock_lot):
        """Test that movement.product must match movement.lot.product."""
        # Create another product
        other_product = Product.objects.create(
            code="OTHER-001",
            name="Other Product",
            price=Decimal("15.00"),
            tax_rate=Decimal("21.00")
        )
        
        with pytest.raises(ValidationError):
            movement = Movement(
                type=Movement.Type.ENTRY,
                product=other_product,  # Different product
                lot=stock_lot,  # Lot belongs to 'product', not 'other_product'
                qty=Decimal("10.000"),
                unit_cost=Decimal("8.00"),
                created_by=user
            )
            movement.full_clean()