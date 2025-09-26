"""Minimal unit tests for customers models - creación básica + defaults + __str__."""

import pytest
from apps.customers.models import Customer


@pytest.mark.unit
@pytest.mark.django_db
class TestCustomerMinimal:
    """Minimal tests for Customer model."""
    
    def test_customer_creation_basic(self):
        """Test basic customer creation with minimal fields."""
        customer = Customer.objects.create(
            name="Test Customer",
            segment=Customer.Segment.RETAIL
        )
        assert customer.id is not None
        assert customer.name == "Test Customer"
        assert customer.segment == Customer.Segment.RETAIL
    
    def test_customer_defaults(self):
        """Test customer default values."""
        customer = Customer.objects.create(
            name="Test Customer 2",
            segment=Customer.Segment.WHOLESALE
        )
        # Test default values
        assert customer.min_shelf_life_days == 0
        assert customer.email == ""
        assert customer.phone == ""
        assert customer.tax_id == ""
        assert customer.tax_condition == ""
    
    def test_customer_str_representation(self):
        """Test customer string representation."""
        customer = Customer.objects.create(
            name="Test Customer 3",
            segment=Customer.Segment.RETAIL
        )
        assert str(customer) == "Test Customer 3"