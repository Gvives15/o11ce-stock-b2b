"""
Tests para verificar que las métricas de pricing se incrementan correctamente.
"""
import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from apps.catalog.models import Product, Benefit
from apps.catalog.utils import calculate_final_price
from apps.catalog.pricing import apply_combo_discounts, price_quote
from apps.core.metrics import (
    pricing_calculations_total,
    pricing_errors_total,
    pricing_calculation_duration_seconds
)


class PricingMetricsTestCase(TestCase):
    """Test case para verificar métricas de pricing."""
    
    def setUp(self):
        """Configurar datos de prueba."""
        # Crear productos de prueba
        self.product1 = Product.objects.create(
            code='P001',
            name='Producto Test 1',
            price=Decimal('100.00'),
            tax_rate=Decimal('21.00')
        )
        
        self.product2 = Product.objects.create(
            code='P002',
            name='Producto Test 2',
            price=Decimal('50.00'),
            tax_rate=Decimal('21.00')
        )
        
        # Crear beneficio de descuento para wholesale
        self.wholesale_benefit = Benefit.objects.create(
            name='Descuento Mayorista',
            type='discount',
            value=Decimal('8.0'),
            segment='wholesale',
            active_from=timezone.now().date(),
            active_to=timezone.now().date() + timedelta(days=365)
        )
    
    @patch('apps.catalog.utils.increment_pricing_calculation')
    @patch('apps.catalog.utils.observe_pricing_duration')
    def test_calculate_final_price_metrics(self, mock_observe_duration, mock_increment_calc):
        """Test que calculate_final_price incrementa las métricas correctamente."""
        # Ejecutar cálculo de precio final
        result = calculate_final_price(self.product1, 'wholesale')
        
        # Verificar que se llamaron las métricas
        mock_increment_calc.assert_called()
        mock_observe_duration.assert_called()
        
        # Verificar los parámetros de las llamadas
        calls = mock_increment_calc.call_args_list
        self.assertTrue(len(calls) >= 1)
        
        # Primera llamada debe ser para final_price
        first_call = calls[0][1]  # kwargs
        self.assertEqual(first_call['segment'], 'wholesale')
        self.assertEqual(first_call['calculation_type'], 'final_price')
        
        # Verificar duración
        duration_call = mock_observe_duration.call_args[1]
        self.assertEqual(duration_call['segment'], 'wholesale')
        self.assertEqual(duration_call['calculation_type'], 'final_price')
        self.assertIsInstance(duration_call['duration_seconds'], float)
    
    @patch('apps.catalog.utils.increment_pricing_error')
    @patch('apps.catalog.utils.get_active_benefits')
    def test_calculate_final_price_error_metrics(self, mock_get_benefits, mock_increment_error):
        """Test que los errores en calculate_final_price incrementan métricas de error."""
        # Simular error en get_active_benefits
        mock_get_benefits.side_effect = Exception("Database error")
        
        # Ejecutar cálculo (debe manejar el error)
        result = calculate_final_price(self.product1, 'wholesale')
        
        # Verificar que se incrementó el contador de errores
        mock_increment_error.assert_called_once()
        
        error_call = mock_increment_error.call_args[1]
        self.assertEqual(error_call['segment'], 'wholesale')
        self.assertEqual(error_call['error_type'], 'calculation_error')
        
        # Debe devolver precio base en caso de error
        self.assertEqual(result, self.product1.price)
    
    @patch('apps.catalog.pricing.increment_pricing_calculation')
    @patch('apps.catalog.pricing.observe_pricing_duration')
    def test_apply_combo_discounts_metrics(self, mock_observe_duration, mock_increment_calc):
        """Test que apply_combo_discounts incrementa las métricas correctamente."""
        products = [self.product1, self.product2]
        
        # Ejecutar cálculo de combo
        result = apply_combo_discounts(products, 'retail')
        
        # Verificar que se llamaron las métricas
        mock_increment_calc.assert_called()
        mock_observe_duration.assert_called()
        
        # Verificar parámetros
        calc_call = mock_increment_calc.call_args[1]
        self.assertEqual(calc_call['segment'], 'retail')
        self.assertEqual(calc_call['calculation_type'], 'combo_discount')
        self.assertEqual(calc_call['product_category'], 'combo')
        
        duration_call = mock_observe_duration.call_args[1]
        self.assertEqual(duration_call['segment'], 'retail')
        self.assertEqual(duration_call['calculation_type'], 'combo_discount')
    
    @patch('apps.catalog.pricing.increment_pricing_error')
    @patch('apps.catalog.pricing.calculate_final_price')
    def test_apply_combo_discounts_error_metrics(self, mock_calc_price, mock_increment_error):
        """Test que los errores en apply_combo_discounts incrementan métricas de error."""
        # Simular error en calculate_final_price
        mock_calc_price.side_effect = Exception("Calculation error")
        
        result = apply_combo_discounts([self.product1], 'retail')
        
        # Verificar que se incrementó el contador de errores
        mock_increment_error.assert_called_once()
        
        error_call = mock_increment_error.call_args[1]
        self.assertEqual(error_call['segment'], 'retail')
        self.assertEqual(error_call['error_type'], 'combo_calculation_error')
        self.assertEqual(error_call['product_category'], 'combo')
    
    @patch('apps.catalog.pricing.increment_pricing_calculation')
    @patch('apps.catalog.pricing.observe_pricing_duration')
    def test_price_quote_metrics(self, mock_observe_duration, mock_increment_calc):
        """Test que price_quote incrementa las métricas correctamente."""
        product_codes = ['P001', 'P002']
        quantities = [2, 1]
        
        # Ejecutar cotización
        result = price_quote(product_codes, 'wholesale', quantities)
        
        # Verificar que se llamaron las métricas
        mock_increment_calc.assert_called()
        mock_observe_duration.assert_called()
        
        # Verificar múltiples llamadas (quote + success)
        calls = mock_increment_calc.call_args_list
        self.assertTrue(len(calls) >= 2)
        
        # Primera llamada debe ser para price_quote
        first_call = calls[0][1]
        self.assertEqual(first_call['segment'], 'wholesale')
        self.assertEqual(first_call['calculation_type'], 'price_quote')
        
        # Última llamada debe ser para quote_success
        last_call = calls[-1][1]
        self.assertEqual(last_call['calculation_type'], 'quote_success')
    
    @patch('apps.catalog.pricing.increment_pricing_error')
    def test_price_quote_error_metrics(self, mock_increment_error):
        """Test que los errores en price_quote incrementan métricas de error."""
        # Intentar cotizar productos inexistentes
        result = price_quote(['NONEXISTENT'], 'retail')
        
        # Verificar que se incrementó el contador de errores
        mock_increment_error.assert_called_once()
        
        error_call = mock_increment_error.call_args[1]
        self.assertEqual(error_call['segment'], 'retail')
        self.assertEqual(error_call['error_type'], 'quote_error')
        self.assertEqual(error_call['product_category'], 'quote')
    
    def test_pricing_metrics_integration(self):
        """Test de integración para verificar que las métricas funcionan end-to-end."""
        # Ejecutar operaciones de pricing sin mocks
        result1 = calculate_final_price(self.product1, 'wholesale')
        result2 = apply_combo_discounts([self.product1, self.product2], 'retail')
        result3 = price_quote(['P001'], 'wholesale', [1])
        
        # Verificar que las funciones se ejecutan sin errores
        self.assertIsInstance(result1, Decimal)
        self.assertIn('final_total', result2)
        self.assertIn('total_amount', result3)
    
    @patch('apps.catalog.utils.increment_pricing_calculation')
    def test_metrics_with_different_segments(self, mock_increment_calc):
        """Test que las métricas se registran correctamente para diferentes segmentos."""
        segments = ['retail', 'wholesale', 'unknown']
        
        for segment in segments:
            calculate_final_price(self.product1, segment)
            
            # Verificar que se llamó con el segmento correcto
            mock_increment_calc.assert_called()
            call_args = mock_increment_calc.call_args[1]
            self.assertEqual(call_args['segment'], segment)
            
            # Reset mock for next iteration
            mock_increment_calc.reset_mock()
    
    @patch('apps.catalog.utils.increment_pricing_calculation')
    def test_metrics_with_product_categories(self, mock_increment_calc):
        """Test que las métricas incluyen categorías de productos cuando están disponibles."""
        # Crear producto con categoría si el modelo lo soporta
        try:
            product_with_category = Product.objects.create(
                code='P003',
                name='Producto con Categoría',
                price=Decimal('75.00'),
                tax_rate=Decimal('21.00'),
                category='electronics'
            )
            
            calculate_final_price(product_with_category, 'retail')
            
            call_args = mock_increment_calc.call_args[1]
            self.assertEqual(call_args['product_category'], 'electronics')
            
        except TypeError:
            # Si el modelo Product no tiene campo category, usar valor por defecto
            calculate_final_price(self.product1, 'retail')
            
            call_args = mock_increment_calc.call_args[1]
            self.assertEqual(call_args['product_category'], 'general')