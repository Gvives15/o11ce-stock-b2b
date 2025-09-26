"""Tests for catalog API endpoints."""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.db import transaction
from decimal import Decimal

from apps.catalog.models import Product, Benefit


class TestProductsAPI(TestCase):
    """Test cases for Products API endpoints."""
    
    def setUp(self):
        """Set up test data with clean database."""
        # Clear all existing products to ensure clean state
        Product.objects.all().delete()
        
        self.client = Client()
        
        # Create test products
        self.coca_product = Product.objects.create(
            code="COCA-355",
            name="Coca Cola 355ml",
            price=Decimal("2.50"),
            tax_rate=Decimal("21.00"),
            brand="Coca Cola",
            category="Bebidas",
            is_active=True
        )
        
        self.pepsi_product = Product.objects.create(
            code="PEPSI-500",
            name="Pepsi 500ml",
            price=Decimal("3.00"),
            tax_rate=Decimal("21.00"),
            brand="Pepsi",
            category="Bebidas",
            is_active=True
        )
        
        self.inactive_product = Product.objects.create(
            code="INACTIVE-001",
            name="Inactive Product",
            price=Decimal("1.00"),
            tax_rate=Decimal("21.00"),
            is_active=False
        )
    
    def test_list_products_success(self):
        """Test successful product listing."""
        response = self.client.get("/api/v1/catalog/products")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        
        # Check that active products are returned
        product_codes = [p["code"] for p in data]
        assert "COCA-355" in product_codes
        assert "PEPSI-500" in product_codes
    
    def test_search_products_by_name(self):
        """Test product search by name."""
        # First, let's see what products exist in the database
        all_products = Product.objects.all()
        print(f"DEBUG: Total products in DB: {all_products.count()}")
        for p in all_products:
            print(f"DEBUG: Product: {p.name} ({p.code}) - Active: {p.is_active}")
        
        # Now test the API call
        response = self.client.get("/api/v1/catalog/products?search=coca")
        print(f"DEBUG: Response status: {response.status_code}")
        print(f"DEBUG: Response headers: {dict(response.headers)}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Debug: Let's see what we're getting
        print(f"DEBUG: Response data: {data}")
        print(f"DEBUG: Number of results: {len(data)}")
        for i, item in enumerate(data):
            print(f"DEBUG: Item {i}: {item.get('name', 'NO NAME')} - {item.get('code', 'NO CODE')}")
        
        # The test is expecting 1 result but getting 3
        # Let's check if there are other products with "coca" in the name
        assert len(data) == 1  # Change back to original expectation
        assert data[0]["name"] == "Coca Cola 355ml"
    
    def test_search_products_by_code(self):
        """Test product search by code."""
        response = self.client.get("/api/v1/catalog/products?search=COCA")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["code"] == "COCA-355"
    
    def test_filter_products_by_brand(self):
        """Test product filtering by brand."""
        response = self.client.get("/api/v1/catalog/products?brand=Coca Cola")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["brand"] == "Coca Cola"
    
    def test_filter_products_by_category(self):
        """Test product filtering by category."""
        response = self.client.get("/api/v1/catalog/products?category=Bebidas")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # Both active products are in "Bebidas" category
    
    def test_filter_products_by_active_status(self):
        """Test product filtering by active status."""
        response = self.client.get("/api/v1/catalog/products?is_active=true")
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned products should be active
        for product in data:
            assert product["is_active"] is True
        
        # Inactive product should not be in results
        product_codes = [p["code"] for p in data]
        assert "INACTIVE-001" not in product_codes
    
    def test_products_response_structure(self):
        """Test that products response has correct structure."""
        response = self.client.get("/api/v1/catalog/products")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        
        product = data[0]
        required_fields = [
            "id", "code", "name", "price", "tax_rate", 
            "unit", "brand", "category", "is_active",
            "created_at", "updated_at"
        ]
        
        for field in required_fields:
            assert field in product


@pytest.mark.django_db
class TestOffersAPI:
    """Tests for /offers API endpoint."""
    
    def setup_method(self):
        """Set up test data."""
        self.client = Client()
        today = date.today()
        
        # Active retail benefit
        self.retail_benefit = Benefit.objects.create(
            name="Retail Discount 10%",
            type="discount",
            segment="retail",
            value=Decimal("10.00"),
            active_from=today - timedelta(days=5),
            active_to=today + timedelta(days=5),
            is_active=True
        )
        
        # Active wholesale benefit
        self.wholesale_benefit = Benefit.objects.create(
            name="Wholesale Discount 25%",
            type="discount",
            segment="wholesale",
            value=Decimal("25.00"),
            active_from=today - timedelta(days=10),
            active_to=today + timedelta(days=10),
            is_active=True
        )
        
        # Inactive benefit
        self.inactive_benefit = Benefit.objects.create(
            name="Inactive Discount",
            type="discount",
            segment="retail",
            value=Decimal("15.00"),
            active_from=today - timedelta(days=5),
            active_to=today + timedelta(days=5),
            is_active=False
        )
        
        # Expired benefit
        self.expired_benefit = Benefit.objects.create(
            name="Expired Discount",
            type="discount",
            segment="retail",
            value=Decimal("20.00"),
            active_from=today - timedelta(days=20),
            active_to=today - timedelta(days=10),
            is_active=True
        )
    
    def test_list_offers_success(self):
        """Test successful offers listing."""
        response = self.client.get("/api/v1/catalog/offers")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        
        # Check that active benefits are returned
        benefit_names = [b["name"] for b in data]
        assert "Retail Discount 10%" in benefit_names
        assert "Wholesale Discount 25%" in benefit_names
        assert "Inactive Discount" not in benefit_names
        assert "Expired Discount" not in benefit_names
    
    def test_filter_offers_by_segment_retail(self):
        """Test offers filtering by retail segment."""
        response = self.client.get("/api/v1/catalog/offers?segment=retail")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        
        # All returned benefits should be for retail segment
        for benefit in data:
            assert benefit["segment"] == "retail"
        
        # Should include retail benefit but not wholesale
        benefit_names = [b["name"] for b in data]
        assert "Retail Discount 10%" in benefit_names
        assert "Wholesale Discount 25%" not in benefit_names
    
    def test_filter_offers_by_segment_wholesale(self):
        """Test offers filtering by wholesale segment."""
        response = self.client.get("/api/v1/catalog/offers?segment=wholesale")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        
        # All returned benefits should be for wholesale segment
        for benefit in data:
            assert benefit["segment"] == "wholesale"
        
        # Should include wholesale benefit but not retail
        benefit_names = [b["name"] for b in data]
        assert "Wholesale Discount 25%" in benefit_names
        assert "Retail Discount 10%" not in benefit_names
    
    def test_offers_response_structure(self):
        """Test that offers response has correct structure."""
        response = self.client.get("/api/v1/catalog/offers")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        
        benefit = data[0]
        required_fields = [
            "id", "name", "type", "segment", "value", 
            "combo_spec", "active_from", "active_to", "is_active"
        ]
        
        for field in required_fields:
            assert field in benefit
    
    def test_offers_only_active_today(self):
        """Test that offers endpoint only returns benefits active today."""
        response = self.client.get("/api/v1/catalog/offers")
        
        assert response.status_code == 200
        data = response.json()
        
        today = date.today()
        
        for benefit in data:
            # All benefits should be active
            assert benefit["is_active"] is True
            
            # All benefits should be active today (within date range)
            active_from = date.fromisoformat(benefit["active_from"])
            active_to = date.fromisoformat(benefit["active_to"])
            assert active_from <= today <= active_to