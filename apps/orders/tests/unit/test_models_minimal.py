"""Minimal unit tests for orders models - creación básica + defaults + __str__."""

import pytest
from decimal import Decimal
from apps.customers.models import Customer
from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem


@pytest.mark.unit
@pytest.mark.django_db
class TestOrderMinimal:
    """Minimal tests for Order model."""
    
    @pytest.fixture
    def customer(self):
        """Create a test customer."""
        return Customer.objects.create(
            name="Test Customer",
            segment=Customer.Segment.RETAIL
        )
    
    def test_order_creation_basic(self, customer):
        """Test basic order creation with minimal fields."""
        order = Order.objects.create(
            customer=customer,
            delivery_method=Order.DeliveryMethod.PICKUP
        )
        assert order.id is not None
        assert order.customer == customer
        assert order.delivery_method == Order.DeliveryMethod.PICKUP
    
    def test_order_defaults(self, customer):
        """Test order default values."""
        order = Order.objects.create(
            customer=customer,
            delivery_method=Order.DeliveryMethod.DELIVERY
        )
        # Test default values
        assert order.status == Order.Status.DRAFT
        assert order.currency == "ARS"
        assert order.subtotal == Decimal("0")
        assert order.discount_total == Decimal("0")
        assert order.tax_total == Decimal("0")
        assert order.total == Decimal("0")
    
    def test_order_str_representation(self, customer):
        """Test order string representation."""
        order = Order.objects.create(
            customer=customer,
            delivery_method=Order.DeliveryMethod.PICKUP
        )
        expected_str = f"Order #{order.id} · {customer.name}"
        assert str(order) == expected_str


@pytest.mark.unit
@pytest.mark.django_db
class TestOrderItemMinimal:
    """Minimal tests for OrderItem model."""
    
    @pytest.fixture
    def customer(self):
        """Create a test customer."""
        return Customer.objects.create(
            name="Test Customer",
            segment=Customer.Segment.RETAIL
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
    def order(self, customer):
        """Create a test order."""
        return Order.objects.create(
            customer=customer,
            delivery_method=Order.DeliveryMethod.PICKUP
        )
    
    def test_order_item_creation_basic(self, order, product):
        """Test basic order item creation with minimal fields."""
        order_item = OrderItem.objects.create(
            order=order,
            product=product,
            qty=Decimal("2.000"),
            unit_price=Decimal("10.00")
        )
        assert order_item.id is not None
        assert order_item.order == order
        assert order_item.product == product
        assert order_item.qty == Decimal("2.000")
        assert order_item.unit_price == Decimal("10.00")
    
    def test_order_item_defaults(self, order, product):
        """Test order item default values."""
        order_item = OrderItem.objects.create(
            order=order,
            product=product,
            qty=Decimal("1.000"),
            unit_price=Decimal("15.00")
        )
        # Test default values (benefit_applied is nullable)
        assert order_item.benefit_applied is None
    
    def test_order_item_str_representation(self, order, product):
        """Test order item string representation."""
        order_item = OrderItem.objects.create(
            order=order,
            product=product,
            qty=Decimal("3.000"),
            unit_price=Decimal("12.00")
        )
        expected_str = f"{product.code} × {order_item.qty}"
        assert str(order_item) == expected_str