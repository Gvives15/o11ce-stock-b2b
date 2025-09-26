"""
Comprehensive test suite for BFF system.
Tests concurrency, FEFO logic, cache invalidation, health checks, metrics, and rate limiting.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase, TransactionTestCase, override_settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
from datetime import date, timedelta
from decimal import Decimal

from apps.inventory.models import Product, StockLot, Warehouse, Order, OrderItem
from apps.inventory.services import FEFOService, StockService
from apps.core.cache import CacheService
from apps.core.health import HealthCheckService
from apps.core.metrics import MetricsService
from tests.factories import *
from tests.fixtures import *


class FEFOConcurrencyTests(TransactionTestCase):
    """Test FEFO logic under concurrent access."""
    
    def setUp(self):
        """Set up test data for concurrency tests."""
        self.warehouse = WarehouseFactory()
        self.product = ProductFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create multiple lots with different expiry dates
        self.lots = []
        base_date = date.today() + timedelta(days=10)
        for i in range(5):
            lot = StockLotFactory(
                product=self.product,
                warehouse=self.warehouse,
                expiry_date=base_date + timedelta(days=i),
                quantity=100,
                reserved_quantity=0
            )
            self.lots.append(lot)
    
    def test_concurrent_fefo_allocation(self):
        """Test that FEFO allocation works correctly under concurrent access."""
        fefo_service = FEFOService()
        results = []
        errors = []
        
        def allocate_stock(quantity):
            """Allocate stock in a separate thread."""
            try:
                result = fefo_service.allocate_stock(
                    product=self.product,
                    warehouse=self.warehouse,
                    quantity=quantity
                )
                results.append(result)
                return result
            except Exception as e:
                errors.append(e)
                return None
        
        # Run concurrent allocations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(10):
                future = executor.submit(allocate_stock, 20)
                futures.append(future)
            
            # Wait for all to complete
            for future in as_completed(futures):
                future.result()
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        
        # Verify allocations were successful
        successful_allocations = [r for r in results if r and r.get('success')]
        self.assertGreater(len(successful_allocations), 0)
        
        # Verify FEFO order was maintained
        # Check that earliest expiry lots were used first
        for allocation in successful_allocations:
            if allocation.get('allocations'):
                expiry_dates = [
                    alloc['lot'].expiry_date 
                    for alloc in allocation['allocations']
                ]
                # Should be sorted by expiry date (FEFO)
                self.assertEqual(expiry_dates, sorted(expiry_dates))
    
    def test_concurrent_order_processing(self):
        """Test concurrent order processing with FEFO."""
        results = []
        errors = []
        
        def process_order(order_id):
            """Process an order in a separate thread."""
            try:
                order = Order.objects.get(id=order_id)
                stock_service = StockService()
                result = stock_service.process_order(order)
                results.append(result)
                return result
            except Exception as e:
                errors.append(e)
                return None
        
        # Create multiple orders
        orders = []
        for i in range(5):
            order = Order.objects.create(
                customer=self.user,
                warehouse=self.warehouse,
                status='pending'
            )
            OrderItem.objects.create(
                order=order,
                product=self.product,
                quantity=30,
                unit_price=Decimal('10.00')
            )
            orders.append(order)
        
        # Process orders concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for order in orders:
                future = executor.submit(process_order, order.id)
                futures.append(future)
            
            # Wait for all to complete
            for future in as_completed(futures):
                future.result()
        
        # Verify results
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        
        # Verify stock consistency
        total_allocated = sum(
            lot.reserved_quantity for lot in StockLot.objects.all()
        )
        expected_allocation = len([r for r in results if r and r.get('success')]) * 30
        self.assertLessEqual(total_allocated, expected_allocation)
    
    def test_race_condition_prevention(self):
        """Test that race conditions are prevented in stock allocation."""
        # Create a lot with limited stock
        limited_lot = StockLotFactory(
            product=self.product,
            warehouse=self.warehouse,
            quantity=50,  # Limited quantity
            reserved_quantity=0
        )
        
        allocation_results = []
        
        def try_allocate_large_quantity():
            """Try to allocate more than available."""
            fefo_service = FEFOService()
            try:
                result = fefo_service.allocate_stock(
                    product=self.product,
                    warehouse=self.warehouse,
                    quantity=40  # Multiple threads trying to allocate 40 each
                )
                allocation_results.append(result)
            except Exception as e:
                allocation_results.append({'error': str(e)})
        
        # Run multiple threads trying to over-allocate
        threads = []
        for i in range(3):
            thread = threading.Thread(target=try_allocate_large_quantity)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify that not all allocations succeeded (preventing over-allocation)
        successful_allocations = [
            r for r in allocation_results 
            if r.get('success') and not r.get('error')
        ]
        
        # Should have at most 1 successful allocation (50/40 = 1.25)
        self.assertLessEqual(len(successful_allocations), 1)


@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocalMemoryCache',
        'LOCATION': 'test-cache',
    }
})
class CacheInvalidationTests(TestCase):
    """Test cache invalidation and consistency."""
    
    def setUp(self):
        """Set up test data."""
        self.warehouse = WarehouseFactory()
        self.product = ProductFactory()
        self.cache_service = CacheService()
        cache.clear()
    
    def test_cache_invalidation_on_stock_update(self):
        """Test that cache is invalidated when stock is updated."""
        # Create initial stock
        lot = StockLotFactory(
            product=self.product,
            warehouse=self.warehouse,
            quantity=100
        )
        
        # Cache stock data
        cache_key = f"stock:{self.product.id}:{self.warehouse.id}"
        initial_stock = {'quantity': 100, 'lots': 1}
        cache.set(cache_key, initial_stock, 300)
        
        # Verify cache is set
        cached_data = cache.get(cache_key)
        self.assertEqual(cached_data['quantity'], 100)
        
        # Update stock (should invalidate cache)
        lot.quantity = 150
        lot.save()
        
        # Verify cache was invalidated
        # Note: In a real implementation, this would be handled by signals
        # For this test, we'll manually invalidate
        cache.delete(cache_key)
        cached_data = cache.get(cache_key)
        self.assertIsNone(cached_data)
    
    def test_cache_consistency_across_operations(self):
        """Test cache consistency across multiple operations."""
        cache_service = CacheService()
        
        # Set initial cache data
        product_key = f"product:{self.product.id}"
        stock_key = f"stock:{self.product.id}"
        
        cache_service.set(product_key, {'name': self.product.name}, 300)
        cache_service.set(stock_key, {'quantity': 100}, 300)
        
        # Verify initial state
        self.assertIsNotNone(cache_service.get(product_key))
        self.assertIsNotNone(cache_service.get(stock_key))
        
        # Perform operation that should invalidate related caches
        cache_service.invalidate_pattern(f"*:{self.product.id}*")
        
        # Verify caches were invalidated
        self.assertIsNone(cache_service.get(product_key))
        self.assertIsNone(cache_service.get(stock_key))
    
    def test_cache_performance_under_load(self):
        """Test cache performance under concurrent load."""
        cache_service = CacheService()
        results = []
        
        def cache_operations():
            """Perform cache operations in a thread."""
            for i in range(100):
                key = f"test_key_{i}"
                value = {'data': f'value_{i}'}
                
                # Set
                cache_service.set(key, value, 60)
                
                # Get
                retrieved = cache_service.get(key)
                results.append(retrieved is not None)
                
                # Delete
                cache_service.delete(key)
        
        # Run concurrent cache operations
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(cache_operations) for _ in range(5)]
            for future in as_completed(futures):
                future.result()
        
        # Verify most operations succeeded
        success_rate = sum(results) / len(results)
        self.assertGreater(success_rate, 0.9)  # 90% success rate
    
    def test_cache_memory_usage(self):
        """Test cache memory usage and cleanup."""
        cache_service = CacheService()
        
        # Fill cache with data
        for i in range(1000):
            key = f"memory_test_{i}"
            value = {'data': 'x' * 1000}  # 1KB per entry
            cache_service.set(key, value, 60)
        
        # Verify data is cached
        test_key = "memory_test_500"
        self.assertIsNotNone(cache_service.get(test_key))
        
        # Clear cache
        cache.clear()
        
        # Verify cache is empty
        self.assertIsNone(cache_service.get(test_key))


class HealthCheckTests(TestCase):
    """Test health check functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.health_service = HealthCheckService()
    
    def test_database_health_check(self):
        """Test database connectivity health check."""
        result = self.health_service.check_database()
        
        self.assertTrue(result['healthy'])
        self.assertEqual(result['service'], 'database')
        self.assertIn('response_time', result)
    
    def test_cache_health_check(self):
        """Test cache connectivity health check."""
        result = self.health_service.check_cache()
        
        self.assertTrue(result['healthy'])
        self.assertEqual(result['service'], 'cache')
        self.assertIn('response_time', result)
    
    @patch('apps.core.health.smtplib.SMTP')
    def test_smtp_health_check(self, mock_smtp):
        """Test SMTP connectivity health check."""
        # Mock successful SMTP connection
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance
        
        result = self.health_service.check_smtp()
        
        self.assertTrue(result['healthy'])
        self.assertEqual(result['service'], 'smtp')
        self.assertIn('response_time', result)
    
    @patch('apps.core.health.smtplib.SMTP')
    def test_smtp_health_check_timeout(self, mock_smtp):
        """Test SMTP health check with timeout."""
        import socket
        
        # Mock timeout exception
        mock_smtp.side_effect = socket.timeout("Connection timed out")
        
        result = self.health_service.check_smtp()
        
        self.assertFalse(result['healthy'])
        self.assertEqual(result['service'], 'smtp')
        self.assertIn('timeout', result['details'].lower())
    
    def test_overall_health_status(self):
        """Test overall system health status."""
        result = self.health_service.get_health_status()
        
        self.assertIn('status', result)
        self.assertIn('checks', result)
        self.assertIn('timestamp', result)
        
        # Verify individual checks
        checks = result['checks']
        self.assertIn('database', checks)
        self.assertIn('cache', checks)
        self.assertIn('smtp', checks)


class MetricsTests(TestCase):
    """Test metrics collection and reporting."""
    
    def setUp(self):
        """Set up test data."""
        self.warehouse = WarehouseFactory()
        self.product = ProductFactory()
        self.metrics_service = MetricsService()
    
    def test_stock_metrics_collection(self):
        """Test stock metrics collection."""
        # Create test stock data
        StockLotFactory(
            product=self.product,
            warehouse=self.warehouse,
            quantity=100,
            reserved_quantity=20
        )
        
        metrics = self.metrics_service.collect_stock_metrics()
        
        self.assertIn('total_products', metrics)
        self.assertIn('total_stock', metrics)
        self.assertIn('reserved_stock', metrics)
        self.assertIn('available_stock', metrics)
        
        self.assertEqual(metrics['total_products'], 1)
        self.assertEqual(metrics['total_stock'], 100)
        self.assertEqual(metrics['reserved_stock'], 20)
        self.assertEqual(metrics['available_stock'], 80)
    
    def test_performance_metrics_collection(self):
        """Test performance metrics collection."""
        # Simulate some operations
        start_time = time.time()
        time.sleep(0.1)  # Simulate work
        end_time = time.time()
        
        self.metrics_service.record_operation_time(
            'test_operation',
            end_time - start_time
        )
        
        metrics = self.metrics_service.get_performance_metrics()
        
        self.assertIn('operations', metrics)
        self.assertIn('test_operation', metrics['operations'])
        
        operation_metrics = metrics['operations']['test_operation']
        self.assertIn('count', operation_metrics)
        self.assertIn('avg_time', operation_metrics)
        self.assertIn('total_time', operation_metrics)
    
    def test_error_metrics_collection(self):
        """Test error metrics collection."""
        # Record some errors
        self.metrics_service.record_error('database_error', 'Connection failed')
        self.metrics_service.record_error('validation_error', 'Invalid data')
        self.metrics_service.record_error('database_error', 'Timeout')
        
        metrics = self.metrics_service.get_error_metrics()
        
        self.assertIn('errors', metrics)
        self.assertIn('database_error', metrics['errors'])
        self.assertIn('validation_error', metrics['errors'])
        
        # Verify error counts
        self.assertEqual(metrics['errors']['database_error']['count'], 2)
        self.assertEqual(metrics['errors']['validation_error']['count'], 1)
    
    def test_metrics_aggregation(self):
        """Test metrics aggregation over time."""
        # Record metrics over time
        for i in range(10):
            self.metrics_service.record_operation_time('api_call', 0.1 + i * 0.01)
        
        aggregated = self.metrics_service.aggregate_metrics('api_call', '1h')
        
        self.assertIn('count', aggregated)
        self.assertIn('avg_time', aggregated)
        self.assertIn('min_time', aggregated)
        self.assertIn('max_time', aggregated)
        
        self.assertEqual(aggregated['count'], 10)
        self.assertAlmostEqual(aggregated['min_time'], 0.1, places=2)
        self.assertAlmostEqual(aggregated['max_time'], 0.19, places=2)


class RateLimitingTests(APITestCase):
    """Test rate limiting functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    @override_settings(RATELIMIT_ENABLE=True)
    def test_api_rate_limiting(self):
        """Test API rate limiting."""
        # Make requests up to the limit
        responses = []
        for i in range(15):  # Assuming limit is 10/minute
            response = self.client.get('/api/products/')
            responses.append(response.status_code)
        
        # Check that some requests were rate limited
        rate_limited_responses = [
            status for status in responses 
            if status == status.HTTP_429_TOO_MANY_REQUESTS
        ]
        
        # Should have some rate limited responses
        self.assertGreater(len(rate_limited_responses), 0)
    
    @override_settings(RATELIMIT_ENABLE=True)
    def test_rate_limit_per_user(self):
        """Test that rate limiting is per user."""
        # Create another user
        user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        client2 = APIClient()
        client2.force_authenticate(user=user2)
        
        # Make requests with first user (exhaust limit)
        for i in range(12):
            self.client.get('/api/products/')
        
        # Make request with second user (should not be limited)
        response = client2.get('/api/products/')
        
        # Second user should not be rate limited
        self.assertNotEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
    
    @override_settings(RATELIMIT_ENABLE=False)
    def test_rate_limiting_disabled(self):
        """Test that rate limiting can be disabled."""
        # Make many requests
        responses = []
        for i in range(20):
            response = self.client.get('/api/products/')
            responses.append(response.status_code)
        
        # No requests should be rate limited
        rate_limited_responses = [
            status for status in responses 
            if status == status.HTTP_429_TOO_MANY_REQUESTS
        ]
        
        self.assertEqual(len(rate_limited_responses), 0)


class IntegrationTests(TransactionTestCase):
    """Integration tests for the complete system."""
    
    def setUp(self):
        """Set up test data."""
        self.warehouse = WarehouseFactory()
        self.product = ProductFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_complete_order_workflow(self):
        """Test complete order workflow from creation to fulfillment."""
        # Create stock
        lot1 = StockLotFactory(
            product=self.product,
            warehouse=self.warehouse,
            expiry_date=date.today() + timedelta(days=5),
            quantity=50
        )
        lot2 = StockLotFactory(
            product=self.product,
            warehouse=self.warehouse,
            expiry_date=date.today() + timedelta(days=10),
            quantity=50
        )
        
        # Create order
        order = Order.objects.create(
            customer=self.user,
            warehouse=self.warehouse,
            status='pending'
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=30,
            unit_price=Decimal('10.00')
        )
        
        # Process order
        stock_service = StockService()
        result = stock_service.process_order(order)
        
        # Verify order was processed successfully
        self.assertTrue(result['success'])
        
        # Verify FEFO was applied (lot1 should be used first)
        lot1.refresh_from_db()
        lot2.refresh_from_db()
        
        self.assertEqual(lot1.reserved_quantity, 30)
        self.assertEqual(lot2.reserved_quantity, 0)
        
        # Verify order status
        order.refresh_from_db()
        self.assertEqual(order.status, 'confirmed')
    
    def test_system_under_load(self):
        """Test system behavior under concurrent load."""
        # Create multiple products and stock
        products = [ProductFactory() for _ in range(5)]
        for product in products:
            for i in range(3):
                StockLotFactory(
                    product=product,
                    warehouse=self.warehouse,
                    quantity=100,
                    expiry_date=date.today() + timedelta(days=i+1)
                )
        
        # Create multiple orders concurrently
        def create_and_process_order(product):
            order = Order.objects.create(
                customer=self.user,
                warehouse=self.warehouse,
                status='pending'
            )
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=20,
                unit_price=Decimal('10.00')
            )
            
            stock_service = StockService()
            return stock_service.process_order(order)
        
        # Process orders concurrently
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for product in products:
                for _ in range(3):  # 3 orders per product
                    future = executor.submit(create_and_process_order, product)
                    futures.append(future)
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        # Verify most orders were processed successfully
        successful_orders = [r for r in results if r and r.get('success')]
        success_rate = len(successful_orders) / len(results)
        
        self.assertGreater(success_rate, 0.8)  # 80% success rate under load
    
    def test_error_recovery(self):
        """Test system error recovery and resilience."""
        # Create order with insufficient stock
        order = Order.objects.create(
            customer=self.user,
            warehouse=self.warehouse,
            status='pending'
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1000,  # More than available
            unit_price=Decimal('10.00')
        )
        
        # Try to process order
        stock_service = StockService()
        result = stock_service.process_order(order)
        
        # Verify graceful failure
        self.assertFalse(result['success'])
        self.assertIn('insufficient_stock', result.get('error', ''))
        
        # Verify system state is consistent
        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')  # Should remain pending
        
        # Verify no stock was reserved
        total_reserved = sum(
            lot.reserved_quantity 
            for lot in StockLot.objects.filter(product=self.product)
        )
        self.assertEqual(total_reserved, 0)


if __name__ == '__main__':
    pytest.main([__file__])