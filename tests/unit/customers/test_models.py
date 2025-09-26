"""Tests for customers models."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from apps.customers.models import Customer


@pytest.mark.django_db
class TestCustomer:
    """Tests for Customer model."""
    
    def test_customer_creation_success(self):
        """Test successful customer creation."""
        customer = Customer.objects.create(
            name="Test Customer",
            segment="retail"
        )
        assert customer.id is not None
        assert customer.name == "Test Customer"
        assert customer.segment == "retail"
    
    def test_customer_name_required(self):
        """Test that customer name is required."""
        with pytest.raises((ValidationError, IntegrityError)):
            customer = Customer(segment="retail")
            customer.full_clean()
    
    def test_customer_segment_choices(self):
        """Test that customer segment must be valid choice."""
        # Valid segments should work
        for segment in ["wholesale", "retail"]:
            customer = Customer.objects.create(
                name=f"Customer {segment}",
                segment=segment
            )
            assert customer.segment == segment
    
    def test_customer_segment_invalid_choice(self):
        """Test that invalid segment choice raises error."""
        with pytest.raises((ValidationError, IntegrityError)):
            customer = Customer(
                name="Test Customer",
                segment="invalid_segment"
            )
            customer.full_clean()
    
    def test_customer_email_optional(self):
        """Test that email is optional."""
        customer = Customer.objects.create(
            name="Customer Without Email",
            segment="retail"
        )
        assert customer.email is None or customer.email == ""
    
    def test_customer_email_valid_format(self):
        """Test that email must be valid format when provided."""
        # Valid email should work
        customer = Customer.objects.create(
            name="Customer With Email",
            segment="retail",
            email="test@example.com"
        )
        assert customer.email == "test@example.com"
    
    def test_customer_phone_optional(self):
        """Test that phone is optional."""
        customer = Customer.objects.create(
            name="Customer Without Phone",
            segment="retail"
        )
        assert customer.phone is None or customer.phone == ""
    
    def test_customer_tax_id_optional(self):
        """Test that tax_id is optional."""
        customer = Customer.objects.create(
            name="Customer Without Tax ID",
            segment="retail"
        )
        assert customer.tax_id is None or customer.tax_id == ""
    
    def test_customer_tax_condition_choices(self):
        """Test that tax_condition must be valid choice when provided."""
        # Valid tax conditions should work
        for tax_condition in ["responsable_inscripto", "monotributo", "exento"]:
            customer = Customer.objects.create(
                name=f"Customer {tax_condition}",
                segment="retail",
                tax_condition=tax_condition
            )
            assert customer.tax_condition == tax_condition
    
    def test_customer_str_representation(self):
        """Test string representation of customer."""
        customer = Customer.objects.create(
            name="Test Customer",
            segment="retail"
        )
        assert str(customer) == "Test Customer"
    
    def test_customer_wholesale_segment(self):
        """Test wholesale customer creation."""
        customer = Customer.objects.create(
            name="Wholesale Customer",
            segment="wholesale",
            tax_id="20-12345678-9",
            tax_condition="responsable_inscripto"
        )
        assert customer.segment == "wholesale"
        assert customer.tax_id == "20-12345678-9"
        assert customer.tax_condition == "responsable_inscripto"
    
    def test_customer_retail_segment(self):
        """Test retail customer creation."""
        customer = Customer.objects.create(
            name="Retail Customer",
            segment="retail",
            email="retail@example.com",
            phone="+54 11 1234-5678"
        )
        assert customer.segment == "retail"
        assert customer.email == "retail@example.com"
        assert customer.phone == "+54 11 1234-5678"