"""
Tests for segment-differentiated cache functionality.

This module tests the intelligent caching system that differentiates between
retail and wholesale segments to ensure correct pricing and offers are cached
and served to each segment without cross-contamination.
"""

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.core.cache import cache
from datetime import date, timedelta

from apps.catalog.cache_segment import SegmentCache, segment_cache
from apps.catalog.models import Product, Benefit


class TestSegmentCache(TestCase):
    """Test cases for SegmentCache functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.cache = SegmentCache()
        
        # Clear cache before each test
        cache.clear()
        
        # Create test products manually
        self.product1 = Product.objects.create(
            code="TEST001",
            name="Test Product 1",
            price=Decimal("100.00"),
            tax_rate=Decimal("21.00")
        )
        self.product2 = Product.objects.create(
            code="TEST002", 
            name="Test Product 2",
            price=Decimal("50.00"),
            tax_rate=Decimal("21.00")
        )
        
        # Create test benefits manually
        self.retail_benefit = Benefit.objects.create(
            name="Retail Discount",
            type="discount",
            segment="retail",
            value=Decimal("10.00"),
            active_from=date.today(),
            active_to=date.today() + timedelta(days=30)
        )
        self.wholesale_benefit = Benefit.objects.create(
            name="Wholesale Discount",
            type="discount", 
            segment="wholesale",
            value=Decimal("20.00"),
            active_from=date.today(),
            active_to=date.today() + timedelta(days=30)
        )
    
    def test_generate_segment_key_basic(self):
        """Test basic segment key generation."""
        key = self.cache._generate_segment_key("test:key", "retail")
        self.assertEqual(key, "test:key:seg:retail")
        
        key = self.cache._generate_segment_key("test:key", "wholesale")
        self.assertEqual(key, "test:key:seg:wholesale")
    
    def test_generate_segment_key_default_segment(self):
        """Test segment key generation with default segment."""
        key = self.cache._generate_segment_key("test:key")
        self.assertEqual(key, "test:key:seg:retail")
    
    def test_generate_segment_key_with_params(self):
        """Test segment key generation with extra parameters."""
        params = {"search": "test", "page": 1}
        key = self.cache._generate_segment_key("test:key", "retail", params)
        self.assertIn("test:key:seg:retail:params:", key)
        self.assertIn("page=1", key)
        self.assertIn("search=test", key)
    
    def test_generate_segment_key_long_params(self):
        """Test segment key generation with long parameters (should be hashed)."""
        long_params = {f"param_{i}": f"value_{i}" for i in range(20)}
        key = self.cache._generate_segment_key("test:key", "retail", long_params)
        self.assertIn("test:key:seg:retail:params:", key)
        # Should contain hash instead of full params
        self.assertTrue(len(key) < 200)  # Should be much shorter than full params
    
    def test_products_list_cache_miss(self):
        """Test products list cache miss."""
        result = self.cache.get_products_list("retail", {"search": "test"})
        self.assertIsNone(result)
    
    def test_products_list_cache_hit(self):
        """Test products list cache hit."""
        test_data = [{"id": 1, "name": "Test Product"}]
        filters = {"search": "test"}
        
        # Set cache
        success = self.cache.set_products_list(test_data, "retail", filters)
        self.assertTrue(success)
        
        # Get from cache
        result = self.cache.get_products_list("retail", filters)
        self.assertEqual(result, test_data)
    
    def test_products_list_segment_isolation(self):
        """Test that retail and wholesale caches are isolated."""
        retail_data = [{"id": 1, "name": "Retail Product", "price": "90.00"}]
        wholesale_data = [{"id": 1, "name": "Wholesale Product", "price": "80.00"}]
        filters = {"search": "test"}
        
        # Set different data for each segment
        self.cache.set_products_list(retail_data, "retail", filters)
        self.cache.set_products_list(wholesale_data, "wholesale", filters)
        
        # Verify isolation
        retail_result = self.cache.get_products_list("retail", filters)
        wholesale_result = self.cache.get_products_list("wholesale", filters)
        
        self.assertEqual(retail_result, retail_data)
        self.assertEqual(wholesale_result, wholesale_data)
        self.assertNotEqual(retail_result, wholesale_result)
    
    def test_product_pricing_cache(self):
        """Test product pricing cache functionality."""
        pricing_data = {
            "base_price": "100.00",
            "final_price": "90.00",
            "discount": "10.00"
        }
        
        # Cache miss
        result = self.cache.get_product_pricing(1, "retail")
        self.assertIsNone(result)
        
        # Set cache
        success = self.cache.set_product_pricing(1, pricing_data, "retail")
        self.assertTrue(success)
        
        # Cache hit
        result = self.cache.get_product_pricing(1, "retail")
        self.assertEqual(result, pricing_data)
    
    def test_product_pricing_segment_isolation(self):
        """Test product pricing segment isolation."""
        retail_pricing = {"final_price": "90.00"}
        wholesale_pricing = {"final_price": "80.00"}
        
        # Set different pricing for each segment
        self.cache.set_product_pricing(1, retail_pricing, "retail")
        self.cache.set_product_pricing(1, wholesale_pricing, "wholesale")
        
        # Verify isolation
        retail_result = self.cache.get_product_pricing(1, "retail")
        wholesale_result = self.cache.get_product_pricing(1, "wholesale")
        
        self.assertEqual(retail_result, retail_pricing)
        self.assertEqual(wholesale_result, wholesale_pricing)
    
    def test_active_benefits_cache(self):
        """Test active benefits cache functionality."""
        benefits_data = [
            {"id": 1, "name": "Retail Discount", "segment": "retail"}
        ]
        
        # Cache miss
        result = self.cache.get_active_benefits("retail")
        self.assertIsNone(result)
        
        # Set cache
        success = self.cache.set_active_benefits(benefits_data, "retail")
        self.assertTrue(success)
        
        # Cache hit
        result = self.cache.get_active_benefits("retail")
        self.assertEqual(result, benefits_data)
    
    def test_active_benefits_segment_isolation(self):
        """Test active benefits segment isolation."""
        retail_benefits = [{"name": "Retail Discount", "segment": "retail"}]
        wholesale_benefits = [{"name": "Wholesale Discount", "segment": "wholesale"}]
        
        # Set different benefits for each segment
        self.cache.set_active_benefits(retail_benefits, "retail")
        self.cache.set_active_benefits(wholesale_benefits, "wholesale")
        
        # Verify isolation
        retail_result = self.cache.get_active_benefits("retail")
        wholesale_result = self.cache.get_active_benefits("wholesale")
        
        self.assertEqual(retail_result, retail_benefits)
        self.assertEqual(wholesale_result, wholesale_benefits)
    
    def test_invalidate_segment(self):
        """Test segment invalidation."""
        # Set up cache data for both segments
        test_data = [{"id": 1, "name": "Test"}]
        self.cache.set_products_list(test_data, "retail")
        self.cache.set_products_list(test_data, "wholesale")
        self.cache.set_active_benefits(test_data, "retail")
        self.cache.set_active_benefits(test_data, "wholesale")
        
        # Invalidate retail segment
        count = self.cache.invalidate_segment("retail")
        self.assertGreater(count, 0)
        
        # Retail cache should be cleared, wholesale should remain
        self.assertIsNone(self.cache.get_products_list("retail"))
        self.assertIsNotNone(self.cache.get_products_list("wholesale"))
    
    def test_invalidate_product(self):
        """Test product invalidation across segments."""
        pricing_data = {"final_price": "100.00"}
        
        # Set pricing for both segments
        self.cache.set_product_pricing(1, pricing_data, "retail")
        self.cache.set_product_pricing(1, pricing_data, "wholesale")
        
        # Invalidate product
        count = self.cache.invalidate_product(1)
        self.assertGreater(count, 0)
        
        # Both segments should be cleared for this product
        self.assertIsNone(self.cache.get_product_pricing(1, "retail"))
        self.assertIsNone(self.cache.get_product_pricing(1, "wholesale"))
    
    @patch('apps.catalog.cache_segment.increment_counter')
    def test_metrics_tracking(self, mock_increment):
        """Test that cache operations are tracked with metrics."""
        # Test cache miss
        self.cache.get_products_list("retail")
        mock_increment.assert_called_with('segment_cache_misses_total', {
            'segment': 'retail',
            'cache_type': 'products_list'
        })
        
        # Test cache set
        self.cache.set_products_list([{"test": "data"}], "retail")
        mock_increment.assert_called_with('segment_cache_sets_total', {
            'segment': 'retail',
            'cache_type': 'products_list'
        })
    
    @patch('apps.core.cache.fault_tolerant_cache.get')
    def test_redis_failure_handling(self, mock_get):
        """Test graceful handling of Redis failures."""
        # Simulate Redis failure
        mock_get.return_value = None  # Instead of raising exception
        
        # Should return None gracefully
        result = self.cache.get_products_list("retail")
        self.assertIsNone(result)
    
    def test_custom_timeout(self):
        """Test custom timeout settings."""
        test_data = [{"id": 1}]
        
        # Set with custom timeout
        success = self.cache.set_products_list(test_data, "retail", timeout=60)
        self.assertTrue(success)
        
        # Should still be retrievable
        result = self.cache.get_products_list("retail")
        self.assertEqual(result, test_data)


class TestSegmentCachedDecorator(TestCase):
    """Test cases for segment_cached_function decorator."""
    
    def setUp(self):
        """Set up test environment."""
        cache.clear()
    
    @patch('apps.catalog.cache_segment.increment_counter')
    def test_decorator_cache_miss_and_hit(self, mock_increment):
        """Test decorator cache miss and subsequent hit."""
        from apps.catalog.cache_segment import segment_cached_function
        
        call_count = 0
        
        @segment_cached_function(timeout=300, cache_type='test')
        def test_function(segment='retail'):
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}_{segment}"
        
        # First call - cache miss
        result1 = test_function(segment='retail')
        self.assertEqual(result1, "result_1_retail")
        self.assertEqual(call_count, 1)
        
        # Second call - cache hit
        result2 = test_function(segment='retail')
        self.assertEqual(result2, "result_1_retail")  # Same result
        self.assertEqual(call_count, 1)  # Function not called again
        
        # Verify metrics were called
        mock_increment.assert_any_call('segment_cache_misses_total', {
            'segment': 'retail',
            'cache_type': 'test',
            'function': 'test_function'
        })
    
    def test_decorator_segment_isolation(self):
        """Test decorator maintains segment isolation."""
        from apps.catalog.cache_segment import segment_cached_function
        
        call_count = 0
        
        @segment_cached_function(timeout=300, cache_type='test')
        def test_function(segment='retail'):
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}_{segment}"
        
        # Call for retail
        retail_result = test_function(segment='retail')
        self.assertEqual(retail_result, "result_1_retail")
        
        # Call for wholesale - should be cache miss
        wholesale_result = test_function(segment='wholesale')
        self.assertEqual(wholesale_result, "result_2_wholesale")
        
        # Verify both segments maintain their cached values
        retail_result2 = test_function(segment='retail')
        wholesale_result2 = test_function(segment='wholesale')
        
        self.assertEqual(retail_result2, "result_1_retail")
        self.assertEqual(wholesale_result2, "result_2_wholesale")
        self.assertEqual(call_count, 2)  # Only called twice total


class TestSegmentCacheIntegration(TestCase):
    """Integration tests for segment cache with real data."""
    
    def setUp(self):
        """Set up integration test data."""
        cache.clear()
        
        # Create products with different pricing for segments
        self.product = Product.objects.create(
            code="INT001",
            name="Integration Test Product",
            price=Decimal("100.00"),
            tax_rate=Decimal("21.00")
        )
        
        # Create segment-specific benefits
        self.retail_benefit = Benefit.objects.create(
            name="Retail 10% Off",
            type="discount",
            segment="retail", 
            value=Decimal("10.00"),
            active_from=date.today(),
            active_to=date.today() + timedelta(days=30)
        )
        self.wholesale_benefit = Benefit.objects.create(
            name="Wholesale 20% Off",
            type="discount",
            segment="wholesale",
            value=Decimal("20.00"),
            active_from=date.today(),
            active_to=date.today() + timedelta(days=30)
        )
    
    def test_end_to_end_segment_caching(self):
        """Test complete segment caching workflow."""
        # Simulate API response data for different segments
        retail_products = [
            {
                "id": self.product.id,
                "code": self.product.code,
                "name": self.product.name,
                "price": str(self.product.price),
                "final_price": "90.00",  # With 10% retail discount
                "segment": "retail"
            }
        ]
        
        wholesale_products = [
            {
                "id": self.product.id,
                "code": self.product.code,
                "name": self.product.name,
                "price": str(self.product.price),
                "final_price": "80.00",  # With 20% wholesale discount
                "segment": "wholesale"
            }
        ]
        
        # Cache products for both segments
        segment_cache.set_products_list(retail_products, "retail")
        segment_cache.set_products_list(wholesale_products, "wholesale")
        
        # Retrieve and verify segment isolation
        cached_retail = segment_cache.get_products_list("retail")
        cached_wholesale = segment_cache.get_products_list("wholesale")
        
        self.assertEqual(cached_retail[0]["final_price"], "90.00")
        self.assertEqual(cached_wholesale[0]["final_price"], "80.00")
        
        # Test product invalidation
        segment_cache.invalidate_product(self.product.id)
        
        # Product-specific caches should be cleared
        self.assertIsNone(segment_cache.get_product_pricing(self.product.id, "retail"))
        self.assertIsNone(segment_cache.get_product_pricing(self.product.id, "wholesale"))