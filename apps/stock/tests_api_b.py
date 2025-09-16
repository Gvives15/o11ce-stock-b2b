"""
Tests para el Bloque B - API de opciones de lote (GET).
Tests API-B1, API-B2, API-B3 según DoD.
"""

from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from ninja.testing import TestClient

from apps.catalog.models import Product
from apps.stock.models import StockLot, Warehouse
from apps.stock.api import router


class LotOptionsAPITestCase(TestCase):
    """Tests para el endpoint GET /api/stock/lots/options"""
    
    def setUp(self):
        """Configuración inicial para los tests"""
        self.client = TestClient(router)
        
        # Crear producto de prueba
        self.product = Product.objects.create(
            code="PROD001",
            name="Producto Test",
            brand="Test Brand",
            price=Decimal("100.00")  # Campo requerido
        )
        
        # Crear warehouse
        self.warehouse = Warehouse.objects.create(
            name="Almacén Principal"
        )
        
        # Crear lotes de prueba con diferentes fechas de vencimiento
        today = date.today()
        
        # Lote A - vence en 10 días (más próximo a vencer - FEFO primero)
        self.lot_a = StockLot.objects.create(
            product=self.product,
            lot_code="LOTE-A",
            expiry_date=today + timedelta(days=10),
            qty_on_hand=Decimal("15.00"),
            unit_cost=Decimal("10.00"),
            warehouse=self.warehouse
        )
        
        # Lote B - vence en 30 días (segundo en FEFO)
        self.lot_b = StockLot.objects.create(
            product=self.product,
            lot_code="LOTE-B",
            expiry_date=today + timedelta(days=30),
            qty_on_hand=Decimal("20.00"),
            unit_cost=Decimal("12.00"),
            warehouse=self.warehouse
        )
        
        # Lote C - vence en 60 días (último en FEFO)
        self.lot_c = StockLot.objects.create(
            product=self.product,
            lot_code="LOTE-C",
            expiry_date=today + timedelta(days=60),
            qty_on_hand=Decimal("25.00"),
            unit_cost=Decimal("15.00"),
            warehouse=self.warehouse
        )
    
    def test_api_b1_200_con_recomendado_correcto_y_lista_fefo(self):
        """
        API-B1: 200 con recomendado correcto y lista FEFO.
        
        Verifica que:
        - El endpoint retorna 200
        - recommended_id es el lote que vence primero (FEFO)
        - La lista de opciones está ordenada por FEFO
        """
        response = self.client.get(
            "/lots/options?product_id={}&qty={}".format(self.product.id, "10.00")
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verificar estructura de respuesta
        self.assertIn("recommended_id", data)
        self.assertIn("options", data)
        
        # El recomendado debe ser el lote A (vence primero)
        self.assertEqual(data["recommended_id"], self.lot_a.id)
        
        # Verificar que hay 3 opciones
        self.assertEqual(len(data["options"]), 3)
        
        # Verificar orden FEFO (por fecha de vencimiento)
        options = data["options"]
        self.assertEqual(options[0]["id"], self.lot_a.id)  # Vence en 10 días
        self.assertEqual(options[1]["id"], self.lot_b.id)  # Vence en 30 días
        self.assertEqual(options[2]["id"], self.lot_c.id)  # Vence en 60 días
        
        # Verificar datos del primer lote (recomendado)
        first_option = options[0]
        self.assertEqual(first_option["lot_code"], "LOTE-A")
        self.assertEqual(first_option["qty_on_hand"], "15.000")  # Decimal con 3 decimales
        self.assertEqual(first_option["expiry_date"], str(self.lot_a.expiry_date))
    
    def test_api_b2_qty_invalida_400(self):
        """
        API-B2: qty inválida → 400 "qty inválida".
        
        Verifica que cantidades inválidas (≤0) retornan error 400.
        """
        # Test con qty = 0
        response = self.client.get(
            "/lots/options?product_id={}&qty={}".format(self.product.id, "0")
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error"], "INVALID_QTY")
        self.assertEqual(data["message"], "qty inválida")
        
        # Test con qty negativa
        response = self.client.get(
            "/lots/options?product_id={}&qty={}".format(self.product.id, "-5.00")
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error"], "INVALID_QTY")
        self.assertEqual(data["message"], "qty inválida")
    
    def test_api_b3_producto_sin_lotes_recommended_null_options_empty(self):
        """
        API-B3: Producto sin lotes → recommended_id=null y options=[].
        
        Verifica que un producto sin lotes disponibles retorna:
        - recommended_id: null
        - options: lista vacía
        """
        # Crear producto sin lotes
        product_sin_lotes = Product.objects.create(
            code="PROD002",
            name="Producto Sin Lotes",
            brand="Test Brand",
            price=Decimal("50.00")  # Campo requerido
        )
        
        response = self.client.get(
            "/lots/options?product_id={}&qty={}".format(product_sin_lotes.id, "10.00")
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verificar que no hay recomendación
        self.assertIsNone(data["recommended_id"])
        
        # Verificar que la lista de opciones está vacía
        self.assertEqual(len(data["options"]), 0)
        self.assertEqual(data["options"], [])
    
    def test_producto_inexistente_404(self):
        """
        Test adicional: Producto inexistente → 404.
        
        Verifica que un product_id que no existe retorna 404.
        """
        response = self.client.get(
            "/lots/options?product_id={}&qty={}".format(99999, "10.00")
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_parametros_faltantes_422(self):
        """
        Test adicional: Parámetros faltantes → 422.
        
        Verifica que faltar parámetros requeridos retorna error de validación.
        """
        # Sin product_id
        response = self.client.get(
            "/lots/options?qty={}".format("10.00")
        )
        
        self.assertEqual(response.status_code, 422)
        
        # Sin qty
        response = self.client.get(
            "/lots/options?product_id={}".format(self.product.id)
        )
        
        self.assertEqual(response.status_code, 422)
    
    def test_lotes_quarantined_y_reserved_excluidos(self):
        """
        Test adicional: Lotes en cuarentena o reservados son excluidos.
        
        Verifica que lotes con is_quarantined=True o is_reserved=True
        no aparecen en las opciones.
        """
        # Marcar lote A como en cuarentena
        self.lot_a.is_quarantined = True
        self.lot_a.save()
        
        # Marcar lote B como reservado
        self.lot_b.is_reserved = True
        self.lot_b.save()
        
        response = self.client.get(
            "/lots/options?product_id={}&qty={}".format(self.product.id, "10.00")
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Solo debe aparecer el lote C
        self.assertEqual(len(data["options"]), 1)
        self.assertEqual(data["options"][0]["id"], self.lot_c.id)
        self.assertEqual(data["recommended_id"], self.lot_c.id)
    
    def test_customer_id_opcional_ignorado(self):
        """
        Test adicional: customer_id opcional es ignorado correctamente.
        
        Verifica que el parámetro customer_id opcional no afecta el resultado.
        """
        response = self.client.get(
            "/lots/options?product_id={}&qty={}&customer_id={}".format(
                self.product.id, "10.00", 123
            )
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Debe funcionar igual que sin customer_id
        self.assertEqual(data["recommended_id"], self.lot_a.id)
        self.assertEqual(len(data["options"]), 3)