"""
Tests para el endpoint POST /pos/price-quote.
"""
import pytest
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.catalog.models import Product
from apps.customers.models import Customer
import json


@pytest.mark.django_db
class TestPriceQuoteEndpoint(TestCase):
    """Tests para el endpoint POST /pos/price-quote."""
    
    def setUp(self):
        """Configuración inicial para los tests."""
        self.client = Client()
        
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
    
    def test_price_quote_caso_ejemplo_wholesale(self):
        """Test DoD: caso ejemplo (1×P2 + 5×P1) devuelve total esperado para mayorista."""
        request_data = {
            "customer_id": self.customer_wholesale.id,
            "items": [
                {
                    "product_id": self.product_p1.id,
                    "qty": "5.0",
                    "unit": "package"
                },
                {
                    "product_id": self.product_p2.id,
                    "qty": "1.0", 
                    "unit": "package"
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/price-quote',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verificar estructura de respuesta
        self.assertIn('items', data)
        self.assertIn('combo_discounts', data)
        self.assertIn('subtotal', data)
        self.assertIn('discounts_total', data)
        self.assertIn('total', data)
        
        # Verificar items
        self.assertEqual(len(data['items']), 2)
        
        # Verificar subtotal inicial: (5 × $450) + (1 × $650) = $2900
        self.assertEqual(Decimal(str(data['subtotal'])), Decimal('2900.00'))
        
        # Verificar que hay descuento por segmento (mayorista -8%)
        # y descuento por combo (1×P2 + 5×P1 → -300)
        self.assertGreater(Decimal(str(data['discounts_total'])), Decimal('0'))
        
        # Verificar combo discount
        self.assertEqual(len(data['combo_discounts']), 1)
        combo = data['combo_discounts'][0]
        self.assertEqual(Decimal(str(combo['discount_amount'])), Decimal('300.00'))
        
        # Verificar total según DoD: totales = suma ítems − descuentos
        expected_total = Decimal(str(data['subtotal'])) - Decimal(str(data['discounts_total']))
        self.assertEqual(Decimal(str(data['total'])), expected_total)
        
        # Para mayorista con combo:
        # Subtotal: $2900
        # Descuento segmento: 8% de $2900 = $232
        # Descuento combo: $300
        # Total: $2900 - $232 - $300 = $2368
        self.assertEqual(Decimal(str(data['total'])), Decimal('2368.00'))
    
    def test_price_quote_caso_ejemplo_retail(self):
        """Test con el caso ejemplo del retail: 30 unidades de P1."""
        data = {
            "customer_id": self.customer_retail.id,
            "items": [
                {
                    "product_id": self.product_p1.id,  # P1
                    "qty": "30.0",
                    "unit": "unit"
                }
            ]
        }
        
        response = self.client.post(
            "/api/v1/pos/price-quote",
            data=json.dumps(data),
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        
        # Verificar que devuelve 30.0 unidades (cantidad original)
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(Decimal(result["items"][0]["qty"]), Decimal("30.0"))
        
        # Verificar subtotal: 5 paquetes × $450 = $2250.000
        self.assertEqual(Decimal(result["items"][0]["subtotal"]), Decimal("2250.000"))
        self.assertEqual(Decimal(result["subtotal"]), Decimal("2250.000"))

    def test_price_quote_qty_zero_error(self):
        """Test que qty = 0 devuelve error 400."""
        data = {
            "customer_id": self.customer_retail.id,
            "items": [
                {
                    "product_id": self.product_p1.id,  # P1
                    "qty": "0",
                    "unit": "unit"
                }
            ]
        }
        
        response = self.client.post(
            "/api/v1/pos/price-quote",
            data=json.dumps(data),
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 400)
        result = response.json()
        self.assertIn("detail", result)
        self.assertIn("cantidad debe ser mayor a 0", result["detail"])

    def test_price_quote_too_many_items_error(self):
        """Test que más de 50 items devuelve error 400."""
        # Crear 51 items para superar el límite
        items = []
        for i in range(51):
            items.append({
                "product_id": self.product_p1.id,  # P1
                "qty": "1.0",
                "unit": "unit"
            })
        
        data = {
            "customer_id": self.customer_retail.id,
            "items": items
        }
        
        response = self.client.post(
            "/api/v1/pos/price-quote",
            data=json.dumps(data),
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 400)
        result = response.json()
        self.assertIn("detail", result)
        self.assertIn("Máximo 50 items permitidos", result["detail"])

    def test_price_quote_empty_items_error(self):
        """Test que lista vacía de items devuelve error 400."""
        data = {
            "customer_id": self.customer_retail.id,
            "items": []
        }
        
        response = self.client.post(
            "/api/v1/pos/price-quote",
            data=json.dumps(data),
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 400)
        result = response.json()
        self.assertIn("detail", result)
        self.assertIn("Debe incluir al menos un item", result["detail"])

    def test_price_quote_qty_negative_error(self):
        """Test que qty negativa devuelve error 400."""
        data = {
            "customer_id": self.customer_retail.id,
            "items": [
                {
                    "product_id": self.product_p1.id,  # P1
                    "qty": "-5",
                    "unit": "unit"
                }
            ]
        }
        
        response = self.client.post(
            "/api/v1/pos/price-quote",
            data=json.dumps(data),
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 400)
        result = response.json()
        self.assertIn("detail", result)
        self.assertIn("cantidad debe ser mayor a 0", result["detail"])
    
    def test_price_quote_unit_conversion(self):
        """Test que el endpoint maneja correctamente las unidades y calcula precios."""
        request_data = {
            "customer_id": self.customer_retail.id,
            "items": [
                {
                    "product_id": self.product_p1.id,
                    "qty": "30.0",  # 30 unidades
                    "unit": "unit"
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/price-quote',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verificar que se procesó correctamente
        item = data['items'][0]
        self.assertEqual(Decimal(str(item['qty'])), Decimal('30.0'))  # Mantiene unidades originales
        self.assertEqual(Decimal(str(item['subtotal'])), Decimal('2250.000'))  # 5 paquetes × $450
    
    def test_price_quote_customer_not_found(self):
        """Test error cuando cliente no existe."""
        request_data = {
            "customer_id": 99999,
            "items": [
                {
                    "product_id": self.product_p1.id,
                    "qty": "1.0",
                    "unit": "package"
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/price-quote',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn('Cliente no encontrado', data['detail'])
    
    def test_price_quote_product_not_found(self):
        """Test error cuando producto no existe."""
        request_data = {
            "customer_id": self.customer_retail.id,
            "items": [
                {
                    "product_id": 99999,
                    "qty": "1.0",
                    "unit": "package"
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/price-quote',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn('Producto 99999 no encontrado', data['detail'])
    
    def test_price_quote_invalid_unit(self):
        """Test error con unidad inválida."""
        request_data = {
            "customer_id": self.customer_retail.id,
            "items": [
                {
                    "product_id": self.product_p1.id,
                    "qty": "1.0",
                    "unit": "invalid_unit"
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/price-quote',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('Error en cantidad para producto', data['detail'])
    
    def test_price_quote_empty_items(self):
        """Test con lista de items vacía."""
        request_data = {
            "customer_id": self.customer_retail.id,
            "items": []
        }
        
        response = self.client.post(
            '/api/v1/pos/price-quote',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        
        # Debe devolver error por lista vacía
        self.assertIn('detail', data)
        self.assertIn('Debe incluir al menos un item', data['detail'])
    
    def test_price_quote_response_structure(self):
        """Test estructura completa de respuesta."""
        request_data = {
            "customer_id": self.customer_wholesale.id,
            "items": [
                {
                    "product_id": self.product_p1.id,
                    "qty": "5.0",
                    "unit": "package"
                },
                {
                    "product_id": self.product_p2.id,
                    "qty": "1.0",
                    "unit": "package"
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/pos/price-quote',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verificar estructura de items
        for item in data['items']:
            self.assertIn('product_id', item)
            self.assertIn('name', item)
            self.assertIn('qty', item)
            self.assertIn('unit_price', item)
            self.assertIn('discount_item', item)
            self.assertIn('subtotal', item)
        
        # Verificar estructura de combo_discounts
        for combo in data['combo_discounts']:
            self.assertIn('name', combo)
            self.assertIn('description', combo)
            self.assertIn('discount_amount', combo)
            self.assertIn('items_affected', combo)