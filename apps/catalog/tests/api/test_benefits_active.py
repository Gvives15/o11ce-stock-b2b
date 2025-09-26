"""
Tests for /catalog/offers endpoint with active benefits filtering.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time
from rest_framework.test import APIClient

from apps.catalog.models import Product, Benefit


class BenefitsActiveAPITest(TestCase):
    """Test suite for active benefits API endpoint."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create test products
        self.product1 = Product.objects.create(
            code="PROD001",
            name="Test Product 1",
            brand="TestBrand",
            category="TestCategory",
            price=Decimal("100.00"),
            unit="UN",
            is_active=True
        )
        
        self.product2 = Product.objects.create(
            code="PROD002",
            name="Test Product 2", 
            brand="TestBrand",
            category="TestCategory",
            price=Decimal("200.00"),
            unit="UN",
            is_active=True
        )
        
        # Set up dates for testing
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        next_month = today + timedelta(days=30)
        last_month = today - timedelta(days=30)
        
        # Active retail benefit (currently valid)
        self.active_retail_benefit = Benefit.objects.create(
            name="Active Retail Discount",
            benefit_type="discount",
            discount_percentage=Decimal("10.00"),
            segment="retail",
            is_active=True,
            valid_from=yesterday,
            valid_to=next_month
        )
        self.active_retail_benefit.products.add(self.product1)
        
        # Active wholesale benefit (currently valid)
        self.active_wholesale_benefit = Benefit.objects.create(
            name="Active Wholesale Discount",
            benefit_type="discount", 
            discount_percentage=Decimal("20.00"),
            segment="wholesale",
            is_active=True,
            valid_from=yesterday,
            valid_to=next_month
        )
        self.active_wholesale_benefit.products.add(self.product1, self.product2)
        
        # Inactive benefit (disabled)
        self.inactive_benefit = Benefit.objects.create(
            name="Inactive Discount",
            benefit_type="discount",
            discount_percentage=Decimal("15.00"),
            segment="retail",
            is_active=False,
            valid_from=yesterday,
            valid_to=next_month
        )
        self.inactive_benefit.products.add(self.product1)
        
        # Expired benefit (past validity period)
        self.expired_benefit = Benefit.objects.create(
            name="Expired Discount",
            benefit_type="discount",
            discount_percentage=Decimal("25.00"),
            segment="retail",
            is_active=True,
            valid_from=last_month,
            valid_to=yesterday
        )
        self.expired_benefit.products.add(self.product1)
        
        # Future benefit (not yet valid)
        self.future_benefit = Benefit.objects.create(
            name="Future Discount",
            benefit_type="discount",
            discount_percentage=Decimal("30.00"),
            segment="retail",
            is_active=True,
            valid_from=tomorrow,
            valid_to=next_month
        )
        self.future_benefit.products.add(self.product1)
        
        # Combo benefit for testing different benefit types
        self.combo_benefit = Benefit.objects.create(
            name="Combo Deal",
            benefit_type="combo",
            combo_quantity=3,
            combo_price=Decimal("250.00"),
            segment="retail",
            is_active=True,
            valid_from=yesterday,
            valid_to=next_month
        )
        self.combo_benefit.products.add(self.product1, self.product2)
    
    def test_list_offers_all_segments(self):
        """Test listing offers without segment filter returns all active benefits."""
        response = self.client.get('/api/v1/catalog/offers')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should return all active benefits (retail, wholesale, combo)
        # Excludes inactive, expired, and future benefits
        expected_count = 3  # active_retail, active_wholesale, combo
        self.assertEqual(len(data), expected_count)
        
        # Verify benefit names are in response
        benefit_names = [benefit['name'] for benefit in data]
        self.assertIn("Active Retail Discount", benefit_names)
        self.assertIn("Active Wholesale Discount", benefit_names)
        self.assertIn("Combo Deal", benefit_names)
        
        # Verify excluded benefits are not in response
        self.assertNotIn("Inactive Discount", benefit_names)
        self.assertNotIn("Expired Discount", benefit_names)
        self.assertNotIn("Future Discount", benefit_names)
    
    def test_list_offers_retail_segment(self):
        """Test listing offers filtered by retail segment."""
        response = self.client.get('/api/v1/catalog/offers?segment=retail')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should return only retail benefits
        expected_count = 2  # active_retail, combo (both are retail segment)
        self.assertEqual(len(data), expected_count)
        
        # Verify all returned benefits are for retail segment
        for benefit in data:
            self.assertEqual(benefit['segment'], 'retail')
        
        # Verify specific benefits
        benefit_names = [benefit['name'] for benefit in data]
        self.assertIn("Active Retail Discount", benefit_names)
        self.assertIn("Combo Deal", benefit_names)
        self.assertNotIn("Active Wholesale Discount", benefit_names)
    
    def test_list_offers_wholesale_segment(self):
        """Test listing offers filtered by wholesale segment."""
        response = self.client.get('/api/v1/catalog/offers?segment=wholesale')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should return only wholesale benefits
        expected_count = 1  # active_wholesale
        self.assertEqual(len(data), expected_count)
        
        # Verify benefit details
        benefit = data[0]
        self.assertEqual(benefit['name'], "Active Wholesale Discount")
        self.assertEqual(benefit['segment'], 'wholesale')
        self.assertEqual(benefit['benefit_type'], 'discount')
        self.assertEqual(Decimal(str(benefit['discount_percentage'])), Decimal("20.00"))
    
    @freeze_time("2024-01-15")
    def test_date_filtering_with_freezegun(self):
        """Test that benefits are filtered correctly by date using freezegun."""
        # Create benefits with specific dates relative to frozen time
        frozen_today = date(2024, 1, 15)
        
        # Valid benefit (should appear)
        valid_benefit = Benefit.objects.create(
            name="Valid on Frozen Date",
            benefit_type="discount",
            discount_percentage=Decimal("12.00"),
            segment="retail",
            is_active=True,
            valid_from=date(2024, 1, 10),
            valid_to=date(2024, 1, 20)
        )
        valid_benefit.products.add(self.product1)
        
        # Expired benefit (should not appear)
        expired_benefit = Benefit.objects.create(
            name="Expired on Frozen Date",
            benefit_type="discount", 
            discount_percentage=Decimal("18.00"),
            segment="retail",
            is_active=True,
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 1, 14)  # Expired yesterday
        )
        expired_benefit.products.add(self.product1)
        
        # Future benefit (should not appear)
        future_benefit = Benefit.objects.create(
            name="Future on Frozen Date",
            benefit_type="discount",
            discount_percentage=Decimal("22.00"),
            segment="retail", 
            is_active=True,
            valid_from=date(2024, 1, 16),  # Starts tomorrow
            valid_to=date(2024, 1, 25)
        )
        future_benefit.products.add(self.product1)
        
        response = self.client.get('/api/v1/catalog/offers?segment=retail')
        data = response.json()
        
        # Find our test benefit
        benefit_names = [benefit['name'] for benefit in data]
        self.assertIn("Valid on Frozen Date", benefit_names)
        self.assertNotIn("Expired on Frozen Date", benefit_names)
        self.assertNotIn("Future on Frozen Date", benefit_names)
    
    def test_inactive_benefits_excluded(self):
        """Test that inactive benefits are excluded from results."""
        response = self.client.get('/api/v1/catalog/offers')
        data = response.json()
        
        # Verify inactive benefit is not in results
        benefit_names = [benefit['name'] for benefit in data]
        self.assertNotIn("Inactive Discount", benefit_names)
        
        # Verify all returned benefits are active
        for benefit in data:
            # Note: is_active is not directly in the API response,
            # but we can verify by checking that inactive benefits don't appear
            pass
    
    def test_expired_benefits_excluded(self):
        """Test that expired benefits are excluded from results."""
        response = self.client.get('/api/v1/catalog/offers')
        data = response.json()
        
        # Verify expired benefit is not in results
        benefit_names = [benefit['name'] for benefit in data]
        self.assertNotIn("Expired Discount", benefit_names)
    
    def test_future_benefits_excluded(self):
        """Test that future benefits are excluded from results."""
        response = self.client.get('/api/v1/catalog/offers')
        data = response.json()
        
        # Verify future benefit is not in results
        benefit_names = [benefit['name'] for benefit in data]
        self.assertNotIn("Future Discount", benefit_names)
    
    def test_invalid_segment_input(self):
        """Test handling of invalid segment parameter."""
        response = self.client.get('/api/v1/catalog/offers?segment=invalid_segment')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should return empty list for invalid segment
        self.assertEqual(len(data), 0)
    
    def test_date_format_validation(self):
        """Test date filter parameter validation."""
        # Test with valid date format
        response = self.client.get('/api/v1/catalog/offers?date_filter=2024-01-15')
        self.assertEqual(response.status_code, 200)
        
        # Test with invalid date format (should not crash, use current date)
        response = self.client.get('/api/v1/catalog/offers?date_filter=invalid-date')
        self.assertEqual(response.status_code, 200)
        
        # Test with empty date filter
        response = self.client.get('/api/v1/catalog/offers?date_filter=')
        self.assertEqual(response.status_code, 200)
    
    def test_benefit_types_representation(self):
        """Test that different benefit types are correctly represented."""
        response = self.client.get('/api/v1/catalog/offers')
        data = response.json()
        
        # Find discount and combo benefits
        discount_benefit = next(
            (b for b in data if b['benefit_type'] == 'discount'), 
            None
        )
        combo_benefit = next(
            (b for b in data if b['benefit_type'] == 'combo'), 
            None
        )
        
        # Verify discount benefit structure
        self.assertIsNotNone(discount_benefit)
        self.assertIn('discount_percentage', discount_benefit)
        self.assertIsNotNone(discount_benefit['discount_percentage'])
        
        # Verify combo benefit structure
        self.assertIsNotNone(combo_benefit)
        self.assertIn('combo_quantity', combo_benefit)
        self.assertIn('combo_price', combo_benefit)
        self.assertIsNotNone(combo_benefit['combo_quantity'])
        self.assertIsNotNone(combo_benefit['combo_price'])
    
    def test_benefit_response_structure(self):
        """Test that benefit response contains all required fields."""
        response = self.client.get('/api/v1/catalog/offers?segment=retail')
        data = response.json()
        
        self.assertTrue(len(data) > 0)
        
        # Check first benefit has required fields
        benefit = data[0]
        required_fields = [
            'id', 'name', 'benefit_type', 'segment', 
            'valid_from', 'valid_to'
        ]
        
        for field in required_fields:
            self.assertIn(field, benefit)
            self.assertIsNotNone(benefit[field])
    
    def test_segment_case_sensitivity(self):
        """Test that segment parameter is case-sensitive."""
        # Test lowercase
        response = self.client.get('/api/v1/catalog/offers?segment=retail')
        retail_count = len(response.json())
        
        # Test uppercase (should return empty since segments are lowercase)
        response = self.client.get('/api/v1/catalog/offers?segment=RETAIL')
        uppercase_count = len(response.json())
        
        # Test mixed case
        response = self.client.get('/api/v1/catalog/offers?segment=Retail')
        mixed_count = len(response.json())
        
        # Only lowercase should return results
        self.assertGreater(retail_count, 0)
        self.assertEqual(uppercase_count, 0)
        self.assertEqual(mixed_count, 0)
    
    @freeze_time("2024-01-15")
    def test_edge_case_validity_boundaries(self):
        """Test benefits at the exact boundaries of validity periods."""
        frozen_today = date(2024, 1, 15)
        
        # Benefit that starts today
        starts_today = Benefit.objects.create(
            name="Starts Today",
            benefit_type="discount",
            discount_percentage=Decimal("5.00"),
            segment="retail",
            is_active=True,
            valid_from=frozen_today,  # Starts exactly today
            valid_to=date(2024, 1, 25)
        )
        starts_today.products.add(self.product1)
        
        # Benefit that ends today
        ends_today = Benefit.objects.create(
            name="Ends Today",
            benefit_type="discount",
            discount_percentage=Decimal("7.00"),
            segment="retail",
            is_active=True,
            valid_from=date(2024, 1, 10),
            valid_to=frozen_today  # Ends exactly today
        )
        ends_today.products.add(self.product1)
        
        response = self.client.get('/api/v1/catalog/offers?segment=retail')
        data = response.json()
        
        benefit_names = [benefit['name'] for benefit in data]
        
        # Both should be included (boundaries are inclusive)
        self.assertIn("Starts Today", benefit_names)
        self.assertIn("Ends Today", benefit_names)