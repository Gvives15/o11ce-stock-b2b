"""Tests for catalog models."""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from apps.catalog.models import Product, Benefit


@pytest.mark.django_db
class TestProduct:
    """Tests for Product model."""
    
    def test_product_creation_success(self):
        """Test successful product creation."""
        product = Product.objects.create(
            code="TEST-001",
            name="Test Product",
            price=Decimal("10.50"),
            tax_rate=Decimal("21.00")
        )
        assert product.id is not None
        assert product.code == "TEST-001"
        assert product.price == Decimal("10.50")
        assert product.is_active is True
    
    def test_product_price_must_be_positive(self):
        """Test that product price must be greater than 0."""
        with pytest.raises((ValidationError, IntegrityError)):
            product = Product(
                code="TEST-002",
                name="Test Product",
                price=Decimal("0.00"),
                tax_rate=Decimal("21.00")
            )
            product.full_clean()
    
    def test_product_price_cannot_be_negative(self):
        """Test that product price cannot be negative."""
        with pytest.raises((ValidationError, IntegrityError)):
            product = Product(
                code="TEST-003",
                name="Test Product",
                price=Decimal("-5.00"),
                tax_rate=Decimal("21.00")
            )
            product.full_clean()
    
    def test_product_tax_rate_cannot_be_negative(self):
        """Test that tax rate cannot be negative."""
        with pytest.raises((ValidationError, IntegrityError)):
            product = Product(
                code="TEST-004",
                name="Test Product",
                price=Decimal("10.00"),
                tax_rate=Decimal("-5.00")
            )
            product.full_clean()
    
    def test_product_tax_rate_cannot_exceed_100(self):
        """Test that tax rate cannot exceed 100%."""
        with pytest.raises((ValidationError, IntegrityError)):
            product = Product(
                code="TEST-005",
                name="Test Product",
                price=Decimal("10.00"),
                tax_rate=Decimal("150.00")
            )
            product.full_clean()
    
    def test_product_code_unique(self):
        """Test that product code must be unique."""
        Product.objects.create(
            code="UNIQUE-001",
            name="First Product",
            price=Decimal("10.00"),
            tax_rate=Decimal("21.00")
        )
        
        with pytest.raises(IntegrityError):
            Product.objects.create(
                code="UNIQUE-001",
                name="Second Product",
                price=Decimal("15.00"),
                tax_rate=Decimal("21.00")
            )


@pytest.mark.django_db
class TestBenefit:
    """Tests for Benefit model."""
    
    def test_benefit_creation_success(self):
        """Test successful benefit creation."""
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
        assert benefit.value == Decimal("10.00")
    
    def test_discount_benefit_requires_value(self):
        """Test that discount benefit must have a value."""
        with pytest.raises((ValidationError, IntegrityError)):
            benefit = Benefit(
                name="Invalid Discount",
                type="discount",
                segment="retail",
                value=None,
                active_from=date.today(),
                active_to=date.today() + timedelta(days=30)
            )
            benefit.full_clean()
    
    def test_discount_value_cannot_exceed_100(self):
        """Test that discount value cannot exceed 100%."""
        with pytest.raises((ValidationError, IntegrityError)):
            benefit = Benefit(
                name="Invalid Discount",
                type="discount",
                segment="retail",
                value=Decimal("150.00"),
                active_from=date.today(),
                active_to=date.today() + timedelta(days=30)
            )
            benefit.full_clean()
    
    def test_combo_benefit_requires_combo_spec(self):
        """Test that combo benefit must have combo_spec."""
        with pytest.raises((ValidationError, IntegrityError)):
            benefit = Benefit(
                name="Invalid Combo",
                type="combo",
                segment="retail",
                combo_spec=None,
                active_from=date.today(),
                active_to=date.today() + timedelta(days=30)
            )
            benefit.full_clean()
    
    def test_active_to_must_be_after_active_from(self):
        """Test that active_to must be after active_from."""
        with pytest.raises((ValidationError, IntegrityError)):
            benefit = Benefit(
                name="Invalid Dates",
                type="discount",
                segment="retail",
                value=Decimal("10.00"),
                active_from=date.today(),
                active_to=date.today() - timedelta(days=1)
            )
            benefit.full_clean()
    
    def test_combo_benefit_with_valid_spec(self):
        """Test successful combo benefit creation."""
        benefit = Benefit.objects.create(
            name="3x2 Combo",
            type="combo",
            segment="retail",
            combo_spec={
                "buy": 3,
                "pay": 2,
                "category": "Bebidas"
            },
            active_from=date.today(),
            active_to=date.today() + timedelta(days=30)
        )
        assert benefit.id is not None
        assert benefit.type == "combo"
        assert benefit.combo_spec["buy"] == 3
        assert benefit.combo_spec["pay"] == 2