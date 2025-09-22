"""
Tests para el motor de beneficios (pricing service).
"""
import pytest
from decimal import Decimal
from django.test import TestCase
from apps.catalog.models import Product
from apps.customers.models import Customer
from apps.catalog.pricing import (
    PricingItem, 
    apply_segment_discount, 
    apply_combo_discounts, 
    price_quote
)


@pytest.mark.django_db
class TestPricingService(TestCase):
    """Tests para el servicio de pricing con motor de beneficios."""
    
    def setUp(self):
        """Configuración inicial para los tests."""
        # Crear productos P1 y P2 según especificación
        self.product_p1 = Product.objects.create(
            code="P1-GALLETITAS",
            name="Galletitas Dulces Pack x6",
            brand="Arcor",
            unit="package",
            category="Dulces",
            price=Decimal("450.00"),
            pack_size=6
        )
        
        self.product_p2 = Product.objects.create(
            code="P2-MERMELADA",
            name="Mermelada de Frutilla 454g",
            brand="Arcor",
            unit="package",
            category="Dulces",
            price=Decimal("650.00"),
            pack_size=10
        )
        
        # Crear producto que no es P1/P2
        self.product_other = Product.objects.create(
            code="OTHER-PRODUCT",
            name="Producto Otro",
            brand="Test",
            unit="unit",
            category="Test",
            price=Decimal("100.00")
        )
        
        # Crear clientes
        self.customer_wholesale = Customer.objects.create(
            name="Cliente Mayorista",
            segment="wholesale",
            email="mayorista@test.com"
        )
        
        self.customer_retail = Customer.objects.create(
            name="Cliente Minorista",
            segment="retail",
            email="retail@test.com"
        )
    
    def test_apply_segment_discount_wholesale_p1_p2(self):
        """Test DoD: mayorista aplica -8% a P1/P2."""
        items = [
            PricingItem(product=self.product_p1, quantity=2),  # $450 x 2 = $900
            PricingItem(product=self.product_p2, quantity=1),  # $650 x 1 = $650
        ]
        
        # Subtotal inicial: $900 + $650 = $1550
        initial_subtotal = sum(item.subtotal for item in items)
        self.assertEqual(initial_subtotal, Decimal('1550.00'))
        
        # Aplicar descuento mayorista
        discount_amount = apply_segment_discount(items, self.customer_wholesale)
        
        # Descuento esperado: 8% de $1550 = $124.00
        expected_discount = Decimal('124.00')
        self.assertEqual(discount_amount, expected_discount)
        
        # Verificar que los precios se actualizaron
        # P1: $450 - 8% = $414.00
        self.assertEqual(items[0].unit_price, Decimal('414.00'))
        self.assertEqual(items[0].subtotal, Decimal('828.00'))  # $414 x 2
        
        # P2: $650 - 8% = $598.00
        self.assertEqual(items[1].unit_price, Decimal('598.00'))
        self.assertEqual(items[1].subtotal, Decimal('598.00'))  # $598 x 1
    
    def test_apply_segment_discount_retail_no_discount(self):
        """Test que retail no recibe descuento por segmento."""
        items = [
            PricingItem(product=self.product_p1, quantity=1),
            PricingItem(product=self.product_p2, quantity=1),
        ]
        
        original_p1_price = items[0].unit_price
        original_p2_price = items[1].unit_price
        
        discount_amount = apply_segment_discount(items, self.customer_retail)
        
        # No debe haber descuento
        self.assertEqual(discount_amount, Decimal('0.00'))
        
        # Precios deben mantenerse iguales
        self.assertEqual(items[0].unit_price, original_p1_price)
        self.assertEqual(items[1].unit_price, original_p2_price)
    
    def test_apply_segment_discount_wholesale_other_products(self):
        """Test que mayorista no recibe descuento en productos que no son P1/P2."""
        items = [
            PricingItem(product=self.product_other, quantity=2),
        ]
        
        original_price = items[0].unit_price
        discount_amount = apply_segment_discount(items, self.customer_wholesale)
        
        # No debe haber descuento para productos que no son P1/P2
        self.assertEqual(discount_amount, Decimal('0.00'))
        self.assertEqual(items[0].unit_price, original_price)
    
    def test_apply_combo_discounts_p1_p2_combo(self):
        """Test DoD: combo 1×P2 + 5×P1 → -300."""
        items = [
            PricingItem(product=self.product_p1, quantity=5),  # 5 P1
            PricingItem(product=self.product_p2, quantity=1),  # 1 P2
        ]
        
        # Subtotal inicial: ($450 x 5) + ($650 x 1) = $2250 + $650 = $2900
        initial_subtotal = sum(item.subtotal for item in items)
        self.assertEqual(initial_subtotal, Decimal('2900.00'))
        
        combo_discounts = apply_combo_discounts(items)
        
        # Debe haber 1 combo aplicado
        self.assertEqual(len(combo_discounts), 1)
        
        combo = combo_discounts[0]
        self.assertEqual(combo.name, "Combo P1+P2")
        self.assertEqual(combo.discount_amount, Decimal('300.00'))
        self.assertIn("P1-GALLETITAS", combo.items_affected)
        self.assertIn("P2-MERMELADA", combo.items_affected)
        
        # Verificar que el subtotal se redujo
        final_subtotal = sum(item.subtotal for item in items)
        self.assertEqual(final_subtotal, Decimal('2600.00'))  # $2900 - $300
    
    def test_apply_combo_discounts_multiple_combos(self):
        """Test combo múltiple: 2×P2 + 10×P1 → -600."""
        items = [
            PricingItem(product=self.product_p1, quantity=10),  # 10 P1
            PricingItem(product=self.product_p2, quantity=2),   # 2 P2
        ]
        
        combo_discounts = apply_combo_discounts(items)
        
        # Debe haber 1 combo con descuento doble
        self.assertEqual(len(combo_discounts), 1)
        
        combo = combo_discounts[0]
        self.assertEqual(combo.discount_amount, Decimal('600.00'))  # 2 combos × $300
        self.assertIn("2x:", combo.description)
    
    def test_apply_combo_discounts_insufficient_items(self):
        """Test que no se aplique combo si no hay suficientes items."""
        items = [
            PricingItem(product=self.product_p1, quantity=3),  # Solo 3 P1 (necesita 5)
            PricingItem(product=self.product_p2, quantity=1),  # 1 P2
        ]
        
        combo_discounts = apply_combo_discounts(items)
        
        # No debe haber combos aplicados
        self.assertEqual(len(combo_discounts), 0)
    
    def test_price_quote_complete_wholesale(self):
        """Test completo de price_quote para cliente mayorista con combo."""
        items_data = [
            {'product_id': self.product_p1.id, 'quantity': 5},
            {'product_id': self.product_p2.id, 'quantity': 1},
        ]
        
        quote = price_quote(self.customer_wholesale, items_data)
        
        # Verificar estructura del quote
        self.assertEqual(len(quote.items), 2)
        self.assertEqual(quote.subtotal, Decimal('2900.00'))  # Subtotal inicial
        
        # Verificar descuento por segmento (8% de $2900 = $232.00)
        self.assertEqual(quote.segment_discount_amount, Decimal('232.00'))
        
        # Verificar descuento por combo
        self.assertEqual(len(quote.combo_discounts), 1)
        self.assertEqual(quote.total_combo_discount, Decimal('300.00'))
        
        # Total final: $2900 - $232 (segmento) - $300 (combo) = $2368
        # Pero el combo se aplica después del descuento por segmento
        # Subtotal después de segmento: $2900 - $232 = $2668
        # Total después de combo: $2668 - $300 = $2368
        expected_total = Decimal('2368.00')
        self.assertEqual(quote.total, expected_total)
    
    def test_price_quote_retail_no_segment_discount(self):
        """Test price_quote para cliente retail (sin descuento por segmento)."""
        items_data = [
            {'product_id': self.product_p1.id, 'quantity': 5},
            {'product_id': self.product_p2.id, 'quantity': 1},
        ]
        
        quote = price_quote(self.customer_retail, items_data)
        
        # No debe haber descuento por segmento
        self.assertEqual(quote.segment_discount_amount, Decimal('0.00'))
        
        # Debe haber descuento por combo
        self.assertEqual(quote.total_combo_discount, Decimal('300.00'))
        
        # Total: $2900 - $300 (combo) = $2600
        self.assertEqual(quote.total, Decimal('2600.00'))
    
    def test_price_quote_nonexistent_product(self):
        """Test que price_quote ignore productos que no existen."""
        items_data = [
            {'product_id': self.product_p1.id, 'quantity': 1},
            {'product_id': 99999, 'quantity': 1},  # Producto inexistente
        ]
        
        quote = price_quote(self.customer_retail, items_data)
        
        # Solo debe procesar el producto existente
        self.assertEqual(len(quote.items), 1)
        self.assertEqual(quote.items[0].product.code, "P1-GALLETITAS")