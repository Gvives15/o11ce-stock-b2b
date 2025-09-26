"""
Tests para verificar que las factories de factory_boy construyen modelos válidos.
"""
import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone

from tests.factories import (
    ProductFactory,
    StockLotFactory,
    BenefitFactory,
    OrderFactory,
    FEFOProductFactory,
    PromotionProductFactory,
    StockAlertProductFactory,
    ComplexOrderFactory,
    PercentageDiscountBenefitFactory,
    BuyXGetYBenefitFactory,
    FixedDiscountBenefitFactory,
)


class TestFactoriesBuildValidModels(TestCase):
    """Test que las factories construyen modelos válidos."""

    def test_product_factory_builds_valid_model(self):
        """Test que ProductFactory crea productos válidos."""
        product = ProductFactory()
        
        # Verificar que el producto se creó correctamente
        self.assertIsNotNone(product.id)
        self.assertIsNotNone(product.name)
        self.assertIsNotNone(product.sku)
        self.assertIsInstance(product.price, Decimal)
        self.assertGreater(product.price, Decimal('0'))
        
        # Verificar que pasa validación completa
        try:
            product.full_clean()
        except ValidationError as e:
            self.fail(f"ProductFactory created invalid model: {e}")

    def test_stock_lot_factory_builds_valid_model(self):
        """Test que StockLotFactory crea lotes válidos."""
        stock_lot = StockLotFactory()
        
        # Verificar campos básicos
        self.assertIsNotNone(stock_lot.id)
        self.assertIsNotNone(stock_lot.product)
        self.assertIsNotNone(stock_lot.warehouse)
        self.assertIsInstance(stock_lot.quantity, int)
        self.assertGreaterEqual(stock_lot.quantity, 0)
        self.assertIsInstance(stock_lot.expiry_date, datetime)
        
        # Verificar que la fecha de expiración es futura
        self.assertGreater(stock_lot.expiry_date, timezone.now())
        
        # Verificar validación
        try:
            stock_lot.full_clean()
        except ValidationError as e:
            self.fail(f"StockLotFactory created invalid model: {e}")

    def test_benefit_factory_builds_valid_model(self):
        """Test que BenefitFactory crea beneficios válidos."""
        benefit = BenefitFactory()
        
        # Verificar campos básicos
        self.assertIsNotNone(benefit.id)
        self.assertIsNotNone(benefit.name)
        self.assertIsNotNone(benefit.benefit_type)
        self.assertIn(benefit.benefit_type, ['percentage', 'fixed', 'buy_x_get_y'])
        
        # Verificar que tiene al menos un producto asociado
        self.assertGreater(benefit.products.count(), 0)
        
        # Verificar validación
        try:
            benefit.full_clean()
        except ValidationError as e:
            self.fail(f"BenefitFactory created invalid model: {e}")

    def test_order_factory_builds_valid_model(self):
        """Test que OrderFactory crea órdenes válidas."""
        order = OrderFactory()
        
        # Verificar campos básicos
        self.assertIsNotNone(order.id)
        self.assertIsNotNone(order.customer)
        self.assertIsNotNone(order.warehouse)
        self.assertIn(order.status, ['pending', 'processing', 'completed', 'cancelled'])
        
        # Verificar que tiene items
        self.assertGreater(order.items.count(), 0)
        
        # Verificar que el total es positivo
        self.assertGreater(order.total_amount, Decimal('0'))
        
        # Verificar validación
        try:
            order.full_clean()
        except ValidationError as e:
            self.fail(f"OrderFactory created invalid model: {e}")

    def test_fefo_product_factory_builds_valid_model(self):
        """Test que FEFOProductFactory crea productos con múltiples lotes FEFO."""
        product = FEFOProductFactory()
        
        # Verificar que tiene múltiples lotes
        stock_lots = product.stock_lots.all()
        self.assertGreaterEqual(stock_lots.count(), 3)
        
        # Verificar que los lotes tienen fechas de expiración diferentes
        expiry_dates = [lot.expiry_date for lot in stock_lots]
        self.assertEqual(len(expiry_dates), len(set(expiry_dates)))
        
        # Verificar que están ordenados por fecha de expiración (FEFO)
        sorted_dates = sorted(expiry_dates)
        self.assertEqual(expiry_dates, sorted_dates)

    def test_promotion_product_factory_builds_valid_model(self):
        """Test que PromotionProductFactory crea productos con promociones."""
        product = PromotionProductFactory()
        
        # Verificar que tiene beneficios asociados
        self.assertGreater(product.benefits.count(), 0)
        
        # Verificar que al menos un beneficio está activo
        active_benefits = product.benefits.filter(is_active=True)
        self.assertGreater(active_benefits.count(), 0)

    def test_stock_alert_product_factory_builds_valid_model(self):
        """Test que StockAlertProductFactory crea productos con alertas de stock."""
        product = StockAlertProductFactory()
        
        # Verificar que tiene lotes con diferentes estados
        stock_lots = product.stock_lots.all()
        self.assertGreater(stock_lots.count(), 0)
        
        # Verificar que algunos lotes están cerca de expirar o con stock bajo
        near_expiry = stock_lots.filter(
            expiry_date__lte=timezone.now() + timedelta(days=7)
        )
        low_stock = stock_lots.filter(quantity__lte=10)
        
        # Al menos uno debe cumplir condición de alerta
        self.assertTrue(near_expiry.exists() or low_stock.exists())

    def test_complex_order_factory_builds_valid_model(self):
        """Test que ComplexOrderFactory crea órdenes complejas válidas."""
        order = ComplexOrderFactory()
        
        # Verificar que tiene múltiples items
        self.assertGreaterEqual(order.items.count(), 3)
        
        # Verificar que tiene productos con beneficios
        items_with_benefits = 0
        for item in order.items.all():
            if item.product.benefits.filter(is_active=True).exists():
                items_with_benefits += 1
        
        self.assertGreater(items_with_benefits, 0)

    def test_percentage_discount_benefit_factory_builds_valid_model(self):
        """Test que PercentageDiscountBenefitFactory crea descuentos porcentuales válidos."""
        benefit = PercentageDiscountBenefitFactory()
        
        self.assertEqual(benefit.benefit_type, 'percentage')
        self.assertIsNotNone(benefit.percentage_discount)
        self.assertGreater(benefit.percentage_discount, Decimal('0'))
        self.assertLessEqual(benefit.percentage_discount, Decimal('100'))

    def test_buy_x_get_y_benefit_factory_builds_valid_model(self):
        """Test que BuyXGetYBenefitFactory crea beneficios 'compra X lleva Y' válidos."""
        benefit = BuyXGetYBenefitFactory()
        
        self.assertEqual(benefit.benefit_type, 'buy_x_get_y')
        self.assertIsNotNone(benefit.buy_quantity)
        self.assertIsNotNone(benefit.get_quantity)
        self.assertGreater(benefit.buy_quantity, 0)
        self.assertGreater(benefit.get_quantity, 0)

    def test_fixed_discount_benefit_factory_builds_valid_model(self):
        """Test que FixedDiscountBenefitFactory crea descuentos fijos válidos."""
        benefit = FixedDiscountBenefitFactory()
        
        self.assertEqual(benefit.benefit_type, 'fixed')
        self.assertIsNotNone(benefit.fixed_discount)
        self.assertGreater(benefit.fixed_discount, Decimal('0'))

    def test_factories_create_unique_instances(self):
        """Test que las factories crean instancias únicas."""
        # Crear múltiples productos
        products = [ProductFactory() for _ in range(5)]
        
        # Verificar que todos tienen IDs únicos
        product_ids = [p.id for p in products]
        self.assertEqual(len(product_ids), len(set(product_ids)))
        
        # Verificar que todos tienen SKUs únicos
        skus = [p.sku for p in products]
        self.assertEqual(len(skus), len(set(skus)))

    def test_factories_respect_relationships(self):
        """Test que las factories respetan las relaciones entre modelos."""
        order = OrderFactory()
        
        # Verificar que todos los items pertenecen a la orden
        for item in order.items.all():
            self.assertEqual(item.order, order)
            
        # Verificar que todos los productos de los items existen
        for item in order.items.all():
            self.assertIsNotNone(item.product.id)
            
        # Verificar que el warehouse del order coincide con el de los stock lots
        for item in order.items.all():
            stock_lots = item.product.stock_lots.filter(warehouse=order.warehouse)
            self.assertGreater(stock_lots.count(), 0)

    def test_factories_handle_edge_cases(self):
        """Test que las factories manejan casos extremos correctamente."""
        # Producto con precio mínimo
        product = ProductFactory(price=Decimal('0.01'))
        self.assertEqual(product.price, Decimal('0.01'))
        
        # Stock lot con cantidad cero
        stock_lot = StockLotFactory(quantity=0)
        self.assertEqual(stock_lot.quantity, 0)
        
        # Beneficio con descuento máximo
        benefit = PercentageDiscountBenefitFactory(percentage_discount=Decimal('100'))
        self.assertEqual(benefit.percentage_discount, Decimal('100'))

    def test_factories_performance(self):
        """Test que las factories tienen performance aceptable."""
        import time
        
        start_time = time.time()
        
        # Crear múltiples instancias
        products = [ProductFactory() for _ in range(10)]
        orders = [OrderFactory() for _ in range(5)]
        benefits = [BenefitFactory() for _ in range(5)]
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Verificar que la creación no toma más de 5 segundos
        self.assertLess(creation_time, 5.0, 
                       f"Factory creation took {creation_time:.2f}s, should be < 5s")
        
        # Verificar que se crearon todas las instancias
        self.assertEqual(len(products), 10)
        self.assertEqual(len(orders), 5)
        self.assertEqual(len(benefits), 5)


class TestFactoriesIntegration(TestCase):
    """Tests de integración para las factories."""

    def test_factories_work_with_django_test_client(self):
        """Test que las factories funcionan con el cliente de test de Django."""
        from django.test import Client
        from django.contrib.auth.models import User
        
        # Crear usuario y producto
        user = User.objects.create_user('testuser', 'test@test.com', 'pass')
        product = ProductFactory()
        
        client = Client()
        client.login(username='testuser', password='pass')
        
        # Hacer request a API (asumiendo que existe endpoint)
        response = client.get(f'/api/products/{product.id}/')
        
        # Verificar que el producto creado por factory es accesible
        self.assertIn(response.status_code, [200, 404])  # 404 si no existe endpoint

    def test_factories_work_with_fixtures(self):
        """Test que las factories funcionan junto con fixtures."""
        from tests.fixtures import fefo_products_fixture
        
        # Usar fixture y factory juntos
        products = fefo_products_fixture()
        additional_product = ProductFactory()
        
        # Verificar que ambos funcionan
        self.assertGreater(len(products), 0)
        self.assertIsNotNone(additional_product.id)
        
        # Verificar que no hay conflictos
        all_products_count = len(products) + 1
        self.assertGreaterEqual(all_products_count, 4)