"""Tests unitarios para los servicios de orders."""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from django.core.exceptions import ValidationError

from apps.catalog.models import Product, Benefit
from apps.customers.models import Customer
from apps.orders.models import Order, OrderItem
from apps.orders.services import (
    apply_benefits,
    checkout,
    PricingInfo,
    _round2
)


@pytest.mark.unit
@pytest.mark.django_db
class TestOrdersServices:
    """Tests para los servicios de orders."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.customer_retail = Customer.objects.create(
            name="Retail Customer",
            segment="retail"
        )
        self.customer_wholesale = Customer.objects.create(
            name="Wholesale Customer", 
            segment="wholesale"
        )
        
        self.product = Product.objects.create(
            code="TEST-001",
            name="Test Product",
            price=Decimal("100.00"),
            tax_rate=Decimal("21.00")
        )
        
        # Beneficio activo para mayoristas
        self.benefit = Benefit.objects.create(
            name="Descuento Mayorista",
            type="discount",
            segment="wholesale",
            value=Decimal("10.00"),  # 10%
            active_from=date.today() - timedelta(days=1),
            active_to=date.today() + timedelta(days=30),
            is_active=True
        )
    
    def test_round2_function(self):
        """Test función de redondeo a 2 decimales."""
        assert _round2(Decimal("10.555")) == Decimal("10.56")
        assert _round2(Decimal("10.554")) == Decimal("10.55")
        assert _round2(Decimal("10.00")) == Decimal("10.00")
    
    def test_apply_benefits_retail_no_discount(self):
        """Test que clientes retail no reciben descuentos."""
        pricing = apply_benefits(self.product, self.customer_retail)
        
        assert pricing.unit_base == Decimal("100.00")
        assert pricing.unit_price == Decimal("100.00")
        assert pricing.benefit_payload is None
    
    def test_apply_benefits_wholesale_with_discount(self):
        """Test que clientes mayoristas reciben descuentos."""
        pricing = apply_benefits(self.product, self.customer_wholesale)
        
        assert pricing.unit_base == Decimal("100.00")
        assert pricing.unit_price == Decimal("90.00")  # 100 - 10%
        assert pricing.benefit_payload is not None
        assert pricing.benefit_payload["type"] == "discount"
        assert pricing.benefit_payload["value"] == 10.0
    
    def test_apply_benefits_inactive_benefit(self):
        """Test que beneficios inactivos no se aplican."""
        # Desactivar el beneficio
        self.benefit.is_active = False
        self.benefit.save()
        
        pricing = apply_benefits(self.product, self.customer_wholesale)
        
        assert pricing.unit_base == Decimal("100.00")
        assert pricing.unit_price == Decimal("100.00")
        assert pricing.benefit_payload is None
    
    def test_apply_benefits_expired_benefit(self):
        """Test que beneficios vencidos no se aplican."""
        # Vencer el beneficio
        self.benefit.active_to = date.today() - timedelta(days=1)
        self.benefit.save()
        
        pricing = apply_benefits(self.product, self.customer_wholesale)
        
        assert pricing.unit_base == Decimal("100.00")
        assert pricing.unit_price == Decimal("100.00")
        assert pricing.benefit_payload is None
    
    def test_apply_benefits_best_discount(self):
        """Test que se aplica el mejor descuento disponible."""
        # Crear un segundo beneficio con mayor descuento
        better_benefit = Benefit.objects.create(
            name="Mejor Descuento",
            type="discount",
            segment="wholesale",
            value=Decimal("15.00"),  # 15%
            active_from=date.today() - timedelta(days=1),
            active_to=date.today() + timedelta(days=30),
            is_active=True
        )
        
        pricing = apply_benefits(self.product, self.customer_wholesale)
        
        assert pricing.unit_price == Decimal("85.00")  # 100 - 15%
        assert pricing.benefit_payload["value"] == 15.0


@pytest.mark.unit
@pytest.mark.django_db
class TestCheckoutService:
    """Tests para el servicio de checkout."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.customer = Customer.objects.create(
            name="Test Customer",
            segment="retail"
        )
        
        self.product1 = Product.objects.create(
            code="PROD-001",
            name="Product 1",
            price=Decimal("50.00"),
            tax_rate=Decimal("21.00")
        )
        
        self.product2 = Product.objects.create(
            code="PROD-002", 
            name="Product 2",
            price=Decimal("75.00"),
            tax_rate=Decimal("10.50")
        )
    
    @patch('apps.orders.services.record_exit_fefo')
    @patch('apps.orders.services.Notification')
    @patch('apps.core.metrics.increment_orders_placed')
    def test_checkout_success(self, mock_increment, mock_notification, mock_record_exit):
        """Test checkout exitoso."""
        # Mock para evitar problemas de stock
        mock_record_exit.return_value = []
        
        items = [
            {"product_id": self.product1.id, "qty": "2"},
            {"product_id": self.product2.id, "qty": "1"}
        ]
        
        order = checkout(
            customer_id=self.customer.id,
            items=items,
            delivery_method="pickup"
        )
        
        assert order.id is not None
        assert order.customer == self.customer
        assert order.status == Order.Status.PLACED
        assert order.delivery_method == "pickup"
        
        # Verificar totales
        # Product1: 50 * 2 = 100, tax = 100 * 0.21 = 21
        # Product2: 75 * 1 = 75, tax = 75 * 0.105 = 7.88 (rounded to 7.88)
        expected_subtotal = Decimal("175.00")
        expected_tax = Decimal("28.88")  # 21 + 7.88
        expected_total = expected_subtotal + expected_tax
        
        assert order.subtotal == expected_subtotal
        assert order.tax_total == expected_tax
        assert order.total == expected_total
        
        # Verificar items creados
        order_items = OrderItem.objects.filter(order=order)
        assert order_items.count() == 2
        
        # Verificar llamadas a servicios externos
        assert mock_record_exit.call_count == 2
        mock_notification.objects.create.assert_called_once()
        mock_increment.assert_called_once()
    
    def test_checkout_empty_items(self):
        """Test error con lista de items vacía."""
        with pytest.raises(ValidationError) as exc_info:
            checkout(
                customer_id=self.customer.id,
                items=[],
                delivery_method="pickup"
            )
        
        assert "items no puede estar vacío" in str(exc_info.value)
    
    def test_checkout_invalid_delivery_method(self):
        """Test error con método de entrega inválido."""
        items = [{"product_id": self.product1.id, "qty": "1"}]
        
        with pytest.raises(ValidationError) as exc_info:
            checkout(
                customer_id=self.customer.id,
                items=items,
                delivery_method="invalid"
            )
        
        assert "delivery_method debe ser 'delivery' o 'pickup'" in str(exc_info.value)
    
    def test_checkout_delivery_without_address(self):
        """Test error con delivery sin dirección."""
        items = [{"product_id": self.product1.id, "qty": "1"}]
        
        with pytest.raises(ValidationError) as exc_info:
            checkout(
                customer_id=self.customer.id,
                items=items,
                delivery_method="delivery",
                delivery_address_text=""
            )
        
        assert "delivery_address_text es obligatorio" in str(exc_info.value)
    
    def test_checkout_invalid_delivery_window(self):
        """Test error con ventana de entrega inválida."""
        from datetime import time
        items = [{"product_id": self.product1.id, "qty": "1"}]
        
        with pytest.raises(ValidationError) as exc_info:
            checkout(
                customer_id=self.customer.id,
                items=items,
                delivery_method="pickup",
                delivery_window_from=time(14, 0),
                delivery_window_to=time(10, 0)  # Antes que from
            )
        
        assert "delivery_window_from no puede ser mayor" in str(exc_info.value)
    
    def test_checkout_past_delivery_date(self):
        """Test error con fecha de entrega en el pasado."""
        items = [{"product_id": self.product1.id, "qty": "1"}]
        
        with pytest.raises(ValidationError) as exc_info:
            checkout(
                customer_id=self.customer.id,
                items=items,
                delivery_method="pickup",
                requested_delivery_date=date.today() - timedelta(days=1)
            )
        
        assert "requested_delivery_date debe ser una fecha futura" in str(exc_info.value)
    
    def test_checkout_too_many_items(self):
        """Test error con demasiados items."""
        items = [{"product_id": self.product1.id, "qty": "1"} for _ in range(101)]
        
        with pytest.raises(ValidationError) as exc_info:
            checkout(
                customer_id=self.customer.id,
                items=items,
                delivery_method="pickup"
            )
        
        assert "No se pueden procesar más de 100 items" in str(exc_info.value)
    
    def test_checkout_invalid_qty_zero(self):
        """Test error con cantidad cero."""
        items = [{"product_id": self.product1.id, "qty": "0"}]
        
        with pytest.raises(ValidationError) as exc_info:
            checkout(
                customer_id=self.customer.id,
                items=items,
                delivery_method="pickup"
            )
        
        assert "qty debe ser > 0" in str(exc_info.value)
    
    def test_checkout_invalid_qty_too_large(self):
        """Test error con cantidad demasiado grande."""
        items = [{"product_id": self.product1.id, "qty": "10001"}]
        
        with pytest.raises(ValidationError) as exc_info:
            checkout(
                customer_id=self.customer.id,
                items=items,
                delivery_method="pickup"
            )
        
        assert "qty no puede ser mayor a 10,000" in str(exc_info.value)
    
    def test_checkout_nonexistent_customer(self):
        """Test error con cliente inexistente."""
        items = [{"product_id": self.product1.id, "qty": "1"}]
        
        with pytest.raises(Exception):  # Http404 o similar
            checkout(
                customer_id=99999,
                items=items,
                delivery_method="pickup"
            )
    
    def test_checkout_nonexistent_product(self):
        """Test error con producto inexistente."""
        items = [{"product_id": 99999, "qty": "1"}]
        
        with pytest.raises(Exception):  # Http404 o similar
            checkout(
                customer_id=self.customer.id,
                items=items,
                delivery_method="pickup"
            )
    
    @patch('apps.orders.services.record_exit_fefo')
    @patch('apps.orders.services.Notification')
    @patch('apps.core.metrics.increment_orders_placed')
    def test_checkout_idempotency(self, mock_increment, mock_notification, mock_record_exit):
        """Test idempotencia con client_req_id."""
        # Mock para evitar problemas de stock
        mock_record_exit.return_value = []
        
        items = [{"product_id": self.product1.id, "qty": "1"}]
        client_req_id = "unique-request-123"
        
        # Primera llamada
        order1 = checkout(
            customer_id=self.customer.id,
            items=items,
            delivery_method="pickup",
            client_req_id=client_req_id
        )
        
        # Segunda llamada con mismo client_req_id
        order2 = checkout(
            customer_id=self.customer.id,
            items=items,
            delivery_method="pickup",
            client_req_id=client_req_id
        )
        
        # Debe retornar la misma orden
        assert order1.id == order2.id
        
        # Solo debe haber una orden en la base de datos
        orders_count = Order.objects.filter(client_req_id=client_req_id).count()
        assert orders_count == 1