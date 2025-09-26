"""
Tests unitarios para los servicios de pricing del catálogo.
"""
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.contrib.auth.models import User

from apps.catalog.models import Product
from apps.customers.models import Customer
from apps.catalog.pricing import (
    PricingItem,
    ComboDiscount,
    PriceQuote,
    apply_segment_discount,
    apply_combo_discounts,
    price_quote
)


@pytest.mark.unit
@pytest.mark.django_db
class TestPricingItem:
    """Tests para la clase PricingItem."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.product = Product.objects.create(
            code="TEST-001",
            name="Test Product",
            price=Decimal("100.00"),
            tax_rate=Decimal("21.00")
        )
    
    def test_pricing_item_creation_with_defaults(self):
        """Test creación de PricingItem con valores por defecto."""
        item = PricingItem(product=self.product, quantity=2)
        
        assert item.product == self.product
        assert item.quantity == 2
        assert item.unit_price == Decimal("100.00")
        assert item.subtotal == Decimal("200.00")
    
    def test_pricing_item_creation_with_custom_values(self):
        """Test creación de PricingItem con valores personalizados."""
        item = PricingItem(
            product=self.product,
            quantity=3,
            unit_price=Decimal("90.00"),
            subtotal=Decimal("270.00")
        )
        
        assert item.unit_price == Decimal("90.00")
        assert item.subtotal == Decimal("270.00")


@pytest.mark.unit
@pytest.mark.django_db
class TestSegmentDiscount:
    """Tests para descuentos por segmento."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.p1_product = Product.objects.create(
            code="P1-001",
            name="P1 Product",
            price=Decimal("100.00"),
            tax_rate=Decimal("21.00")
        )
        self.p2_product = Product.objects.create(
            code="P2-001",
            name="P2 Product",
            price=Decimal("200.00"),
            tax_rate=Decimal("21.00")
        )
        self.other_product = Product.objects.create(
            code="OTHER-001",
            name="Other Product",
            price=Decimal("50.00"),
            tax_rate=Decimal("21.00")
        )
        
        self.wholesale_customer = Customer.objects.create(
            name="Wholesale Customer",
            segment="wholesale"
        )
        self.retail_customer = Customer.objects.create(
            name="Retail Customer",
            segment="retail"
        )
    
    def test_apply_segment_discount_wholesale_p1_p2(self):
        """Test aplicación de descuento por segmento mayorista en productos P1 y P2."""
        items = [
            PricingItem(product=self.p1_product, quantity=2),  # 200.00
            PricingItem(product=self.p2_product, quantity=1),  # 200.00
            PricingItem(product=self.other_product, quantity=1)  # 50.00 (no descuento)
        ]
        
        discount = apply_segment_discount(items, self.wholesale_customer)
        
        # 8% de descuento en P1 y P2: (200 + 200) * 0.08 = 32.00
        assert discount == Decimal("32.00")
        
        # Verificar que los precios se actualizaron
        assert items[0].unit_price == Decimal("92.00")  # 100 - 8%
        assert items[0].subtotal == Decimal("184.00")   # 92 * 2
        assert items[1].unit_price == Decimal("184.00") # 200 - 8%
        assert items[1].subtotal == Decimal("184.00")   # 184 * 1
        assert items[2].unit_price == Decimal("50.00")  # Sin cambio
        assert items[2].subtotal == Decimal("50.00")    # Sin cambio
    
    def test_apply_segment_discount_retail_no_discount(self):
        """Test que clientes retail no reciben descuento por segmento."""
        items = [
            PricingItem(product=self.p1_product, quantity=2),
            PricingItem(product=self.p2_product, quantity=1)
        ]
        
        discount = apply_segment_discount(items, self.retail_customer)
        
        assert discount == Decimal("0.00")
        
        # Verificar que los precios no cambiaron
        assert items[0].unit_price == Decimal("100.00")
        assert items[0].subtotal == Decimal("200.00")
        assert items[1].unit_price == Decimal("200.00")
        assert items[1].subtotal == Decimal("200.00")
    
    def test_apply_segment_discount_no_p1_p2_products(self):
        """Test que productos que no son P1 o P2 no reciben descuento."""
        items = [
            PricingItem(product=self.other_product, quantity=5)
        ]
        
        discount = apply_segment_discount(items, self.wholesale_customer)
        
        assert discount == Decimal("0.00")
        assert items[0].unit_price == Decimal("50.00")
        assert items[0].subtotal == Decimal("250.00")


@pytest.mark.unit
@pytest.mark.django_db
class TestComboDiscounts:
    """Tests para descuentos por combo."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.p1_product = Product.objects.create(
            code="P1-001",
            name="P1 Product",
            price=Decimal("100.00"),
            tax_rate=Decimal("21.00")
        )
        self.p2_product = Product.objects.create(
            code="P2-001",
            name="P2 Product",
            price=Decimal("200.00"),
            tax_rate=Decimal("21.00")
        )
        self.other_product = Product.objects.create(
            code="OTHER-001",
            name="Other Product",
            price=Decimal("50.00"),
            tax_rate=Decimal("21.00")
        )
    
    def test_apply_combo_discounts_valid_combo(self):
        """Test aplicación de descuento por combo válido (1×P2 + 5×P1)."""
        items = [
            PricingItem(product=self.p1_product, quantity=5),  # 500.00
            PricingItem(product=self.p2_product, quantity=1)   # 200.00
        ]
        
        combo_discounts = apply_combo_discounts(items)
        
        assert len(combo_discounts) == 1
        combo = combo_discounts[0]
        assert combo.name == "Combo P1+P2"
        assert combo.discount_amount == Decimal("300.00")
        assert "P1-001" in combo.items_affected
        assert "P2-001" in combo.items_affected
        
        # Verificar que se aplicó el descuento proporcionalmente
        total_original = Decimal("700.00")  # 500 + 200
        expected_total_after_discount = total_original - Decimal("300.00")
        actual_total = sum(item.subtotal for item in items)
        assert actual_total == expected_total_after_discount
    
    def test_apply_combo_discounts_multiple_combos(self):
        """Test aplicación de múltiples combos."""
        items = [
            PricingItem(product=self.p1_product, quantity=10),  # 1000.00
            PricingItem(product=self.p2_product, quantity=2)    # 400.00
        ]
        
        combo_discounts = apply_combo_discounts(items)
        
        assert len(combo_discounts) == 1
        combo = combo_discounts[0]
        # Puede aplicar 2 combos: min(10//5, 2//1) = 2
        assert combo.discount_amount == Decimal("600.00")  # 300 * 2
        assert "2x" in combo.description
    
    def test_apply_combo_discounts_insufficient_p1(self):
        """Test que no se aplica combo si no hay suficientes P1."""
        items = [
            PricingItem(product=self.p1_product, quantity=3),  # Solo 3 P1
            PricingItem(product=self.p2_product, quantity=1)
        ]
        
        combo_discounts = apply_combo_discounts(items)
        
        assert len(combo_discounts) == 0
    
    def test_apply_combo_discounts_insufficient_p2(self):
        """Test que no se aplica combo si no hay suficientes P2."""
        items = [
            PricingItem(product=self.p1_product, quantity=5),
            # Sin P2
        ]
        
        combo_discounts = apply_combo_discounts(items)
        
        assert len(combo_discounts) == 0
    
    def test_apply_combo_discounts_no_p1_p2_products(self):
        """Test que no se aplica combo si no hay productos P1 o P2."""
        items = [
            PricingItem(product=self.other_product, quantity=10)
        ]
        
        combo_discounts = apply_combo_discounts(items)
        
        assert len(combo_discounts) == 0


@pytest.mark.unit
@pytest.mark.django_db
class TestPriceQuote:
    """Tests para la función price_quote completa."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.p1_product = Product.objects.create(
            code="P1-001",
            name="P1 Product",
            price=Decimal("100.00"),
            tax_rate=Decimal("21.00")
        )
        self.p2_product = Product.objects.create(
            code="P2-001",
            name="P2 Product",
            price=Decimal("200.00"),
            tax_rate=Decimal("21.00")
        )
        
        self.wholesale_customer = Customer.objects.create(
            name="Wholesale Customer",
            segment="wholesale"
        )
        self.retail_customer = Customer.objects.create(
            name="Retail Customer",
            segment="retail"
        )
    
    def test_price_quote_wholesale_with_combo(self):
        """Test cotización completa para mayorista con combo."""
        items = [
            {'product_id': self.p1_product.id, 'quantity': 5},
            {'product_id': self.p2_product.id, 'quantity': 1}
        ]
        
        quote = price_quote(self.wholesale_customer, items)
        
        # Subtotal inicial: 500 + 200 = 700
        assert quote.subtotal == Decimal("700.00")
        
        # Descuento por segmento: 8% de 700 = 56
        assert quote.segment_discount_amount == Decimal("56.00")
        
        # Descuento por combo: 300
        assert quote.total_combo_discount == Decimal("300.00")
        assert len(quote.combo_discounts) == 1
        
        # Total final: 700 - 56 (segmento) - 300 (combo) = 344
        assert quote.total == Decimal("344.00")
    
    def test_price_quote_retail_no_discounts(self):
        """Test cotización para cliente retail sin descuentos."""
        items = [
            {'product_id': self.p1_product.id, 'quantity': 2},
            {'product_id': self.p2_product.id, 'quantity': 1}
        ]
        
        quote = price_quote(self.retail_customer, items)
        
        # Subtotal: 200 + 200 = 400
        assert quote.subtotal == Decimal("400.00")
        assert quote.segment_discount_amount == Decimal("0.00")
        assert quote.total_combo_discount == Decimal("0.00")
        assert quote.total == Decimal("400.00")
    
    def test_price_quote_nonexistent_product(self):
        """Test cotización con producto inexistente."""
        items = [
            {'product_id': 99999, 'quantity': 1},  # Producto inexistente
            {'product_id': self.p1_product.id, 'quantity': 2}
        ]
        
        quote = price_quote(self.retail_customer, items)
        
        # Solo debe incluir el producto existente
        assert len(quote.items) == 1
        assert quote.items[0].product == self.p1_product
        assert quote.subtotal == Decimal("200.00")
        assert quote.total == Decimal("200.00")
    
    def test_price_quote_empty_items(self):
        """Test cotización con lista vacía de items."""
        items = []
        
        quote = price_quote(self.retail_customer, items)
        
        assert len(quote.items) == 0
        assert quote.subtotal == Decimal("0.00")
        assert quote.segment_discount_amount == Decimal("0.00")
        assert quote.total_combo_discount == Decimal("0.00")
        assert quote.total == Decimal("0.00")