"""
Tests for fault tolerance features - Bloque 6.
"""
import pytest
import time
import socket
from unittest.mock import patch, Mock, MagicMock
from django.test import TestCase, override_settings
from django.core.cache import cache
from django.core.mail import get_connection
from django.urls import reverse
from celery import current_app
from celery.exceptions import Retry

from apps.notifications.tasks import send_email_alert, notify_new_order
from apps.stock.tasks import scan_near_expiry, scan_low_stock
from apps.core.cache import fault_tolerant_cache, cached_function
from apps.core.health import check_celery, check_cache, check_smtp


class TestTaskRetryOnSMTPFailure(TestCase):
    """Test that tasks retry automatically when SMTP fails."""
    
    @patch('apps.notifications.tasks.send_mail')
    def test_task_retry_on_smtp_failure(self, mock_send_mail):
        """Test that send_email_alert retries on SMTP failure."""
        # Configure mock to fail first two times, succeed on third
        mock_send_mail.side_effect = [
            Exception("SMTP connection failed"),
            Exception("SMTP timeout"),
            True  # Success on third attempt
        ]
        
        # Execute task
        result = send_email_alert.apply(
            args=['Test Subject', 'Test Message', 'test@example.com'],
            throw=True
        )
        
        # Verify task succeeded after retries
        self.assertEqual(result.status, 'SUCCESS')
        self.assertEqual(mock_send_mail.call_count, 3)
        
        # Verify result contains success status
        task_result = result.result
        self.assertEqual(task_result['status'], 'success')
        self.assertEqual(task_result['recipient'], 'test@example.com')
    
    @patch('apps.notifications.tasks.send_mail')
    def test_task_exhausts_retries_on_persistent_smtp_failure(self, mock_send_mail):
        """Test that task fails after exhausting all retries."""
        # Configure mock to always fail
        mock_send_mail.side_effect = Exception("Persistent SMTP failure")
        
        # Execute task and expect failure
        with self.assertRaises(Exception):
            send_email_alert.apply(
                args=['Test Subject', 'Test Message', 'test@example.com'],
                throw=True
            )
        
        # Verify all retry attempts were made (max_retries + 1 initial attempt)
        self.assertEqual(mock_send_mail.call_count, 4)  # 3 retries + 1 initial
    
    @patch('socket.setdefaulttimeout')
    @patch('apps.notifications.tasks.send_mail')
    def test_smtp_timeout_configuration(self, mock_send_mail, mock_set_timeout):
        """Test that SMTP operations use configured timeouts."""
        mock_send_mail.return_value = True
        
        # Execute task
        send_email_alert.apply(
            args=['Test Subject', 'Test Message', 'test@example.com'],
            throw=True
        )
        
        # Verify timeout was set to 5 seconds
        mock_set_timeout.assert_called_with(5.0)


class TestAPIWithoutRedis(TestCase):
    """Test that API continues to work when Redis is down."""
    
    def setUp(self):
        """Set up test data."""
        from apps.catalog.models import Product
        self.product = Product.objects.create(
            name="Test Product",
            description="Test Description",
            price=10.00,
            is_active=True
        )
    
    @patch('django.core.cache.cache.get')
    @patch('django.core.cache.cache.set')
    def test_api_survives_when_redis_down(self, mock_cache_set, mock_cache_get):
        """Test that API endpoints work when Redis is unavailable."""
        # Simulate Redis being down
        mock_cache_get.side_effect = ConnectionError("Redis connection failed")
        mock_cache_set.side_effect = ConnectionError("Redis connection failed")
        
        # Test product list endpoint (should work without cache)
        response = self.client.get('/api/products/')
        
        # API should still respond successfully
        self.assertEqual(response.status_code, 200)
        
        # Verify cache operations were attempted but failed gracefully
        self.assertTrue(mock_cache_get.called)
    
    def test_fault_tolerant_cache_handles_redis_failure(self):
        """Test that fault-tolerant cache handles Redis failures gracefully."""
        # Test cache operations when Redis is down
        with patch('django.core.cache.cache.get', side_effect=ConnectionError("Redis down")):
            # get() should return default value
            result = fault_tolerant_cache.get('test_key', 'default_value')
            self.assertEqual(result, 'default_value')
        
        with patch('django.core.cache.cache.set', side_effect=ConnectionError("Redis down")):
            # set() should return False but not crash
            result = fault_tolerant_cache.set('test_key', 'test_value')
            self.assertFalse(result)
        
        with patch('django.core.cache.cache.delete', side_effect=ConnectionError("Redis down")):
            # delete() should return False but not crash
            result = fault_tolerant_cache.delete('test_key')
            self.assertFalse(result)
    
    def test_cached_function_decorator_with_redis_failure(self):
        """Test that cached function decorator works when Redis fails."""
        call_count = 0
        
        @cached_function(timeout=300, key_prefix='test')
        def expensive_function():
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"
        
        # Mock Redis failure
        with patch('apps.core.cache.fault_tolerant_cache.get', side_effect=ConnectionError("Redis down")):
            with patch('apps.core.cache.fault_tolerant_cache.set', side_effect=ConnectionError("Redis down")):
                # Function should still work, just without caching
                result1 = expensive_function()
                result2 = expensive_function()
                
                # Both calls should execute (no caching due to Redis failure)
                self.assertEqual(result1, "result_1")
                self.assertEqual(result2, "result_2")
                self.assertEqual(call_count, 2)


class TestHealthChecksCelery(TestCase):
    """Test health checks show Celery status correctly."""
    
    @patch('celery.current_app.control.inspect')
    @patch('kombu.Connection')
    def test_health_ready_shows_celery_ok(self, mock_connection, mock_inspect):
        """Test that health endpoint shows Celery as OK when working."""
        # Mock successful Celery components
        mock_connection.return_value.__enter__.return_value.ensure_connection.return_value = True
        
        mock_inspect_instance = Mock()
        mock_inspect_instance.active.return_value = {'worker1': []}
        mock_inspect_instance.scheduled.return_value = {'worker1': []}
        mock_inspect.return_value = mock_inspect_instance
        
        # Test Celery health check
        result = check_celery()
        
        # Verify Celery is reported as healthy
        self.assertEqual(result['status'], 'healthy')
        self.assertIn('components', result)
        self.assertEqual(result['components']['broker']['status'], 'healthy')
        self.assertEqual(result['components']['workers']['status'], 'healthy')
    
    @patch('celery.current_app.control.inspect')
    @patch('kombu.Connection')
    def test_health_ready_shows_celery_degraded(self, mock_connection, mock_inspect):
        """Test that health endpoint shows Celery as degraded when broker OK but no workers."""
        # Mock broker OK but no workers
        mock_connection.return_value.__enter__.return_value.ensure_connection.return_value = True
        
        mock_inspect_instance = Mock()
        mock_inspect_instance.active.return_value = {}  # No active workers
        mock_inspect_instance.scheduled.return_value = {}
        mock_inspect.return_value = mock_inspect_instance
        
        # Test Celery health check
        result = check_celery()
        
        # Verify Celery is reported as degraded
        self.assertEqual(result['status'], 'degraded')
        self.assertEqual(result['components']['broker']['status'], 'healthy')
        self.assertEqual(result['components']['workers']['status'], 'unhealthy')
    
    @patch('kombu.Connection')
    def test_health_ready_shows_celery_unhealthy(self, mock_connection):
        """Test that health endpoint shows Celery as unhealthy when broker fails."""
        # Mock broker connection failure
        mock_connection.return_value.__enter__.side_effect = ConnectionError("Broker unavailable")
        
        # Test Celery health check
        result = check_celery()
        
        # Verify Celery is reported as unhealthy
        self.assertEqual(result['status'], 'unhealthy')
        self.assertEqual(result['components']['broker']['status'], 'unhealthy')
    
    def test_health_endpoint_integration(self):
        """Test the full health endpoint integration."""
        response = self.client.get('/health/ready/')
        
        # Should return valid JSON response
        self.assertIn(response.status_code, [200, 503])  # OK or Service Unavailable
        
        data = response.json()
        self.assertIn('status', data)
        self.assertIn('checks', data)
        self.assertIn('celery', data['checks'])


class TestScheduledTasksRun(TestCase):
    """Test that scheduled tasks are configured and can run."""
    
    def setUp(self):
        """Set up test data."""
        from apps.catalog.models import Product
        from apps.stock.models import StockLot, Warehouse
        from datetime import date, timedelta
        
        # Create test warehouse
        self.warehouse = Warehouse.objects.create(name="Test Warehouse")
        
        # Create test product
        self.product = Product.objects.create(
            name="Test Product",
            description="Test Description",
            price=10.00,
            is_active=True
        )
        
        # Create stock lot near expiry
        self.near_expiry_lot = StockLot.objects.create(
            product=self.product,
            lot_code="NEAR_EXPIRY",
            expiry_date=date.today() + timedelta(days=3),
            qty_on_hand=50,
            unit_cost=5.00,
            warehouse=self.warehouse
        )
    
    @patch('apps.notifications.tasks.send_email_alert.delay')
    def test_low_stock_scan_scheduled_runs(self, mock_send_alert):
        """Test that low stock scan task can run successfully."""
        # Execute the task
        result = scan_low_stock.apply(args=[5.0], throw=True)  # Threshold of 5 units
        
        # Verify task completed successfully
        self.assertEqual(result.status, 'SUCCESS')
        
        task_result = result.result
        self.assertEqual(task_result['status'], 'success')
        self.assertGreaterEqual(task_result['products_found'], 1)  # Should find our test product
        
        # Verify alert was sent
        self.assertTrue(mock_send_alert.called)
    
    @patch('apps.notifications.tasks.send_email_alert.delay')
    def test_near_expiry_scan_scheduled_runs(self, mock_send_alert):
        """Test that near expiry scan task can run successfully."""
        # Execute the task
        result = scan_near_expiry.apply(args=[7], throw=True)  # 7 days ahead
        
        # Verify task completed successfully
        self.assertEqual(result.status, 'SUCCESS')
        
        task_result = result.result
        self.assertEqual(task_result['status'], 'success')
        self.assertGreaterEqual(task_result['products_found'], 1)  # Should find our test product
        
        # Verify alert was sent
        self.assertTrue(mock_send_alert.called)
    
    def test_celery_beat_schedule_configuration(self):
        """Test that Celery Beat schedules are properly configured."""
        from config.celery import app
        
        # Verify schedules are configured
        beat_schedule = app.conf.beat_schedule
        
        self.assertIn('scan-near-expiry', beat_schedule)
        self.assertIn('scan-low-stock', beat_schedule)
        
        # Verify schedule details
        near_expiry_schedule = beat_schedule['scan-near-expiry']
        self.assertEqual(near_expiry_schedule['task'], 'apps.stock.tasks.scan_near_expiry')
        self.assertIn('schedule', near_expiry_schedule)
        
        low_stock_schedule = beat_schedule['scan-low-stock']
        self.assertEqual(low_stock_schedule['task'], 'apps.stock.tasks.scan_low_stock')
        self.assertIn('schedule', low_stock_schedule)


class TestCacheMetrics(TestCase):
    """Test that cache failures are properly tracked with metrics."""
    
    @patch('apps.core.metrics.increment_counter')
    def test_redis_failures_metric_incremented(self, mock_increment):
        """Test that Redis failures increment the redis_failures_total metric."""
        # Simulate Redis failure
        with patch('django.core.cache.cache.get', side_effect=ConnectionError("Redis connection failed")):
            fault_tolerant_cache.get('test_key')
        
        # Verify metric was incremented
        mock_increment.assert_called_with('redis_failures_total', {
            'operation': 'get',
            'error_type': 'ConnectionError'
        })
    
    @patch('apps.core.metrics.increment_counter')
    def test_cache_hit_miss_metrics(self, mock_increment):
        """Test that cache hits and misses are tracked."""
        call_count = 0
        
        @cached_function(timeout=300, key_prefix='test')
        def test_function():
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"
        
        # First call should be a miss
        result1 = test_function()
        
        # Verify cache miss was recorded
        mock_increment.assert_called_with('cache_misses_total', {'function': 'test_function'})
        
        # Reset mock
        mock_increment.reset_mock()
        
        # Second call should be a hit (if cache is working)
        result2 = test_function()
        
        # Should have recorded either hit or miss
        self.assertTrue(mock_increment.called)


class TestSMTPTimeouts(TestCase):
    """Test SMTP timeout configuration."""
    
    @patch('socket.setdefaulttimeout')
    @patch('django.core.mail.get_connection')
    def test_smtp_health_check_timeout(self, mock_get_connection, mock_set_timeout):
        """Test that SMTP health check uses proper timeout."""
        mock_connection = Mock()
        mock_get_connection.return_value = mock_connection
        
        # Execute SMTP health check
        check_smtp()
        
        # Verify timeout was set to 4 seconds
        mock_set_timeout.assert_called_with(4.0)
        
        # Verify connection was attempted
        mock_connection.open.assert_called_once()
        mock_connection.close.assert_called_once()
    
    @patch('socket.setdefaulttimeout')
    def test_smtp_timeout_in_email_task(self, mock_set_timeout):
        """Test that email tasks use proper SMTP timeout."""
        with patch('apps.notifications.tasks.send_mail', return_value=True):
            # Execute email task
            send_email_alert.apply(
                args=['Test Subject', 'Test Message', 'test@example.com'],
                throw=True
            )
        
        # Verify timeout was set to 5 seconds
        mock_set_timeout.assert_called_with(5.0)


# Integration test to verify the complete fault tolerance system
class TestFaultToleranceIntegration(TestCase):
    """Integration tests for the complete fault tolerance system."""
    
    def test_system_continues_with_multiple_failures(self):
        """Test that system continues to operate with multiple component failures."""
        # Simulate Redis down
        with patch('django.core.cache.cache.get', side_effect=ConnectionError("Redis down")):
            with patch('django.core.cache.cache.set', side_effect=ConnectionError("Redis down")):
                
                # API should still work
                response = self.client.get('/health/live/')
                self.assertEqual(response.status_code, 200)
                
                # Cache operations should fail gracefully
                result = fault_tolerant_cache.get('test_key', 'default')
                self.assertEqual(result, 'default')
                
                # Health check should show degraded but not failed
                cache_health = check_cache()
                self.assertEqual(cache_health['status'], 'degraded')
                self.assertTrue(cache_health['fault_tolerant'])
    
    def test_metrics_tracking_during_failures(self):
        """Test that metrics are properly tracked during various failures."""
        with patch('apps.core.metrics.increment_counter') as mock_increment:
            # Simulate various failures
            with patch('django.core.cache.cache.get', side_effect=ConnectionError("Redis down")):
                fault_tolerant_cache.get('test_key')
            
            with patch('apps.notifications.tasks.send_mail', side_effect=Exception("SMTP down")):
                try:
                    send_email_alert.apply(
                        args=['Test', 'Test', 'test@example.com'],
                        throw=True
                    )
                except:
                    pass
            
            # Verify metrics were recorded
            self.assertTrue(mock_increment.called)
            
            # Check that different failure types were recorded
            call_args_list = [call[0] for call in mock_increment.call_args_list]
            metric_names = [args[0] for args in call_args_list]
            
            self.assertIn('redis_failures_total', metric_names)
            self.assertIn('email_alerts_sent_total', metric_names)