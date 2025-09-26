"""Tests for orders models."""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from apps.orders.models import Order, OrderItem
from apps.customers.models import Customer
from apps.catalog.models import Product, Benefit


@pytest.mark.django_db
class TestOrder:
    """Tests for Order model."""
    
    @pytest.fixture
    def customer(self):
        """Create a test customer."""
        return Customer.objects.create(
            name="Test Customer",
            segment="retail"
        )
    
    def test_order_creation_success(self, customer):
        """Test successful order creation."""
        order = Order.objects.create(
            customer=customer,
            status="draft",
            total=Decimal("100.00")
        )
        assert order.id is not None
        assert order.customer == customer
        assert order.status == "draft"
        assert order.total == Decimal("100.00")
    
    def test_order_customer_required(self):
        """Test that customer is required."""
        with pytest.raises((ValidationError, IntegrityError)):
            order = Order(
                status="draft",
                total=Decimal("100.00")
            )
            order.full_clean()
    
    def test_order_status_choices(self, customer):
        """Test that order status must be valid choice."""
        # Valid statuses should work
        for status in ["draft", "placed"]:
            order = Order.objects.create(
                customer=customer,
                status=status,
                total=Decimal("100.00")
            )
            assert order.status == status
    
    def test_order_status_invalid_choice(self, customer):
        """Test that invalid status choice raises error."""
        with pytest.raises((ValidationError, IntegrityError)):
            order = Order(
                customer=customer,
                status="invalid_status",
                total=Decimal("100.00")
            )
            order.full_clean()
    
    def test_order_total_cannot_be_negative(self, customer):
        """Test that order total cannot be negative."""
        with pytest.raises((ValidationError, IntegrityError)):
            order = Order(
                customer=customer,
                status="draft",
                total=Decimal("-50.00")
            )
            order.full_clean()
    
    def test_order_total_can_be_zero(self, customer):
        """Test that order total can be zero (free orders)."""
        order = Order.objects.create(
            customer=customer,
            status="draft",
            total=Decimal("0.00")
        )
        assert order.total == Decimal("0.00")
    
    def test_order_str_representation(self, customer):
        """Test string representation of order."""
        order = Order.objects.create(
            customer=customer,
            status="draft",
            total=Decimal("100.00")
        )
        expected = f"Order #{order.id} · {customer.name}"
        assert str(order) == expected
    
    def test_order_currency_default(self, customer):
        """Test that currency defaults to ARS."""
        order = Order.objects.create(
            customer=customer,
            status="draft",
            total=Decimal("100.00")
        )
        assert order.currency == "ARS"
    
    def test_order_subtotal_calculation(self, customer):
        """Test subtotal calculation fields."""
        order = Order.objects.create(
            customer=customer,
            status="draft",
            subtotal=Decimal("85.00"),
            discount_total=Decimal("5.00"),
            tax_total=Decimal("20.00"),
            total=Decimal("100.00")
        )
        assert order.subtotal == Decimal("85.00")
        assert order.discount_total == Decimal("5.00")
        assert order.tax_total == Decimal("20.00")


@pytest.mark.django_db
class TestOrderItem:
    """Tests for OrderItem model."""
    
    @pytest.fixture
    def customer(self):
        """Create a test customer."""
        return Customer.objects.create(
            name="Test Customer",
            segment="retail"
        )
    
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
    def order(self, customer):
        """Create a test order."""
        return Order.objects.create(
            customer=customer,
            status="draft",
            total=Decimal("100.00")
        )
    
    @pytest.fixture
    def benefit(self):
        """Create a test benefit."""
        return Benefit.objects.create(
            name="Test Discount",
            type="discount",
            segment="retail",
            value=Decimal("10.00")
        )
    
    def test_orderitem_creation_success(self, order, product):
        """Test successful order item creation."""
        item = OrderItem.objects.create(
            order=order,
            product=product,
            qty=Decimal("2.00"),
            unit_price=Decimal("10.50")
        )
        assert item.id is not None
        assert item.order == order
        assert item.product == product
        assert item.qty == Decimal("2.00")
        assert item.unit_price == Decimal("10.50")
    
    def test_orderitem_order_required(self, product):
        """Test that order is required."""
        with pytest.raises((ValidationError, IntegrityError)):
            item = OrderItem(
                product=product,
                qty=Decimal("2.00"),
                unit_price=Decimal("10.50")
            )
            item.full_clean()
    
    def test_orderitem_product_required(self, order):
        """Test that product is required."""
        with pytest.raises((ValidationError, IntegrityError)):
            item = OrderItem(
                order=order,
                qty=Decimal("2.00"),
                unit_price=Decimal("10.50")
            )
            item.full_clean()
    
    def test_orderitem_qty_cannot_be_zero(self, order, product):
        """Test that quantity cannot be zero."""
        with pytest.raises((ValidationError, IntegrityError)):
            item = OrderItem(
                order=order,
                product=product,
                qty=Decimal("0.00"),
                unit_price=Decimal("10.50")
            )
            item.full_clean()
    
    def test_orderitem_qty_cannot_be_negative(self, order, product):
        """Test that quantity cannot be negative."""
        with pytest.raises((ValidationError, IntegrityError)):
            item = OrderItem(
                order=order,
                product=product,
                qty=Decimal("-1.00"),
                unit_price=Decimal("10.50")
            )
            item.full_clean()
    
    def test_orderitem_unit_price_cannot_be_negative(self, order, product):
        """Test that unit price cannot be negative."""
        with pytest.raises((ValidationError, IntegrityError)):
            item = OrderItem(
                order=order,
                product=product,
                qty=Decimal("2.00"),
                unit_price=Decimal("-5.00")
            )
            item.full_clean()
    
    def test_orderitem_unit_price_can_be_zero(self, order, product):
        """Test that unit price can be zero (free items)."""
        item = OrderItem.objects.create(
            order=order,
            product=product,
            qty=Decimal("1.00"),
            unit_price=Decimal("0.00")
        )
        assert item.unit_price == Decimal("0.00")
    
    def test_orderitem_benefit_optional(self, order, product, benefit):
        """Test that benefit is optional."""
        # Without benefit
        item1 = OrderItem.objects.create(
            order=order,
            product=product,
            qty=Decimal("1.00"),
            unit_price=Decimal("10.50")
        )
        assert item1.benefit_applied is None
        
        # With benefit
        item2 = OrderItem.objects.create(
            order=order,
            product=product,
            qty=Decimal("1.00"),
            unit_price=Decimal("9.45"),
            benefit_applied=benefit
        )
        assert item2.benefit_applied == benefit
    
    def test_orderitem_str_representation(self, order, product):
        """Test string representation of order item."""
        item = OrderItem.objects.create(
            order=order,
            product=product,
            qty=Decimal("2.00"),
            unit_price=Decimal("10.50")
        )
        expected = f"{product.code} × {item.qty}"
        assert str(item) == expected
    
    def test_orderitem_benefit_optional(self, order, product):
        """Test that benefit is optional and stored as JSON."""
        # Without benefit
        item1 = OrderItem.objects.create(
            order=order,
            product=product,
            qty=Decimal("1.00"),
            unit_price=Decimal("10.50")
        )
        assert item1.benefit_applied is None
        
        # With benefit (JSON format)
        benefit_data = {"type": "discount", "value": "10.00", "name": "Test Discount"}
        # Create second product to avoid unique constraint
        product2 = Product.objects.create(
            code="TEST-002",
            name="Test Product 2",
            price=Decimal("9.45"),
            tax_rate=Decimal("21.00")
        )
        item2 = OrderItem.objects.create(
            order=order,
            product=product2,
            qty=Decimal("1.00"),
            unit_price=Decimal("9.45"),
            benefit_applied=benefit_data
        )
        assert item2.benefit_applied == benefit_data