"""Tests for catalog utility functions."""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from apps.catalog.utils import apply_discount, get_active_benefits
from apps.catalog.models import Benefit


class TestApplyDiscount:
    """Tests for apply_discount helper function."""
    
    def test_apply_discount_success(self):
        """Test successful discount application."""
        price = Decimal("100.00")
        discount = Decimal("10.00")
        result = apply_discount(price, discount)
        
        assert result == Decimal("90.00")
        assert isinstance(result, Decimal)
    
    def test_apply_discount_rounding(self):
        """Test discount with rounding to 2 decimals."""
        price = Decimal("33.33")
        discount = Decimal("10.00")
        result = apply_discount(price, discount)
        
        # 33.33 - (33.33 * 0.10) = 33.33 - 3.333 = 29.997 -> 30.00
        assert result == Decimal("30.00")
    
    def test_apply_discount_zero_discount(self):
        """Test discount with 0% discount."""
        price = Decimal("50.00")
        discount = Decimal("0.00")
        result = apply_discount(price, discount)
        
        assert result == Decimal("50.00")
    
    def test_apply_discount_full_discount(self):
        """Test discount with 100% discount."""
        price = Decimal("25.00")
        discount = Decimal("100.00")
        result = apply_discount(price, discount)
        
        assert result == Decimal("0.00")
    
    def test_apply_discount_invalid_price_zero(self):
        """Test that price cannot be zero."""
        with pytest.raises(ValueError, match="El precio debe ser mayor a 0"):
            apply_discount(Decimal("0.00"), Decimal("10.00"))
    
    def test_apply_discount_invalid_price_negative(self):
        """Test that price cannot be negative."""
        with pytest.raises(ValueError, match="El precio debe ser mayor a 0"):
            apply_discount(Decimal("-10.00"), Decimal("10.00"))
    
    def test_apply_discount_invalid_percentage_negative(self):
        """Test that discount percentage cannot be negative."""
        with pytest.raises(ValueError, match="El porcentaje debe estar entre 0 y 100"):
            apply_discount(Decimal("100.00"), Decimal("-5.00"))
    
    def test_apply_discount_invalid_percentage_over_100(self):
        """Test that discount percentage cannot exceed 100."""
        with pytest.raises(ValueError, match="El porcentaje debe estar entre 0 y 100"):
            apply_discount(Decimal("100.00"), Decimal("150.00"))


@pytest.mark.django_db
class TestGetActiveBenefits:
    """Tests for get_active_benefits helper function."""
    
    def setup_method(self):
        """Set up test data."""
        today = date.today()
        
        # Active retail benefit
        self.retail_benefit = Benefit.objects.create(
            name="Retail Discount",
            type="discount",
            segment="retail",
            value=Decimal("10.00"),
            active_from=today - timedelta(days=5),
            active_to=today + timedelta(days=5),
            is_active=True
        )
        
        # Active wholesale benefit
        self.wholesale_benefit = Benefit.objects.create(
            name="Wholesale Discount",
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
        
        # Future benefit
        self.future_benefit = Benefit.objects.create(
            name="Future Discount",
            type="discount",
            segment="retail",
            value=Decimal("30.00"),
            active_from=today + timedelta(days=10),
            active_to=today + timedelta(days=20),
            is_active=True
        )
    
    def test_get_active_benefits_all(self):
        """Test getting all active benefits."""
        benefits = get_active_benefits()
        benefit_names = [b.name for b in benefits]
        
        assert len(benefits) == 2
        assert "Retail Discount" in benefit_names
        assert "Wholesale Discount" in benefit_names
        assert "Inactive Discount" not in benefit_names
        assert "Expired Discount" not in benefit_names
        assert "Future Discount" not in benefit_names
    
    def test_get_active_benefits_by_segment_retail(self):
        """Test getting active benefits for retail segment."""
        benefits = get_active_benefits(segment="retail")
        benefit_names = [b.name for b in benefits]
        
        assert len(benefits) == 1
        assert "Retail Discount" in benefit_names
        assert "Wholesale Discount" not in benefit_names
    
    def test_get_active_benefits_by_segment_wholesale(self):
        """Test getting active benefits for wholesale segment."""
        benefits = get_active_benefits(segment="wholesale")
        benefit_names = [b.name for b in benefits]
        
        assert len(benefits) == 1
        assert "Wholesale Discount" in benefit_names
        assert "Retail Discount" not in benefit_names
    
    def test_get_active_benefits_by_date_past(self):
        """Test getting active benefits for a past date."""
        past_date = date.today() - timedelta(days=15)
        benefits = get_active_benefits(filter_date=past_date)
        benefit_names = [b.name for b in benefits]
        
        assert len(benefits) == 1
        assert "Expired Discount" in benefit_names
    
    def test_get_active_benefits_by_date_future(self):
        """Test getting active benefits for a future date."""
        future_date = date.today() + timedelta(days=15)
        benefits = get_active_benefits(filter_date=future_date)
        benefit_names = [b.name for b in benefits]
        
        assert len(benefits) == 1
        assert "Future Discount" in benefit_names
    
    def test_get_active_benefits_empty_result(self):
        """Test getting benefits when none match criteria."""
        benefits = get_active_benefits(segment="nonexistent")
        assert len(benefits) == 0