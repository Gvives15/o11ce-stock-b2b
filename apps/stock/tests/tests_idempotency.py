"""Tests for stock API idempotency functionality."""

import json
import uuid
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from apps.catalog.models import Product
from apps.stock.models import Warehouse, StockLot, Movement
from apps.stock.models_idempotency import StockIdempotencyKey
from apps.stock.idempotency_service import IdempotencyService

User = get_user_model()


class StockIdempotencyTestCase(TestCase):
    """Test cases for stock API idempotency functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Authenticate user
        self.client.force_login(self.user)
        
        # Create product
        self.product = Product.objects.create(
            code='TEST-001',
            name='Test Product',
            price=Decimal('10.00'),
            unit='unit'
        )
        
        # Create warehouse
        self.warehouse = Warehouse.objects.create(
            name='Test Warehouse'
        )

    def test_missing_idempotency_key_entry(self):
        """Test that entry endpoint returns 400 when idempotency key is missing."""
        payload = {
            "product_id": self.product.id,
            "lot_code": "LOT-001",
            "expiry_date": "2024-12-31",
            "qty": "10.000",
            "unit_cost": "5.00",
            "warehouse_id": self.warehouse.id,
            "reason": "Initial stock"
        }
        
        response = self.client.post(
            '/api/v1/stock/entry',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(response_data['error'], 'MISSING_IDEMPOTENCY_KEY')

    def test_missing_idempotency_key_exit(self):
        """Test that exit endpoint returns 400 when idempotency key is missing."""
        # Create initial stock
        StockLot.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            lot_code="LOT-001",
            expiry_date=date.today() + timedelta(days=30),
            qty_on_hand=Decimal('20.000'),
            unit_cost=Decimal('5.00')
        )
        
        payload = {
            "product_id": self.product.id,
            "qty_total": "5.000",  # Changed from "qty" to "qty_total"
            "warehouse_id": self.warehouse.id,
            "reason": "Sale"
        }
        
        response = self.client.post(
            '/api/v1/stock/exit',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(response_data['error'], 'MISSING_IDEMPOTENCY_KEY')

    def test_entry_idempotency_duplicate_request(self):
        """Test that duplicate entry requests with same idempotency key return cached response."""
        payload = {
            "product_id": self.product.id,
            "lot_code": "LOT-001",
            "expiry_date": "2024-12-31",
            "qty": "10.000",
            "unit_cost": "5.00",
            "warehouse_id": self.warehouse.id,
            "reason": "Initial stock"
        }
        
        headers = {'HTTP_IDEMPOTENCY_KEY': 'test-key-123'}
        
        # First request
        response1 = self.client.post(
            '/api/v1/stock/entry',
            data=payload,
            content_type='application/json',
            **headers
        )
        
        self.assertEqual(response1.status_code, 201)
        
        # Second request with same key should return cached response
        response2 = self.client.post(
            '/api/v1/stock/entry',
            data=payload,
            content_type='application/json',
            **headers
        )
        
        self.assertEqual(response2.status_code, 201)
        
        # Compare responses - entry endpoint doesn't have total_qty field
        response1_data = response1.json()
        response2_data = response2.json()
        
        # Normalize decimal values for comparison
        if 'new_qty_on_hand' in response1_data:
            response1_data['new_qty_on_hand'] = float(response1_data['new_qty_on_hand'])
            response2_data['new_qty_on_hand'] = float(response2_data['new_qty_on_hand'])
        
        self.assertEqual(response1_data, response2_data)
        
        # Verify only one movement was created
        movements = Movement.objects.filter(product=self.product)
        self.assertEqual(movements.count(), 1)

    def test_exit_idempotency_duplicate_request(self):
        """Test that duplicate exit requests with same idempotency key return cached response."""
        # Create initial stock
        StockLot.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            lot_code="LOT-001",
            expiry_date=date.today() + timedelta(days=30),
            qty_on_hand=Decimal('20.000'),
            unit_cost=Decimal('5.00')
        )
        
        payload = {
            "product_id": self.product.id,
            "qty_total": "5.000",  # Changed from "qty" to "qty_total"
            "warehouse_id": self.warehouse.id,
            "reason": "Sale"
        }
        
        headers = {'HTTP_IDEMPOTENCY_KEY': 'test-exit-key-123'}
        
        # First request
        response1 = self.client.post(
            '/api/v1/stock/exit',
            data=payload,
            content_type='application/json',
            **headers
        )
        
        self.assertEqual(response1.status_code, 201)
        
        # Second request with same key should return cached response
        response2 = self.client.post(
            '/api/v1/stock/exit',
            data=payload,
            content_type='application/json',
            **headers
        )
        
        self.assertEqual(response2.status_code, 201)
        
        # Compare responses ignoring decimal formatting differences
        response1_data = response1.json()
        response2_data = response2.json()
        
        # Normalize decimal values for comparison
        if 'total_qty' in response1_data:
            response1_data['total_qty'] = str(Decimal(response1_data['total_qty']))
            response2_data['total_qty'] = str(Decimal(response2_data['total_qty']))
        
        if 'movements' in response1_data:
            for movement in response1_data['movements']:
                if 'qty_taken' in movement:
                    movement['qty_taken'] = str(Decimal(movement['qty_taken']))
                if 'unit_cost' in movement:
                    movement['unit_cost'] = str(Decimal(movement['unit_cost']))
            
            for movement in response2_data['movements']:
                if 'qty_taken' in movement:
                    movement['qty_taken'] = str(Decimal(movement['qty_taken']))
                if 'unit_cost' in movement:
                    movement['unit_cost'] = str(Decimal(movement['unit_cost']))
        
        self.assertEqual(response1_data, response2_data)
        
        # Verify only one exit movement was created
        exit_movements = Movement.objects.filter(
            product=self.product,
            type='exit'  # Changed to lowercase to match the actual value
        )
        self.assertEqual(exit_movements.count(), 1)

    def test_idempotency_different_request_data_same_key(self):
        """Test that same key with different request data raises validation error."""
        idempotency_key = 'test-key-456'
        
        payload1 = {
            "product_id": self.product.id,
            "lot_code": "LOT-001",
            "expiry_date": "2024-12-31",
            "qty": "10.000",
            "unit_cost": "5.00",
            "warehouse_id": self.warehouse.id,
            "reason": "Initial stock"
        }
        
        headers1 = {'HTTP_IDEMPOTENCY_KEY': idempotency_key}
        
        response1 = self.client.post(
            '/api/v1/stock/entry',
            data=payload1,
            content_type='application/json',
            **headers1
        )
        
        self.assertEqual(response1.status_code, 201)
        
        # Different payload with same key
        payload2 = {
            "product_id": self.product.id,
            "lot_code": "LOT-002",  # Different lot code
            "expiry_date": "2024-12-31",
            "qty": "20.000",  # Different quantity
            "unit_cost": "5.00",
            "warehouse_id": self.warehouse.id,
            "reason": "Initial stock"
        }
        
        headers2 = {'HTTP_IDEMPOTENCY_KEY': idempotency_key}
        
        response2 = self.client.post(
            '/api/v1/stock/entry',
            data=payload2,
            content_type='application/json',
            **headers2
        )
        
        self.assertEqual(response2.status_code, 400)
        response2_data = response2.json()
        self.assertEqual(response2_data['error'], 'IDEMPOTENCY_ERROR')

    def test_idempotency_error_response_cached(self):
        """Test that error responses are also cached for idempotency."""
        idempotency_key = 'test-error-key-789'
        payload = {
            "product_id": 99999,  # Non-existent product
            "lot_code": "LOT-001",
            "expiry_date": "2024-12-31",
            "qty": "10.000",
            "unit_cost": "5.00",
            "warehouse_id": self.warehouse.id,
            "reason": "Initial stock"
        }
        
        headers = {'HTTP_IDEMPOTENCY_KEY': idempotency_key}
        
        # First request (should fail)
        response1 = self.client.post(
            '/api/v1/stock/entry',
            data=payload,
            content_type='application/json',
            **headers
        )
        
        self.assertEqual(response1.status_code, 404)
        
        # Second request with same key (should return cached error)
        response2 = self.client.post(
            '/api/v1/stock/entry',
            data=payload,
            content_type='application/json',
            **headers
        )
        
        self.assertEqual(response2.status_code, 404)
        self.assertEqual(response1.json(), response2.json())
        
        # Verify idempotency key was stored
        self.assertTrue(
            StockIdempotencyKey.objects.filter(key=idempotency_key).exists()
        )

    def test_cleanup_expired_keys(self):
        """Test cleanup of expired idempotency keys."""
        from django.utils import timezone
        from datetime import timedelta
        
        # Create expired key
        expired_key = StockIdempotencyKey.objects.create(
            key='expired-key',
            operation_type='entry',
            request_hash='test-hash',
            response_data={'test': 'data'},
            status_code=201,
            created_by=self.user,
            expires_at=timezone.now() - timedelta(hours=1)  # Expired 1 hour ago
        )
        
        # Create non-expired key
        valid_key = StockIdempotencyKey.objects.create(
            key='valid-key',
            operation_type='entry',
            request_hash='test-hash-2',
            response_data={'test': 'data2'},
            status_code=201,
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=1)  # Expires in 1 hour
        )
        
        # Verify both keys exist
        self.assertEqual(StockIdempotencyKey.objects.count(), 2)
        
        # Run cleanup
        from apps.stock.idempotency_service import IdempotencyService
        IdempotencyService.cleanup_expired_keys()
        
        # Verify only valid key remains
        self.assertEqual(StockIdempotencyKey.objects.count(), 1)
        self.assertTrue(StockIdempotencyKey.objects.filter(key='valid-key').exists())
        self.assertFalse(StockIdempotencyKey.objects.filter(key='expired-key').exists())