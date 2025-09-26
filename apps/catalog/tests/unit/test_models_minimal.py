"""Minimal unit tests for catalog models - creación básica + defaults + __str__."""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from apps.catalog.models import Product, Benefit


@pytest.mark.unit
@pytest.mark.django_db
class TestProductMinimal:
    """Minimal tests for Product model."""
    
    def test_product_creation_basic(self):
        """Test basic product creation with minimal fields."""
        product = Product.objects.create(
            code="TEST-001",
            name="Test Product",
            price=Decimal("10.50"),
            tax_rate=Decimal("21.00")
        )
        assert product.id is not None
        assert product.code == "TEST-001"
        assert product.name == "Test Product"
        assert product.price == Decimal("10.50")
        assert product.tax_rate == Decimal("21.00")
    
    def test_product_defaults(self):
        """Test product default values."""
        product = Product.objects.create(
            code="TEST-002",
            name="Test Product 2",
            price=Decimal("15.00")
        )
        # Test default values
        assert product.unit == Product.Unit.UNIT
        assert product.tax_rate == Decimal("21")
        assert product.is_active is True
        assert product.segment is None  # segment is nullable
    
    def test_product_str_representation(self):
        """Test product string representation."""
        product = Product.objects.create(
            code="TEST-003",
            name="Test Product 3",
            price=Decimal("20.00"),
            tax_rate=Decimal("21.00")
        )
        expected_str = f"{product.code} · {product.name}"  # Using the correct separator
        assert str(product) == expected_str


@pytest.mark.unit
@pytest.mark.django_db
class TestBenefitMinimal:
    """Minimal tests for Benefit model."""
    
    def test_benefit_creation_basic(self):
        """Test basic benefit creation with minimal fields."""
        benefit = Benefit.objects.create(
            name="Test Discount",
            type="discount",
            segment="retail",
            value=Decimal("10.00"),
            active_from=date.today(),
            active_to=date.today() + timedelta(days=30)
        )
        assert benefit.id is not None
        assert benefit.name == "Test Discount"
        assert benefit.type == "discount"
        assert benefit.segment == "retail"
        assert benefit.value == Decimal("10.00")
    
    def test_benefit_defaults(self):
        """Test benefit default values."""
        benefit = Benefit.objects.create(
            name="Test Benefit",
            type="discount",
            segment="retail",
            value=Decimal("5.00"),
            active_from=date.today(),
            active_to=date.today() + timedelta(days=30)
        )
        # Test that required fields are set (no specific defaults to test)
        assert benefit.active_from is not None
        assert benefit.active_to is not None
    
    def test_benefit_str_representation(self):
        """Test benefit string representation."""
        benefit = Benefit.objects.create(
            name="Test Benefit Str",
            type="discount",
            segment="retail",
            value=Decimal("15.00"),
            active_from=date.today(),
            active_to=date.today() + timedelta(days=30)
        )
        expected_str = f"{benefit.name} ({benefit.type})"
        assert str(benefit) == expected_str