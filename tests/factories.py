"""
Factory Boy factories for generating test data.
Provides realistic, consistent test data for all models.
"""
import factory
from factory import fuzzy
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth.models import User

from apps.catalog.models import Product, Category, Benefit
from apps.stock.models import StockLot, Warehouse, StockMovement
from apps.orders.models import Order, OrderItem
from apps.customers.models import Customer


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for Django User model."""
    
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True
    is_staff = False


class CategoryFactory(factory.django.DjangoModelFactory):
    """Factory for Category model."""
    
    class Meta:
        model = Category
    
    name = factory.Faker('word')
    description = factory.Faker('text', max_nb_chars=200)
    is_active = True


class ProductFactory(factory.django.DjangoModelFactory):
    """Factory for Product model with realistic data."""
    
    class Meta:
        model = Product
    
    name = factory.Faker('catch_phrase')
    description = factory.Faker('text', max_nb_chars=500)
    sku = factory.Sequence(lambda n: f"SKU{n:06d}")
    barcode = factory.Sequence(lambda n: f"78901234{n:05d}")
    price = fuzzy.FuzzyDecimal(1.00, 999.99, 2)
    cost = factory.LazyAttribute(lambda obj: obj.price * Decimal('0.6'))  # 60% of price
    category = factory.SubFactory(CategoryFactory)
    is_active = True
    requires_lot = True
    min_stock_level = fuzzy.FuzzyInteger(5, 50)
    max_stock_level = fuzzy.FuzzyInteger(100, 500)
    
    # Nutritional info for food products
    calories_per_100g = fuzzy.FuzzyInteger(50, 600)
    protein_per_100g = fuzzy.FuzzyDecimal(0.5, 30.0, 1)
    carbs_per_100g = fuzzy.FuzzyDecimal(0.0, 80.0, 1)
    fat_per_100g = fuzzy.FuzzyDecimal(0.0, 50.0, 1)


class WarehouseFactory(factory.django.DjangoModelFactory):
    """Factory for Warehouse model."""
    
    class Meta:
        model = Warehouse
    
    name = factory.Faker('company')
    address = factory.Faker('address')
    is_active = True


class StockLotFactory(factory.django.DjangoModelFactory):
    """Factory for StockLot model with realistic expiry dates."""
    
    class Meta:
        model = StockLot
    
    product = factory.SubFactory(ProductFactory)
    lot_code = factory.Sequence(lambda n: f"LOT{n:08d}")
    expiry_date = factory.LazyFunction(
        lambda: date.today() + timedelta(days=fuzzy.FuzzyInteger(30, 365).fuzz())
    )
    qty_on_hand = fuzzy.FuzzyInteger(0, 1000)
    unit_cost = factory.LazyAttribute(lambda obj: obj.product.cost)
    warehouse = factory.SubFactory(WarehouseFactory)
    
    @factory.post_generation
    def ensure_valid_expiry(self, create, extracted, **kwargs):
        """Ensure expiry date is in the future for active lots."""
        if create and self.qty_on_hand > 0:
            # Active lots should have future expiry dates
            if self.expiry_date <= date.today():
                self.expiry_date = date.today() + timedelta(days=30)
                self.save()


class NearExpiryStockLotFactory(StockLotFactory):
    """Factory for StockLot that expires soon (for testing alerts)."""
    
    expiry_date = factory.LazyFunction(
        lambda: date.today() + timedelta(days=fuzzy.FuzzyInteger(1, 7).fuzz())
    )
    qty_on_hand = fuzzy.FuzzyInteger(10, 100)


class ExpiredStockLotFactory(StockLotFactory):
    """Factory for expired StockLot (for testing cleanup)."""
    
    expiry_date = factory.LazyFunction(
        lambda: date.today() - timedelta(days=fuzzy.FuzzyInteger(1, 30).fuzz())
    )
    qty_on_hand = 0  # Expired lots should be empty


class LowStockLotFactory(StockLotFactory):
    """Factory for StockLot with low quantity (for testing alerts)."""
    
    qty_on_hand = fuzzy.FuzzyInteger(1, 5)
    expiry_date = factory.LazyFunction(
        lambda: date.today() + timedelta(days=fuzzy.FuzzyInteger(60, 365).fuzz())
    )


class BenefitFactory(factory.django.DjangoModelFactory):
    """Factory for Benefit model with realistic promotions."""
    
    class Meta:
        model = Benefit
    
    name = factory.Faker('catch_phrase')
    description = factory.Faker('text', max_nb_chars=300)
    benefit_type = fuzzy.FuzzyChoice(['percentage', 'fixed_amount', 'buy_x_get_y'])
    
    # Percentage discount (5% to 50%)
    percentage_discount = factory.Maybe(
        'benefit_type',
        yes_declaration=fuzzy.FuzzyDecimal(5.0, 50.0, 1),
        no_declaration=None,
        condition=lambda obj: obj.benefit_type == 'percentage'
    )
    
    # Fixed amount discount ($1 to $50)
    fixed_discount = factory.Maybe(
        'benefit_type',
        yes_declaration=fuzzy.FuzzyDecimal(1.00, 50.00, 2),
        no_declaration=None,
        condition=lambda obj: obj.benefit_type == 'fixed_amount'
    )
    
    # Buy X Get Y free
    buy_quantity = factory.Maybe(
        'benefit_type',
        yes_declaration=fuzzy.FuzzyInteger(2, 5),
        no_declaration=None,
        condition=lambda obj: obj.benefit_type == 'buy_x_get_y'
    )
    
    get_quantity = factory.Maybe(
        'benefit_type',
        yes_declaration=fuzzy.FuzzyInteger(1, 2),
        no_declaration=None,
        condition=lambda obj: obj.benefit_type == 'buy_x_get_y'
    )
    
    min_purchase_amount = fuzzy.FuzzyDecimal(0.00, 100.00, 2)
    max_uses_per_customer = fuzzy.FuzzyInteger(1, 10)
    
    start_date = factory.LazyFunction(
        lambda: date.today() - timedelta(days=fuzzy.FuzzyInteger(0, 30).fuzz())
    )
    end_date = factory.LazyFunction(
        lambda: date.today() + timedelta(days=fuzzy.FuzzyInteger(30, 90).fuzz())
    )
    
    is_active = True


class CustomerFactory(factory.django.DjangoModelFactory):
    """Factory for Customer model."""
    
    class Meta:
        model = Customer
    
    name = factory.Faker('company')
    email = factory.Faker('email')
    phone = factory.Faker('phone_number')
    address = factory.Faker('address')
    tax_id = factory.Sequence(lambda n: f"TAX{n:08d}")
    is_active = True
    credit_limit = fuzzy.FuzzyDecimal(1000.00, 50000.00, 2)
    payment_terms_days = fuzzy.FuzzyChoice([15, 30, 45, 60])


class OrderFactory(factory.django.DjangoModelFactory):
    """Factory for Order model with realistic data."""
    
    class Meta:
        model = Order
    
    customer = factory.SubFactory(CustomerFactory)
    order_date = factory.Faker('date_between', start_date='-30d', end_date='today')
    status = fuzzy.FuzzyChoice(['pending', 'confirmed', 'shipped', 'delivered', 'cancelled'])
    
    # Financial fields
    subtotal = fuzzy.FuzzyDecimal(50.00, 5000.00, 2)
    tax_amount = factory.LazyAttribute(lambda obj: obj.subtotal * Decimal('0.21'))  # 21% IVA
    discount_amount = fuzzy.FuzzyDecimal(0.00, 100.00, 2)
    total_amount = factory.LazyAttribute(
        lambda obj: obj.subtotal + obj.tax_amount - obj.discount_amount
    )
    
    # Delivery info
    delivery_address = factory.Faker('address')
    delivery_date = factory.LazyAttribute(
        lambda obj: obj.order_date + timedelta(days=fuzzy.FuzzyInteger(1, 7).fuzz())
    )
    
    notes = factory.Faker('text', max_nb_chars=200)


class OrderItemFactory(factory.django.DjangoModelFactory):
    """Factory for OrderItem model."""
    
    class Meta:
        model = OrderItem
    
    order = factory.SubFactory(OrderFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = fuzzy.FuzzyInteger(1, 50)
    unit_price = factory.LazyAttribute(lambda obj: obj.product.price)
    total_price = factory.LazyAttribute(lambda obj: obj.quantity * obj.unit_price)
    
    # FEFO allocation (will be set by FEFO service)
    allocated_lots = factory.LazyFunction(dict)  # JSON field


class StockMovementFactory(factory.django.DjangoModelFactory):
    """Factory for StockMovement model."""
    
    class Meta:
        model = StockMovement
    
    stock_lot = factory.SubFactory(StockLotFactory)
    movement_type = fuzzy.FuzzyChoice(['in', 'out', 'adjustment', 'transfer'])
    quantity = fuzzy.FuzzyInteger(-100, 100)  # Can be negative for outbound
    reference_type = fuzzy.FuzzyChoice(['purchase', 'sale', 'adjustment', 'transfer'])
    reference_id = fuzzy.FuzzyInteger(1, 9999)
    notes = factory.Faker('sentence')
    
    created_at = factory.Faker('date_time_between', start_date='-30d', end_date='now')


# Specialized factories for complex test scenarios

class ProductWithMultipleLots(ProductFactory):
    """Product with multiple stock lots for FEFO testing."""
    
    @factory.post_generation
    def create_lots(self, create, extracted, **kwargs):
        """Create multiple lots with different expiry dates."""
        if not create:
            return
        
        # Create 3-5 lots with different expiry dates
        lot_count = extracted or fuzzy.FuzzyInteger(3, 5).fuzz()
        
        for i in range(lot_count):
            StockLotFactory(
                product=self,
                expiry_date=date.today() + timedelta(days=30 + (i * 30)),
                qty_on_hand=fuzzy.FuzzyInteger(10, 100).fuzz(),
                lot_code=f"{self.sku}_LOT_{i+1:02d}"
            )


class ProductWithBenefits(ProductFactory):
    """Product with multiple benefits for promotion testing."""
    
    @factory.post_generation
    def create_benefits(self, create, extracted, **kwargs):
        """Create multiple benefits for this product."""
        if not create:
            return
        
        benefit_count = extracted or fuzzy.FuzzyInteger(1, 3).fuzz()
        
        for i in range(benefit_count):
            benefit = BenefitFactory()
            benefit.applicable_products.add(self)


class CompleteOrderWithItems(OrderFactory):
    """Order with multiple items for complex testing."""
    
    @factory.post_generation
    def create_items(self, create, extracted, **kwargs):
        """Create multiple order items."""
        if not create:
            return
        
        item_count = extracted or fuzzy.FuzzyInteger(2, 8).fuzz()
        total = Decimal('0.00')
        
        for i in range(item_count):
            item = OrderItemFactory(order=self)
            total += item.total_price
        
        # Update order totals
        self.subtotal = total
        self.tax_amount = total * Decimal('0.21')
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        self.save()


# Test data traits for specific scenarios

class Traits:
    """Common traits for test scenarios."""
    
    @staticmethod
    def near_expiry_product():
        """Product with lots expiring soon."""
        return ProductFactory(
            name="Near Expiry Product",
            requires_lot=True
        )
    
    @staticmethod
    def low_stock_product():
        """Product with low stock levels."""
        return ProductFactory(
            name="Low Stock Product",
            min_stock_level=50,
            requires_lot=True
        )
    
    @staticmethod
    def high_value_order():
        """High value order for testing limits."""
        return OrderFactory(
            subtotal=fuzzy.FuzzyDecimal(5000.00, 20000.00, 2).fuzz()
        )
    
    @staticmethod
    def bulk_discount_benefit():
        """Bulk discount benefit."""
        return BenefitFactory(
            name="Bulk Discount 20%",
            benefit_type='percentage',
            percentage_discount=Decimal('20.0'),
            min_purchase_amount=Decimal('500.0')
        )


# Utility functions for test setup

def create_fefo_test_scenario():
    """Create a complete FEFO test scenario with multiple products and lots."""
    products = []
    
    for i in range(3):
        product = ProductWithMultipleLots(
            name=f"FEFO Test Product {i+1}",
            sku=f"FEFO{i+1:03d}"
        )
        products.append(product)
    
    return products


def create_promotion_test_scenario():
    """Create products with various benefits for promotion testing."""
    products = []
    
    # Product with percentage discount
    product1 = ProductWithBenefits(
        name="Discounted Product",
        price=Decimal('100.00')
    )
    products.append(product1)
    
    # Product with buy X get Y
    product2 = ProductWithBenefits(
        name="BOGO Product",
        price=Decimal('50.00')
    )
    products.append(product2)
    
    return products


def create_stock_alert_scenario():
    """Create scenario for testing stock alerts."""
    warehouse = WarehouseFactory(name="Main Warehouse")
    
    # Near expiry products
    near_expiry_products = []
    for i in range(3):
        product = ProductFactory(name=f"Near Expiry {i+1}")
        NearExpiryStockLotFactory(
            product=product,
            warehouse=warehouse,
            qty_on_hand=50
        )
        near_expiry_products.append(product)
    
    # Low stock products
    low_stock_products = []
    for i in range(2):
        product = ProductFactory(name=f"Low Stock {i+1}", min_stock_level=20)
        LowStockLotFactory(
            product=product,
            warehouse=warehouse,
            qty_on_hand=5
        )
        low_stock_products.append(product)
    
    return {
        'warehouse': warehouse,
        'near_expiry_products': near_expiry_products,
        'low_stock_products': low_stock_products
    }