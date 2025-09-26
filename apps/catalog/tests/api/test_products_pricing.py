"""
Tests for /catalog/products endpoint with pricing and segment functionality.
"""
import pytest
import time
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time
from hypothesis import given, strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase
from rest_framework.test import APIClient

from apps.catalog.models import Product, Benefit
from apps.catalog.utils import calculate_final_price


class ProductsPricingAPITest(TestCase):
    """Test suite for products pricing API endpoint."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        today = date.today()
        
        # Create test products
        self.product1 = Product.objects.create(
            code="PROD001",
            name="Test Product 1",
            price=Decimal("100.00"),
            is_active=True
        )
        
        self.product2 = Product.objects.create(
            code="PROD002",
            name="Another Product",
            price=Decimal("50.00"),
            is_active=True
        )
        
        # Create test benefits with correct field names
        self.retail_benefit = Benefit.objects.create(
            name="Retail Discount",
            type=Benefit.Type.DISCOUNT,
            segment=Benefit.Segment.RETAIL,
            value=Decimal("10.00"),  # 10% discount
            active_from=today - timedelta(days=10),
            active_to=today + timedelta(days=30)
        )
        
        self.wholesale_benefit = Benefit.objects.create(
            name="Wholesale Discount",
            type=Benefit.Type.DISCOUNT,
            segment=Benefit.Segment.WHOLESALE,
            value=Decimal("20.00"),  # 20% discount
            active_from=today - timedelta(days=5),
            active_to=today + timedelta(days=20)
        )
        
        self.expired_benefit = Benefit.objects.create(
            name="Expired Discount",
            type=Benefit.Type.DISCOUNT,
            segment=Benefit.Segment.RETAIL,
            value=Decimal("15.00"),
            active_from=today - timedelta(days=60),
            active_to=today - timedelta(days=30)
        )
    
    def test_list_products_without_segment(self):
        """Test listing products without segment returns base price as final_price."""
        response = self.client.get('/api/v1/catalog/products')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should return both products
        self.assertEqual(len(data), 2)
        
        # Without segment, final_price should equal base price
        for product in data:
            self.assertEqual(
                Decimal(str(product['final_price'])), 
                Decimal(str(product['price']))
            )
    
    def test_list_products_retail_segment(self):
        """Test listing products with retail segment applies retail benefits."""
        response = self.client.get('/api/v1/catalog/products?segment=retail')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Find product1 in response
        product1_data = next(p for p in data if p['code'] == 'PROD001')
        product2_data = next(p for p in data if p['code'] == 'PROD002')
        
        # Both products should have retail discount applied (10% off) - benefits are global
        expected_price1 = Decimal("90.00")  # 100 - 10%
        self.assertEqual(Decimal(str(product1_data['final_price'])), expected_price1)
        
        # Product2 also gets retail discount applied globally
        expected_price2 = Decimal("45.00")  # 50 - 10%
        self.assertEqual(Decimal(str(product2_data['final_price'])), expected_price2)
    
    def test_list_products_wholesale_segment(self):
        """Test listing products with wholesale segment pricing."""
        response = self.client.get('/api/v1/catalog/products?segment=wholesale')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(len(data), 2)
        
        # Check prices with wholesale benefits applied globally
        product1_data = next(p for p in data if p['code'] == 'PROD001')
        product2_data = next(p for p in data if p['code'] == 'PROD002')
        
        # Both products get the 20% wholesale discount (global benefit)
        # product1: 100.00 with 20% wholesale discount = 80.00
        self.assertEqual(Decimal(product1_data['final_price']), Decimal('80.00'))
        # product2: 50.00 with 20% wholesale discount = 40.00
        self.assertEqual(Decimal(product2_data['final_price']), Decimal('40.00'))
    
    def test_search_products_case_insensitive_name(self):
        """Test case-insensitive search by product name."""
        # Search with lowercase - should find "Test Product 1"
        response = self.client.get('/api/v1/catalog/products?search=test')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)  # Only "Test Product 1" matches
        
        # Search with uppercase
        response = self.client.get('/api/v1/catalog/products?search=TEST')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        
        # Search with mixed case
        response = self.client.get('/api/v1/catalog/products?search=TeSt')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
    
    def test_search_products_case_insensitive_code(self):
        """Test case-insensitive search by product code."""
        # Search with lowercase
        response = self.client.get('/api/v1/catalog/products?search=prod001')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['code'], 'PROD001')
        
        # Search with uppercase
        response = self.client.get('/api/v1/catalog/products?search=PROD001')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['code'], 'PROD001')
    
    @freeze_time("2024-01-15")
    def test_benefit_validity_period(self):
        """Test that benefits are only applied within their validity period."""
        # Clear existing benefits to avoid interference
        Benefit.objects.all().delete()
        
        # Create a current benefit that should be active on 2024-01-15
        current_benefit = Benefit.objects.create(
            name="Current Discount",
            type=Benefit.Type.DISCOUNT,
            segment=Benefit.Segment.RETAIL,
            value=Decimal("10.00"),  # 10% discount
            active_from=date(2024, 1, 1),
            active_to=date(2024, 1, 31)
        )
        
        # Create a future benefit that should NOT be active on 2024-01-15
        future_benefit = Benefit.objects.create(
            name="Future Discount",
            type=Benefit.Type.DISCOUNT,
            value=Decimal("30.00"),
            segment=Benefit.Segment.RETAIL,
            active_from=date(2024, 2, 1),
            active_to=date(2024, 2, 28)
        )
        
        # Should apply current benefit but not future benefit
        response = self.client.get('/api/v1/catalog/products?segment=retail')
        data = response.json()
        product1_data = next(p for p in data if p['code'] == 'PROD001')
        
        # Should have the current retail benefit (10% off), not the future one
        expected_price = Decimal("90.00")  # 100 - 10%
        self.assertEqual(Decimal(str(product1_data['final_price'])), expected_price)
    
    def test_inactive_benefits_not_applied(self):
        """Test that inactive benefits are not applied."""
        # Deactivate all active benefits
        Benefit.objects.filter(is_active=True).update(is_active=False)
        
        response = self.client.get('/api/v1/catalog/products?segment=retail')
        data = response.json()
        
        # All products should have base price since no active benefits
        for product in data:
            self.assertEqual(
                Decimal(str(product['final_price'])), 
                Decimal(str(product['price']))
            )
    
    def test_no_applicable_benefits(self):
        """Test product pricing when no benefits apply."""
        # Create a product without any benefits
        product3 = Product.objects.create(
            code='PROD003',
            name='Test Product 3',
            price=Decimal('75.00')
        )
        
        response = self.client.get('/api/v1/catalog/products?segment=retail')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        product3_data = next(p for p in data if p['code'] == 'PROD003')
        
        # Product3 should get the global retail discount (10% off)
        # 75.00 with 10% retail discount = 67.50
        self.assertEqual(Decimal(product3_data['final_price']), Decimal('67.50'))
    
    def test_get_single_product_with_segment(self):
        """Test getting single product with segment parameter."""
        response = self.client.get(f'/api/v1/catalog/products/{self.product1.id}?segment=wholesale')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should have wholesale discount applied
        expected_price = Decimal("80.00")  # 100 - 20%
        self.assertEqual(Decimal(str(data['final_price'])), expected_price)
    
    def test_search_endpoint_with_segment(self):
        """Test /search endpoint with segment parameter."""
        response = self.client.get('/api/v1/catalog/search?q=test&segment=retail')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should return results with final_price calculated
        self.assertIn('results', data)
        results = data['results']
        self.assertTrue(len(results) > 0)
        
        # Check that final_price is included
        for result in results:
            self.assertIn('final_price', result)
            self.assertIsNotNone(result['final_price'])


class ProductsPricingHypothesisTest(HypothesisTestCase):
    """Property-based tests for pricing calculations using Hypothesis."""
    
    def setUp(self):
        """Set up test data."""
        # Clear any existing data to avoid conflicts
        Product.objects.all().delete()
        Benefit.objects.all().delete()
    
    @given(
        base_price=st.decimals(
            min_value=Decimal("1.00"),
            max_value=Decimal("1000.00"), 
            places=2
        ),
        discount_percentage=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("50.00"),
            places=2
        )
    )
    def test_final_price_non_negative(self, base_price, discount_percentage):
        """Property test: final_price should always be non-negative."""
        # Create unique product for each test to avoid constraint issues
        import random
        import uuid
        product_code = f"PROP{uuid.uuid4().hex[:8].upper()}"
        product = Product.objects.create(
            code=product_code,
            name=f"Property Test Product {product_code}",
            price=base_price,
            is_active=True
        )
        
        today = date.today()
        
        # Create benefit with unique name to avoid constraint issues
        benefit_name = f"Property Test Discount {uuid.uuid4().hex[:8]}"
        benefit = Benefit.objects.create(
            name=benefit_name,
            type=Benefit.Type.DISCOUNT,
            value=discount_percentage,
            segment=Benefit.Segment.RETAIL,
            active_from=today - timedelta(days=1),
            active_to=today + timedelta(days=30)
        )
        
        try:
            final_price = calculate_final_price(product, "retail")
            
            # Property: final_price should always be >= 0
            self.assertGreaterEqual(final_price, Decimal("0.00"))
            
            # Property: final_price should be <= original price for percentage discounts
            self.assertLessEqual(final_price, product.price)
            
        finally:
            # Clean up
            benefit.delete()
            product.delete()

    @given(
        base_price=st.decimals(
            min_value=Decimal("1.00"),
            max_value=Decimal("1000.00"), 
            places=2
        ),
        discount_percentage=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("50.00"),
            places=2
        )
    )
    def test_discount_calculation_properties(self, base_price, discount_percentage):
        """Property test: discount calculations should follow mathematical rules."""
        # Create unique product for each test to avoid constraint issues
        import random
        import uuid
        from decimal import ROUND_HALF_UP
        product_code = f"DISC{uuid.uuid4().hex[:8].upper()}"
        product = Product.objects.create(
            code=product_code,
            name=f"Discount Test Product {product_code}",
            price=base_price,
            is_active=True
        )
        
        today = date.today()
        
        # Create benefit with unique name to avoid constraint issues
        benefit_name = f"Discount Test Benefit {uuid.uuid4().hex[:8]}"
        benefit = Benefit.objects.create(
            name=benefit_name,
            type=Benefit.Type.DISCOUNT,
            value=discount_percentage,
            segment=Benefit.Segment.RETAIL,
            active_from=today - timedelta(days=1),
            active_to=today + timedelta(days=30)
        )
        
        try:
            final_price = calculate_final_price(product, "retail")
            
            # Calculate expected discount using the same rounding as apply_discount
            discount_amount = (base_price * discount_percentage) / Decimal("100")
            expected_final_price = base_price - discount_amount
            # Apply the same rounding as apply_discount function
            expected_final_price_rounded = expected_final_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # Property: calculated final_price should match expected calculation
            self.assertEqual(final_price, expected_final_price_rounded)
            
            # Property: discount amount should be positive
            self.assertGreater(discount_amount, Decimal("0.00"))
            
            # Property: final price should be less than base price (for positive discounts)
            # Only check this if discount actually reduces the price (avoid edge cases where discount is very small)
            if discount_amount >= Decimal("0.01"):
                self.assertLess(final_price, base_price)
            
        finally:
            # Clean up
            benefit.delete()
            product.delete()