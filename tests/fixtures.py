"""
Test fixtures for complex scenarios.
Provides pre-configured test data for integration tests.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth.models import User

from .factories import (
    UserFactory, ProductFactory, StockLotFactory, BenefitFactory,
    OrderFactory, OrderItemFactory, CustomerFactory, WarehouseFactory,
    ProductWithMultipleLots, ProductWithBenefits, CompleteOrderWithItems,
    NearExpiryStockLotFactory, LowStockLotFactory, ExpiredStockLotFactory
)


@pytest.fixture
def admin_user():
    """Admin user for testing."""
    return UserFactory(
        username='admin',
        email='admin@example.com',
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def regular_user():
    """Regular user for testing."""
    return UserFactory(
        username='testuser',
        email='test@example.com'
    )


@pytest.fixture
def main_warehouse():
    """Main warehouse for testing."""
    return WarehouseFactory(
        name='Main Warehouse',
        address='123 Main St, Test City'
    )


@pytest.fixture
def secondary_warehouse():
    """Secondary warehouse for testing."""
    return WarehouseFactory(
        name='Secondary Warehouse',
        address='456 Second St, Test City'
    )


@pytest.fixture
def test_customer():
    """Test customer with good credit."""
    return CustomerFactory(
        name='Test Customer Inc.',
        email='customer@test.com',
        credit_limit=Decimal('10000.00'),
        payment_terms_days=30
    )


@pytest.fixture
def vip_customer():
    """VIP customer with high credit limit."""
    return CustomerFactory(
        name='VIP Customer Corp.',
        email='vip@customer.com',
        credit_limit=Decimal('50000.00'),
        payment_terms_days=15
    )


# Product fixtures with multiple lots for FEFO testing

@pytest.fixture
def fefo_product_a(main_warehouse):
    """Product A with multiple lots for FEFO testing."""
    product = ProductFactory(
        name='FEFO Product A',
        sku='FEFO001',
        price=Decimal('25.00'),
        requires_lot=True
    )
    
    # Create lots with different expiry dates (FEFO order)
    lots = [
        StockLotFactory(
            product=product,
            warehouse=main_warehouse,
            lot_code='FEFO001_LOT_001',
            expiry_date=date.today() + timedelta(days=30),
            qty_on_hand=100,
            unit_cost=Decimal('15.00')
        ),
        StockLotFactory(
            product=product,
            warehouse=main_warehouse,
            lot_code='FEFO001_LOT_002',
            expiry_date=date.today() + timedelta(days=60),
            qty_on_hand=150,
            unit_cost=Decimal('15.00')
        ),
        StockLotFactory(
            product=product,
            warehouse=main_warehouse,
            lot_code='FEFO001_LOT_003',
            expiry_date=date.today() + timedelta(days=90),
            qty_on_hand=200,
            unit_cost=Decimal('15.00')
        )
    ]
    
    return {
        'product': product,
        'lots': lots,
        'total_stock': 450
    }


@pytest.fixture
def fefo_product_b(main_warehouse):
    """Product B with multiple lots for FEFO testing."""
    product = ProductFactory(
        name='FEFO Product B',
        sku='FEFO002',
        price=Decimal('50.00'),
        requires_lot=True
    )
    
    # Create lots with mixed expiry dates
    lots = [
        StockLotFactory(
            product=product,
            warehouse=main_warehouse,
            lot_code='FEFO002_LOT_001',
            expiry_date=date.today() + timedelta(days=45),
            qty_on_hand=75,
            unit_cost=Decimal('30.00')
        ),
        StockLotFactory(
            product=product,
            warehouse=main_warehouse,
            lot_code='FEFO002_LOT_002',
            expiry_date=date.today() + timedelta(days=15),  # Expires first
            qty_on_hand=50,
            unit_cost=Decimal('30.00')
        ),
        StockLotFactory(
            product=product,
            warehouse=main_warehouse,
            lot_code='FEFO002_LOT_003',
            expiry_date=date.today() + timedelta(days=120),
            qty_on_hand=125,
            unit_cost=Decimal('30.00')
        )
    ]
    
    return {
        'product': product,
        'lots': lots,
        'total_stock': 250
    }


# Products with benefits for promotion testing

@pytest.fixture
def percentage_discount_product():
    """Product with percentage discount benefit."""
    product = ProductFactory(
        name='Discounted Product',
        sku='DISC001',
        price=Decimal('100.00')
    )
    
    benefit = BenefitFactory(
        name='20% Off Everything',
        benefit_type='percentage',
        percentage_discount=Decimal('20.0'),
        min_purchase_amount=Decimal('50.0'),
        start_date=date.today() - timedelta(days=1),
        end_date=date.today() + timedelta(days=30)
    )
    benefit.applicable_products.add(product)
    
    return {
        'product': product,
        'benefit': benefit,
        'expected_discount': Decimal('20.0')  # 20% off $100 = $20
    }


@pytest.fixture
def buy_x_get_y_product():
    """Product with buy X get Y benefit."""
    product = ProductFactory(
        name='BOGO Product',
        sku='BOGO001',
        price=Decimal('30.00')
    )
    
    benefit = BenefitFactory(
        name='Buy 2 Get 1 Free',
        benefit_type='buy_x_get_y',
        buy_quantity=2,
        get_quantity=1,
        start_date=date.today() - timedelta(days=1),
        end_date=date.today() + timedelta(days=30)
    )
    benefit.applicable_products.add(product)
    
    return {
        'product': product,
        'benefit': benefit,
        'buy_qty': 2,
        'get_qty': 1
    }


@pytest.fixture
def fixed_discount_product():
    """Product with fixed amount discount."""
    product = ProductFactory(
        name='Fixed Discount Product',
        sku='FIXED001',
        price=Decimal('75.00')
    )
    
    benefit = BenefitFactory(
        name='$15 Off',
        benefit_type='fixed_amount',
        fixed_discount=Decimal('15.00'),
        min_purchase_amount=Decimal('50.0'),
        start_date=date.today() - timedelta(days=1),
        end_date=date.today() + timedelta(days=30)
    )
    benefit.applicable_products.add(product)
    
    return {
        'product': product,
        'benefit': benefit,
        'discount_amount': Decimal('15.00')
    }


# Stock alert scenarios

@pytest.fixture
def near_expiry_scenario(main_warehouse):
    """Products with lots expiring soon."""
    products = []
    
    for i in range(3):
        product = ProductFactory(
            name=f'Near Expiry Product {i+1}',
            sku=f'NEAR{i+1:03d}',
            requires_lot=True
        )
        
        # Create lot expiring in 3-7 days
        lot = NearExpiryStockLotFactory(
            product=product,
            warehouse=main_warehouse,
            expiry_date=date.today() + timedelta(days=3 + i),
            qty_on_hand=50 + (i * 25)
        )
        
        products.append({
            'product': product,
            'lot': lot,
            'days_to_expiry': 3 + i
        })
    
    return products


@pytest.fixture
def low_stock_scenario(main_warehouse):
    """Products with low stock levels."""
    products = []
    
    for i in range(3):
        product = ProductFactory(
            name=f'Low Stock Product {i+1}',
            sku=f'LOW{i+1:03d}',
            min_stock_level=20,
            requires_lot=True
        )
        
        # Create lot with low quantity
        lot = LowStockLotFactory(
            product=product,
            warehouse=main_warehouse,
            qty_on_hand=5 + i  # 5, 6, 7 units (all below min_stock_level)
        )
        
        products.append({
            'product': product,
            'lot': lot,
            'current_stock': 5 + i,
            'min_level': 20
        })
    
    return products


@pytest.fixture
def expired_lots_scenario(main_warehouse):
    """Expired lots for cleanup testing."""
    products = []
    
    for i in range(2):
        product = ProductFactory(
            name=f'Product with Expired Lots {i+1}',
            sku=f'EXP{i+1:03d}',
            requires_lot=True
        )
        
        # Create expired lot (should be cleaned up)
        expired_lot = ExpiredStockLotFactory(
            product=product,
            warehouse=main_warehouse,
            expiry_date=date.today() - timedelta(days=10 + i),
            qty_on_hand=0  # Already cleaned
        )
        
        # Create active lot
        active_lot = StockLotFactory(
            product=product,
            warehouse=main_warehouse,
            expiry_date=date.today() + timedelta(days=60),
            qty_on_hand=100
        )
        
        products.append({
            'product': product,
            'expired_lot': expired_lot,
            'active_lot': active_lot
        })
    
    return products


# Complex order scenarios

@pytest.fixture
def multi_product_order(test_customer, fefo_product_a, fefo_product_b):
    """Order with multiple products requiring FEFO allocation."""
    order = OrderFactory(
        customer=test_customer,
        status='pending'
    )
    
    # Order items
    item_a = OrderItemFactory(
        order=order,
        product=fefo_product_a['product'],
        quantity=75,  # Should use first lot completely + part of second
        unit_price=fefo_product_a['product'].price
    )
    
    item_b = OrderItemFactory(
        order=order,
        product=fefo_product_b['product'],
        quantity=60,  # Should use lot with earliest expiry first
        unit_price=fefo_product_b['product'].price
    )
    
    # Update order totals
    subtotal = item_a.total_price + item_b.total_price
    order.subtotal = subtotal
    order.tax_amount = subtotal * Decimal('0.21')
    order.total_amount = order.subtotal + order.tax_amount
    order.save()
    
    return {
        'order': order,
        'items': [item_a, item_b],
        'expected_fefo_allocation': {
            'product_a': [
                {'lot_code': 'FEFO001_LOT_001', 'qty': 75},  # Use earliest expiry first
            ],
            'product_b': [
                {'lot_code': 'FEFO002_LOT_002', 'qty': 50},  # Earliest expiry
                {'lot_code': 'FEFO002_LOT_001', 'qty': 10},  # Next earliest
            ]
        }
    }


@pytest.fixture
def promotion_order(test_customer, percentage_discount_product, buy_x_get_y_product):
    """Order with products that have promotions."""
    order = OrderFactory(
        customer=test_customer,
        status='pending'
    )
    
    # Item with percentage discount
    item_discount = OrderItemFactory(
        order=order,
        product=percentage_discount_product['product'],
        quantity=2,
        unit_price=percentage_discount_product['product'].price
    )
    
    # Item with buy X get Y
    item_bogo = OrderItemFactory(
        order=order,
        product=buy_x_get_y_product['product'],
        quantity=3,  # Buy 2 get 1 free
        unit_price=buy_x_get_y_product['product'].price
    )
    
    return {
        'order': order,
        'discount_item': item_discount,
        'bogo_item': item_bogo,
        'expected_savings': {
            'percentage_discount': Decimal('40.00'),  # 20% off $200
            'bogo_discount': Decimal('30.00')  # 1 free item worth $30
        }
    }


@pytest.fixture
def high_volume_order(vip_customer):
    """Large order for performance testing."""
    order = CompleteOrderWithItems(
        customer=vip_customer,
        status='pending'
    )
    
    # Create 20 items with different products
    items = []
    for i in range(20):
        product = ProductWithMultipleLots(
            name=f'Bulk Product {i+1}',
            sku=f'BULK{i+1:03d}',
            price=Decimal('25.00') + (i * Decimal('5.00'))
        )
        
        item = OrderItemFactory(
            order=order,
            product=product,
            quantity=10 + (i * 2),
            unit_price=product.price
        )
        items.append(item)
    
    return {
        'order': order,
        'items': items,
        'total_items': 20,
        'total_products': sum(item.quantity for item in items)
    }


# Cache testing scenarios

@pytest.fixture
def cache_test_products():
    """Products for cache performance testing."""
    products = []
    
    for i in range(50):
        product = ProductFactory(
            name=f'Cache Test Product {i+1}',
            sku=f'CACHE{i+1:03d}',
            price=Decimal('10.00') + (i * Decimal('2.00'))
        )
        products.append(product)
    
    return products


# Concurrency testing scenarios

@pytest.fixture
def concurrent_order_scenario(main_warehouse):
    """Scenario for testing concurrent order processing."""
    # Product with limited stock
    product = ProductFactory(
        name='Limited Stock Product',
        sku='LIMIT001',
        price=Decimal('100.00'),
        requires_lot=True
    )
    
    # Single lot with exactly 100 units
    lot = StockLotFactory(
        product=product,
        warehouse=main_warehouse,
        lot_code='LIMIT001_LOT_001',
        qty_on_hand=100,
        expiry_date=date.today() + timedelta(days=60)
    )
    
    # Create multiple customers for concurrent orders
    customers = [
        CustomerFactory(name=f'Concurrent Customer {i+1}')
        for i in range(5)
    ]
    
    return {
        'product': product,
        'lot': lot,
        'available_stock': 100,
        'customers': customers
    }


# Health check scenarios

@pytest.fixture
def health_check_scenario():
    """Scenario for testing health checks."""
    return {
        'expected_checks': ['database', 'cache', 'smtp', 'celery'],
        'healthy_response_time_ms': 100,
        'degraded_response_time_ms': 500,
        'unhealthy_response_time_ms': 1000
    }


# Metrics scenarios

@pytest.fixture
def metrics_scenario():
    """Scenario for testing metrics collection."""
    return {
        'expected_metrics': [
            'http_requests_total',
            'cache_hits_total',
            'cache_misses_total',
            'redis_failures_total',
            'email_alerts_sent_total',
            'fefo_allocations_total',
            'stock_movements_total'
        ],
        'sample_labels': {
            'method': 'GET',
            'status': '200',
            'endpoint': '/api/products/'
        }
    }


# Complete integration test scenario

@pytest.fixture
def full_integration_scenario(
    main_warehouse, 
    test_customer, 
    fefo_product_a, 
    fefo_product_b,
    percentage_discount_product
):
    """Complete scenario for full integration testing."""
    # Create order with FEFO products and promotions
    order = OrderFactory(
        customer=test_customer,
        status='pending'
    )
    
    # Add items
    items = [
        OrderItemFactory(
            order=order,
            product=fefo_product_a['product'],
            quantity=50,
            unit_price=fefo_product_a['product'].price
        ),
        OrderItemFactory(
            order=order,
            product=fefo_product_b['product'],
            quantity=30,
            unit_price=fefo_product_b['product'].price
        ),
        OrderItemFactory(
            order=order,
            product=percentage_discount_product['product'],
            quantity=1,
            unit_price=percentage_discount_product['product'].price
        )
    ]
    
    return {
        'warehouse': main_warehouse,
        'customer': test_customer,
        'order': order,
        'items': items,
        'fefo_products': [fefo_product_a, fefo_product_b],
        'promotion_product': percentage_discount_product,
        'expected_operations': [
            'fefo_allocation',
            'promotion_calculation',
            'stock_reservation',
            'cache_invalidation',
            'metrics_recording'
        ]
    }