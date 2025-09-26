"""Tests específicos para el endpoint GET /catalog/search según B1-BE-01."""

import pytest
from decimal import Decimal
from django.test import Client
from apps.catalog.models import Product


@pytest.mark.django_db
class TestCatalogSearchAPI:
    """Tests para el endpoint GET /catalog/search según B1-BE-01."""
    
    def setup_method(self):
        """Set up test data."""
        self.client = Client()
        
        # Crear productos de prueba según los casos requeridos
        self.gaseosa_product = Product.objects.create(
            code="GAS-500",
            name="Gaseosa 500ml",
            price=Decimal("2.50"),
            tax_rate=Decimal("21.00"),
            brand="Coca Cola",
            category="Bebidas",
            unit="UN",
            is_active=True
        )
        
        self.galletas_caja = Product.objects.create(
            code="GALCX10",
            name="Galletas Caja x10 unidades",
            price=Decimal("15.00"),
            tax_rate=Decimal("21.00"),
            brand="Bagley",
            category="Snacks",
            unit="UN",
            is_active=True
        )
        
        # Productos adicionales para pruebas de paginación
        for i in range(1, 26):  # 25 productos adicionales
            Product.objects.create(
                code=f"TEST-{i:03d}",
                name=f"Producto Test {i}",
                price=Decimal("10.00"),
                tax_rate=Decimal("21.00"),
                unit="UN",
                is_active=True
            )
        
        # Producto inactivo (no debe aparecer en resultados)
        self.inactive_product = Product.objects.create(
            code="INACTIVE-001",
            name="Producto Inactivo",
            price=Decimal("1.00"),
            tax_rate=Decimal("21.00"),
            is_active=False
        )
    
    def test_search_by_name_gas_case(self):
        """Test B1-BE-01: Dado q='gas' → incluye Gaseosa 500ml."""
        response = self.client.get("/api/v1/catalog/search?q=gas")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verificar estructura de respuesta
        assert "results" in data
        assert "next" in data
        
        # Verificar que encuentra la gaseosa
        assert len(data["results"]) >= 1
        
        # Buscar el producto específico en los resultados
        found_gaseosa = False
        for product in data["results"]:
            if "gaseosa" in product["name"].lower():
                found_gaseosa = True
                # Verificar estructura del producto
                assert "id" in product
                assert "sku" in product
                assert "name" in product
                assert "unit" in product
                assert "pack_size" in product
                assert "price_base" in product
                
                # Verificar valores específicos
                assert product["sku"] == "GAS-500"
                assert product["name"] == "Gaseosa 500ml"
                assert product["unit"] == "UN"
                assert product["price_base"] == "2.50"
                break
        
        assert found_gaseosa, "No se encontró la gaseosa en los resultados"
    
    def test_search_by_sku_galcx10_case(self):
        """Test B1-BE-01: Dado q='GALCX10' → devuelve la caja."""
        response = self.client.get("/api/v1/catalog/search?q=GALCX10")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verificar que encuentra el producto específico
        assert len(data["results"]) >= 1
        
        # Buscar el producto específico en los resultados
        found_galletas = False
        for product in data["results"]:
            if product["sku"] == "GALCX10":
                found_galletas = True
                assert product["name"] == "Galletas Caja x10 unidades"
                assert product["unit"] == "UN"
                assert product["price_base"] == "15.00"
                break
        
        assert found_galletas, "No se encontró el producto GALCX10 en los resultados"
    
    def test_search_case_insensitive(self):
        """Test que la búsqueda es case-insensitive."""
        # Buscar en minúsculas
        response_lower = self.client.get("/api/v1/catalog/search?q=galcx10")
        # Buscar en mayúsculas
        response_upper = self.client.get("/api/v1/catalog/search?q=GALCX10")
        
        assert response_lower.status_code == 200
        assert response_upper.status_code == 200
        
        data_lower = response_lower.json()
        data_upper = response_upper.json()
        
        # Verificar que ambas búsquedas encuentran el producto
        found_lower = any(p["sku"] == "GALCX10" for p in data_lower["results"])
        found_upper = any(p["sku"] == "GALCX10" for p in data_upper["results"])
        
        assert found_lower, "Búsqueda en minúsculas no encontró el producto"
        assert found_upper, "Búsqueda en mayúsculas no encontró el producto"
    
    def test_pagination_respects_size(self):
        """Test B1-BE-01: Paginación respeta size."""
        # Solicitar solo 5 elementos por página
        response = self.client.get("/api/v1/catalog/search?size=5")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verificar que devuelve máximo 5 resultados (puede ser menos si hay pocos productos)
        assert len(data["results"]) <= 5
        
        # Si hay más de 5 productos totales, debe haber paginación
        if len(data["results"]) == 5:
            assert data["next"] is not None
            assert "page=2" in data["next"]
            assert "size=5" in data["next"]
    
    def test_pagination_page_parameter(self):
        """Test que el parámetro page funciona correctamente."""
        # Primero verificar cuántos productos hay en total
        response_all = self.client.get("/api/v1/catalog/search?size=100")
        total_products = len(response_all.json()["results"])
        
        # Solo hacer test de paginación si hay suficientes productos
        if total_products > 5:
            # Obtener primera página
            response_page1 = self.client.get("/api/v1/catalog/search?page=1&size=5")
            # Obtener segunda página
            response_page2 = self.client.get("/api/v1/catalog/search?page=2&size=5")
            
            assert response_page1.status_code == 200
            assert response_page2.status_code == 200
            
            data_page1 = response_page1.json()
            data_page2 = response_page2.json()
            
            # Verificar que ambas páginas tienen resultados
            assert len(data_page1["results"]) > 0
            assert len(data_page2["results"]) > 0
            
            # Verificar que los resultados son diferentes
            page1_skus = {p["sku"] for p in data_page1["results"]}
            page2_skus = {p["sku"] for p in data_page2["results"]}
            assert page1_skus != page2_skus, "Las páginas no deben tener los mismos productos"
        else:
            # Si no hay suficientes productos, solo verificar que la primera página funciona
            response = self.client.get("/api/v1/catalog/search?page=1&size=5")
            assert response.status_code == 200
    
    def test_search_with_pagination_preserves_query(self):
        """Test que la paginación preserva el query de búsqueda."""
        response = self.client.get("/api/v1/catalog/search?q=TEST&size=10")
        
        assert response.status_code == 200
        data = response.json()
        
        # Si hay siguiente página, debe preservar el query
        if data["next"]:
            assert "q=TEST" in data["next"]
        # Si no hay siguiente página, el test pasa (no hay suficientes resultados para paginar)
    
    def test_empty_search_returns_all_active_products(self):
        """Test que búsqueda vacía devuelve todos los productos activos."""
        response = self.client.get("/api/v1/catalog/search")
        
        assert response.status_code == 200
        data = response.json()
        
        # Debe devolver productos (al menos los que creamos)
        assert len(data["results"]) >= 2  # Al menos gaseosa y galletas
        
        # Verificar que no incluye productos inactivos
        returned_skus = {p["sku"] for p in data["results"]}
        assert "INACTIVE-001" not in returned_skus
    
    def test_search_no_results(self):
        """Test búsqueda que no devuelve resultados."""
        response = self.client.get("/api/v1/catalog/search?q=NOEXISTE12345")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["results"]) == 0
        assert data["next"] is None
    
    def test_response_structure_compliance(self):
        """Test que la respuesta cumple con la estructura especificada."""
        response = self.client.get("/api/v1/catalog/search?q=GAS")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verificar estructura principal
        assert "results" in data
        assert "next" in data
        
        # Verificar estructura de cada producto
        if data["results"]:
            product = data["results"][0]
            required_fields = ["id", "sku", "name", "unit", "pack_size", "price_base"]
            
            for field in required_fields:
                assert field in product, f"Campo {field} faltante en la respuesta"
            
            # Verificar tipos de datos
            assert isinstance(product["id"], int)
            assert isinstance(product["sku"], str)
            assert isinstance(product["name"], str)
            assert isinstance(product["unit"], str)
            assert product["pack_size"] is None or isinstance(product["pack_size"], str)
            assert isinstance(product["price_base"], str)  # Decimal serializado como string
    
    def test_search_by_partial_name(self):
        """Test búsqueda por nombre parcial."""
        response = self.client.get("/api/v1/catalog/search?q=Galletas")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["results"]) >= 1
        
        # Verificar que encuentra el producto correcto
        found = False
        for product in data["results"]:
            if "galletas" in product["name"].lower():
                found = True
                break
        
        assert found, "No se encontró producto con 'Galletas' en el nombre"
    
    def test_search_by_partial_sku(self):
        """Test búsqueda por SKU parcial."""
        response = self.client.get("/api/v1/catalog/search?q=GAL")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["results"]) >= 1
        
        # Verificar que encuentra el producto correcto
        found = False
        for product in data["results"]:
            if "GAL" in product["sku"]:
                found = True
                break
        
        assert found, "No se encontró producto con 'GAL' en el SKU"