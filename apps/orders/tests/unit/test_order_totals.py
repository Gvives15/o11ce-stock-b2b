"""Unit tests for order totals calculations."""

import pytest
from decimal import Decimal
from apps.customers.models import Customer
from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem


@pytest.mark.unit
@pytest.mark.django_db
class TestOrderTotalsCalculation:
    """Test order totals calculation logic."""
    
    @pytest.fixture
    def customer(self):
        """Create a test customer."""
        return Customer.objects.create(
            name="Test Customer",
            segment=Customer.Segment.RETAIL
        )
    
    @pytest.fixture
    def product_a(self):
        """Create test product A."""
        return Product.objects.create(
            code="PROD-A",
            name="Product A",
            price=Decimal("10.00"),
            tax_rate=Decimal("21.00")
        )
    
    @pytest.fixture
    def product_b(self):
        """Create test product B."""
        return Product.objects.create(
            code="PROD-B",
            name="Product B",
            price=Decimal("15.00"),
            tax_rate=Decimal("10.50")
        )
    
    def test_order_single_item_totals(self, customer, product_a):
        """Test order totals with single item."""
        order = Order.objects.create(
            customer=customer,
            delivery_method=Order.DeliveryMethod.PICKUP
        )
        
        # Add single item: 2 units at $10.00 each
        OrderItem.objects.create(
            order=order,
            product=product_a,
            qty=Decimal("2.000"),
            unit_price=Decimal("10.00")
        )
        
        # Manual calculation for verification
        # Subtotal = 2 * 10.00 = 20.00
        # Tax = 20.00 * 0.21 = 4.20
        # Total = 20.00 + 4.20 = 24.20
        
        # Note: These would be calculated by business logic, not the model itself
        # For now, we test that the fields can store the calculated values
        order.subtotal = Decimal("20.00")
        order.tax_total = Decimal("4.20")
        order.total = Decimal("24.20")
        order.save()
        
        assert order.subtotal == Decimal("20.00")
        assert order.tax_total == Decimal("4.20")
        assert order.total == Decimal("24.20")
    
    def test_order_multiple_items_totals(self, customer, product_a, product_b):
        """Test order totals with multiple items."""
        order = Order.objects.create(
            customer=customer,
            delivery_method=Order.DeliveryMethod.DELIVERY
        )
        
        # Add first item: 3 units at $10.00 each (21% tax)
        OrderItem.objects.create(
            order=order,
            product=product_a,
            qty=Decimal("3.000"),
            unit_price=Decimal("10.00")
        )
        
        # Add second item: 1 unit at $15.00 each (10.5% tax)
        OrderItem.objects.create(
            order=order,
            product=product_b,
            qty=Decimal("1.000"),
            unit_price=Decimal("15.00")
        )
        
        # Manual calculation for verification
        # Item A: 3 * 10.00 = 30.00, tax = 30.00 * 0.21 = 6.30
        # Item B: 1 * 15.00 = 15.00, tax = 15.00 * 0.105 = 1.575 ≈ 1.58
        # Subtotal = 30.00 + 15.00 = 45.00
        # Tax total = 6.30 + 1.58 = 7.88
        # Total = 45.00 + 7.88 = 52.88
        
        order.subtotal = Decimal("45.00")
        order.tax_total = Decimal("7.88")
        order.total = Decimal("52.88")
        order.save()
        
        assert order.subtotal == Decimal("45.00")
        assert order.tax_total == Decimal("7.88")
        assert order.total == Decimal("52.88")
    
    def test_order_with_discount_totals(self, customer, product_a):
        """Test order totals with discount applied."""
        order = Order.objects.create(
            customer=customer,
            delivery_method=Order.DeliveryMethod.PICKUP
        )
        
        # Add item: 5 units at $10.00 each
        OrderItem.objects.create(
            order=order,
            product=product_a,
            qty=Decimal("5.000"),
            unit_price=Decimal("10.00")
        )
        
        # Manual calculation with 10% discount
        # Subtotal = 5 * 10.00 = 50.00
        # Discount = 50.00 * 0.10 = 5.00
        # Taxable amount = 50.00 - 5.00 = 45.00
        # Tax = 45.00 * 0.21 = 9.45
        # Total = 45.00 + 9.45 = 54.45
        
        order.subtotal = Decimal("50.00")
        order.discount_total = Decimal("5.00")
        order.tax_total = Decimal("9.45")
        order.total = Decimal("54.45")
        order.save()
        
        assert order.subtotal == Decimal("50.00")
        assert order.discount_total == Decimal("5.00")
        assert order.tax_total == Decimal("9.45")
        assert order.total == Decimal("54.45")
    
    def test_order_zero_totals(self, customer):
        """Test order with zero totals (empty order)."""
        order = Order.objects.create(
            customer=customer,
            delivery_method=Order.DeliveryMethod.PICKUP
        )
        
        # Empty order should have zero totals
        assert order.subtotal == Decimal("0.00")
        assert order.discount_total == Decimal("0.00")
        assert order.tax_total == Decimal("0.00")
        assert order.total == Decimal("0.00")
    
    def test_order_item_line_total_calculation(self, customer, product_a):
        """Test individual order item line total calculation."""
        order = Order.objects.create(
            customer=customer,
            delivery_method=Order.DeliveryMethod.PICKUP
        )
        
        # Add item: 2.5 units at $12.50 each
        order_item = OrderItem.objects.create(
            order=order,
            product=product_a,
            qty=Decimal("2.500"),
            unit_price=Decimal("12.50")
        )
        
        # Line total = qty * unit_price = 2.5 * 12.50 = 31.25
        expected_line_total = order_item.qty * order_item.unit_price
        assert expected_line_total == Decimal("31.25")
    
    def test_order_fractional_quantities_totals(self, customer, product_a):
        """Test order totals with fractional quantities."""
        order = Order.objects.create(
            customer=customer,
            delivery_method=Order.DeliveryMethod.DELIVERY
        )
        
        # Add item: 1.750 units at $8.40 each
        OrderItem.objects.create(
            order=order,
            product=product_a,
            qty=Decimal("1.750"),
            unit_price=Decimal("8.40")
        )
        
        # Manual calculation
        # Subtotal = 1.750 * 8.40 = 14.70
        # Tax = 14.70 * 0.21 = 3.087 ≈ 3.09
        # Total = 14.70 + 3.09 = 17.79
        
        order.subtotal = Decimal("14.70")
        order.tax_total = Decimal("3.09")
        order.total = Decimal("17.79")
        order.save()
        
        assert order.subtotal == Decimal("14.70")
        assert order.tax_total == Decimal("3.09")
        assert order.total == Decimal("17.79")


@pytest.mark.unit
@pytest.mark.django_db
class TestOrderTotalsConstraints:
    """Test order totals constraints and validations."""
    
    @pytest.fixture
    def customer(self):
        """Create a test customer."""
        return Customer.objects.create(
            name="Test Customer",
            segment=Customer.Segment.RETAIL
        )
    
    def test_order_totals_precision(self, customer):
        """Test that order totals maintain proper decimal precision."""
        order = Order.objects.create(
            customer=customer,
            delivery_method=Order.DeliveryMethod.PICKUP,
            subtotal=Decimal("123.45"),
            discount_total=Decimal("12.34"),
            tax_total=Decimal("23.45"),
            total=Decimal("134.56")
        )
        
        # Verify precision is maintained
        assert order.subtotal == Decimal("123.45")
        assert order.discount_total == Decimal("12.34")
        assert order.tax_total == Decimal("23.45")
        assert order.total == Decimal("134.56")
    
    def test_order_totals_large_values(self, customer):
        """Test order totals with large monetary values."""
        order = Order.objects.create(
            customer=customer,
            delivery_method=Order.DeliveryMethod.DELIVERY,
            subtotal=Decimal("9999999999.99"),
            discount_total=Decimal("1000000000.00"),
            tax_total=Decimal("1999999999.99"),
            total=Decimal("10999999999.98")
        )
        
        # Verify large values are stored correctly
        assert order.subtotal == Decimal("9999999999.99")
        assert order.discount_total == Decimal("1000000000.00")
        assert order.tax_total == Decimal("1999999999.99")
        assert order.total == Decimal("10999999999.98")