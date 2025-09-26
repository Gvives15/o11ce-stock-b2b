"""
Smoke tests for Celery tasks.
Tests task execution, retry behavior, and integration with Django models.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.core import mail
from django.contrib.auth.models import User
from celery import current_app
from celery.exceptions import Retry

from apps.notifications.tasks import (
    send_email_alert,
    send_low_stock_alert,
    send_near_expiry_alert,
    cleanup_expired_lots
)
from apps.inventory.tasks import (
    update_stock_metrics,
    scan_near_expiry_products,
    scan_low_stock_products
)
from apps.inventory.models import Product, StockLot, Warehouse
from tests.factories import ProductFactory, StockLotFactory, WarehouseFactory
from tests.fixtures import *


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
)
class CeleryTaskSmokeTests(TestCase):
    """Basic smoke tests to ensure tasks can be called and execute."""
    
    def setUp(self):
        """Set up test data."""
        self.warehouse = WarehouseFactory()
        self.product = ProductFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_celery_is_configured_for_tests(self):
        """Verify Celery is properly configured for testing."""
        self.assertTrue(current_app.conf.task_always_eager)
        self.assertTrue(current_app.conf.task_eager_propagates)
    
    def test_send_email_alert_task_executes(self):
        """Test that send_email_alert task can be called and executes."""
        # Clear any existing emails
        mail.outbox = []
        
        # Call the task
        result = send_email_alert.delay(
            subject='Test Alert',
            message='This is a test message',
            recipient_list=['test@example.com']
        )
        
        # Verify task completed
        self.assertTrue(result.successful())
        
        # Verify email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Test Alert')
        self.assertEqual(mail.outbox[0].to, ['test@example.com'])
    
    def test_send_low_stock_alert_task_executes(self):
        """Test that send_low_stock_alert task executes."""
        # Create low stock scenario
        lot = StockLotFactory(
            product=self.product,
            warehouse=self.warehouse,
            quantity=5,  # Low stock
            reserved_quantity=0
        )
        
        # Clear emails
        mail.outbox = []
        
        # Call the task
        result = send_low_stock_alert.delay(
            product_id=self.product.id,
            current_stock=5,
            threshold=10
        )
        
        # Verify task completed
        self.assertTrue(result.successful())
        
        # Verify email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Low Stock Alert', mail.outbox[0].subject)
    
    def test_send_near_expiry_alert_task_executes(self):
        """Test that send_near_expiry_alert task executes."""
        from datetime import date, timedelta
        
        # Create near expiry lot
        expiry_date = date.today() + timedelta(days=2)
        lot = StockLotFactory(
            product=self.product,
            warehouse=self.warehouse,
            expiry_date=expiry_date,
            quantity=10
        )
        
        # Clear emails
        mail.outbox = []
        
        # Call the task
        result = send_near_expiry_alert.delay(
            lot_id=lot.id,
            days_until_expiry=2
        )
        
        # Verify task completed
        self.assertTrue(result.successful())
        
        # Verify email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Near Expiry Alert', mail.outbox[0].subject)
    
    def test_cleanup_expired_lots_task_executes(self):
        """Test that cleanup_expired_lots task executes."""
        from datetime import date, timedelta
        
        # Create expired lot
        expired_date = date.today() - timedelta(days=5)
        expired_lot = StockLotFactory(
            product=self.product,
            warehouse=self.warehouse,
            expiry_date=expired_date,
            quantity=0  # Already consumed
        )
        
        # Call the task
        result = cleanup_expired_lots.delay()
        
        # Verify task completed
        self.assertTrue(result.successful())
        
        # Verify result contains cleanup info
        self.assertIsInstance(result.result, dict)
        self.assertIn('cleaned_lots', result.result)
    
    def test_update_stock_metrics_task_executes(self):
        """Test that update_stock_metrics task executes."""
        # Create some stock data
        StockLotFactory(
            product=self.product,
            warehouse=self.warehouse,
            quantity=100
        )
        
        # Call the task
        result = update_stock_metrics.delay()
        
        # Verify task completed
        self.assertTrue(result.successful())
        
        # Verify result contains metrics
        self.assertIsInstance(result.result, dict)
        self.assertIn('total_products', result.result)
    
    def test_scan_near_expiry_products_task_executes(self):
        """Test that scan_near_expiry_products task executes."""
        from datetime import date, timedelta
        
        # Create near expiry product
        expiry_date = date.today() + timedelta(days=3)
        StockLotFactory(
            product=self.product,
            warehouse=self.warehouse,
            expiry_date=expiry_date,
            quantity=10
        )
        
        # Call the task
        result = scan_near_expiry_products.delay()
        
        # Verify task completed
        self.assertTrue(result.successful())
        
        # Verify result
        self.assertIsInstance(result.result, dict)
        self.assertIn('scanned_products', result.result)
    
    def test_scan_low_stock_products_task_executes(self):
        """Test that scan_low_stock_products task executes."""
        # Create low stock product
        StockLotFactory(
            product=self.product,
            warehouse=self.warehouse,
            quantity=5,  # Below threshold
            reserved_quantity=0
        )
        
        # Call the task
        result = scan_low_stock_products.delay()
        
        # Verify task completed
        self.assertTrue(result.successful())
        
        # Verify result
        self.assertIsInstance(result.result, dict)
        self.assertIn('scanned_products', result.result)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True
)
class CeleryTaskRetryTests(TestCase):
    """Test retry behavior of Celery tasks."""
    
    def setUp(self):
        """Set up test data."""
        self.warehouse = WarehouseFactory()
        self.product = ProductFactory()
    
    @patch('apps.notifications.tasks.send_mail')
    def test_send_email_alert_retry_on_smtp_error(self, mock_send_mail):
        """Test that send_email_alert retries on SMTP errors."""
        import smtplib
        
        # Configure mock to raise SMTP error on first call, succeed on second
        mock_send_mail.side_effect = [
            smtplib.SMTPException("Connection failed"),
            None  # Success on retry
        ]
        
        # Call the task
        result = send_email_alert.delay(
            subject='Test',
            message='Test message',
            recipient_list=['test@example.com']
        )
        
        # Verify task eventually succeeded
        self.assertTrue(result.successful())
        
        # Verify send_mail was called twice (original + retry)
        self.assertEqual(mock_send_mail.call_count, 2)
    
    @patch('apps.notifications.tasks.send_mail')
    def test_send_email_alert_max_retries(self, mock_send_mail):
        """Test that send_email_alert respects max retries."""
        import smtplib
        
        # Configure mock to always fail
        mock_send_mail.side_effect = smtplib.SMTPException("Persistent error")
        
        # Call the task and expect it to fail after retries
        with self.assertRaises(smtplib.SMTPException):
            send_email_alert.delay(
                subject='Test',
                message='Test message',
                recipient_list=['test@example.com']
            )
        
        # Verify max retries were attempted (3 retries + 1 original = 4 calls)
        self.assertEqual(mock_send_mail.call_count, 4)
    
    def test_cleanup_expired_lots_handles_missing_lots(self):
        """Test that cleanup_expired_lots handles missing lots gracefully."""
        # Call task with no expired lots
        result = cleanup_expired_lots.delay()
        
        # Should complete successfully
        self.assertTrue(result.successful())
        
        # Should return empty cleanup result
        self.assertEqual(result.result['cleaned_lots'], 0)
    
    def test_update_stock_metrics_handles_empty_inventory(self):
        """Test that update_stock_metrics handles empty inventory."""
        # Ensure no products exist
        Product.objects.all().delete()
        
        # Call task
        result = update_stock_metrics.delay()
        
        # Should complete successfully
        self.assertTrue(result.successful())
        
        # Should return zero metrics
        self.assertEqual(result.result['total_products'], 0)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True
)
class CeleryTaskIntegrationTests(TestCase):
    """Integration tests for Celery tasks with Django models."""
    
    def setUp(self):
        """Set up test data."""
        self.warehouse = WarehouseFactory()
        self.product = ProductFactory()
    
    def test_task_chain_execution(self):
        """Test that multiple tasks can be chained together."""
        from celery import chain
        
        # Create a chain of tasks
        job = chain(
            update_stock_metrics.s(),
            scan_low_stock_products.s(),
            scan_near_expiry_products.s()
        )
        
        # Execute the chain
        result = job.apply()
        
        # Verify all tasks completed
        self.assertTrue(result.successful())
    
    def test_task_group_execution(self):
        """Test that multiple tasks can be executed in parallel."""
        from celery import group
        
        # Create a group of tasks
        job = group(
            update_stock_metrics.s(),
            scan_low_stock_products.s(),
            scan_near_expiry_products.s()
        )
        
        # Execute the group
        result = job.apply()
        
        # Verify all tasks completed
        for task_result in result:
            self.assertTrue(task_result.successful())
    
    def test_task_with_database_transaction(self):
        """Test that tasks work correctly with database transactions."""
        from django.db import transaction
        
        # Create test data in a transaction
        with transaction.atomic():
            lot = StockLotFactory(
                product=self.product,
                warehouse=self.warehouse,
                quantity=100
            )
        
        # Call task that reads from database
        result = update_stock_metrics.delay()
        
        # Verify task can read the committed data
        self.assertTrue(result.successful())
        self.assertGreater(result.result['total_stock'], 0)
    
    def test_task_error_handling_with_database(self):
        """Test that task errors don't corrupt database state."""
        from django.db import transaction
        
        # Create initial state
        initial_count = StockLot.objects.count()
        
        # Try to call a task that might fail
        try:
            # This should not affect database state
            result = cleanup_expired_lots.delay()
        except Exception:
            pass
        
        # Verify database state is unchanged
        self.assertEqual(StockLot.objects.count(), initial_count)


class CeleryConfigurationTests(TestCase):
    """Test Celery configuration and setup."""
    
    def test_celery_app_is_configured(self):
        """Test that Celery app is properly configured."""
        from config.celery import app
        
        # Verify app exists and is configured
        self.assertIsNotNone(app)
        self.assertEqual(app.main, 'config')
    
    def test_celery_tasks_are_registered(self):
        """Test that all tasks are properly registered."""
        from config.celery import app
        
        # Get registered tasks
        registered_tasks = list(app.tasks.keys())
        
        # Verify our tasks are registered
        expected_tasks = [
            'apps.notifications.tasks.send_email_alert',
            'apps.notifications.tasks.send_low_stock_alert',
            'apps.notifications.tasks.send_near_expiry_alert',
            'apps.notifications.tasks.cleanup_expired_lots',
            'apps.inventory.tasks.update_stock_metrics',
            'apps.inventory.tasks.scan_near_expiry_products',
            'apps.inventory.tasks.scan_low_stock_products',
        ]
        
        for task_name in expected_tasks:
            self.assertIn(task_name, registered_tasks)
    
    def test_celery_beat_schedule_is_configured(self):
        """Test that Celery Beat schedule is properly configured."""
        from config.celery import app
        
        # Verify beat schedule exists
        self.assertIsNotNone(app.conf.beat_schedule)
        
        # Verify expected scheduled tasks
        expected_schedules = [
            'scan-near-expiry',
            'scan-low-stock',
            'cleanup-expired-lots',
            'update-stock-metrics'
        ]
        
        for schedule_name in expected_schedules:
            self.assertIn(schedule_name, app.conf.beat_schedule)
    
    def test_task_routing_is_configured(self):
        """Test that task routing is properly configured."""
        from config.celery import app
        
        # Verify task routes exist
        self.assertIsNotNone(app.conf.task_routes)
        
        # Test a specific route
        routes = app.conf.task_routes
        self.assertIn('apps.notifications.tasks.*', routes)
        self.assertEqual(routes['apps.notifications.tasks.*']['queue'], 'notifications')


if __name__ == '__main__':
    pytest.main([__file__])