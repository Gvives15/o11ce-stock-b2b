"""
Tests de seguridad para el módulo POS.

Test G-SEC-01: Validar control de acceso por roles en endpoints de trazabilidad.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from datetime import date, timedelta
import json

from apps.catalog.models import Product
from apps.stock.models import Warehouse, StockLot, Movement
from apps.customers.models import Customer
from apps.panel.models import UserScope
from apps.pos.models import SaleItemLot


class TestGSEC01AccessControl(TestCase):
    """
    Test G-SEC-01: Control de acceso por roles
    
    Verifica que:
    - Los vendedores solo puedan ver sus propias ventas
    - Los administradores puedan ver todas las ventas
    - Los usuarios no autenticados no puedan acceder
    """
    
    def setUp(self):
        """Configuración inicial para los tests de seguridad G-SEC-01"""
        # Crear usuarios con diferentes roles
        self.seller1 = User.objects.create_user(
            username='seller1',
            password='testpass123',
            email='seller1@test.com'
        )
        
        self.seller2 = User.objects.create_user(
            username='seller2', 
            password='testpass123',
            email='seller2@test.com'
        )
        
        self.admin = User.objects.create_user(
            username='admin',
            password='testpass123',
            email='admin@test.com'
        )
        
        # Configurar permisos usando get_or_create para evitar duplicados
        seller1_scope, created = UserScope.objects.get_or_create(
            user=self.seller1,
            defaults={'has_scope_reports': False}
        )
        if not created:
            seller1_scope.has_scope_reports = False
            seller1_scope.save()
            
        seller2_scope, created = UserScope.objects.get_or_create(
            user=self.seller2,
            defaults={'has_scope_reports': False}
        )
        if not created:
            seller2_scope.has_scope_reports = False
            seller2_scope.save()
            
        admin_scope, created = UserScope.objects.get_or_create(
            user=self.admin,
            defaults={'has_scope_reports': True}
        )
        if not created:
            admin_scope.has_scope_reports = True
            admin_scope.save()
            
        # Verificar que los scopes están correctamente asignados
        self.seller1.refresh_from_db()
        self.seller2.refresh_from_db()
        self.admin.refresh_from_db()
        
        # Crear datos de prueba
        self.warehouse = Warehouse.objects.create(name='Almacén Test')
        
        self.product = Product.objects.create(
            name='Producto Test',
            code='TEST001',
            price=Decimal('10.00')
        )
        
        self.customer = Customer.objects.create(
            name='Cliente Test',
            segment='retail'
        )
        
        # Crear lotes con stock usando el servicio de entrada
        from apps.stock.services import record_entry
        
        entry1 = record_entry(
            product_id=self.product.id,
            lot_code='LOT001',
            expiry_date=date.today() + timedelta(days=30),
            qty=Decimal('100.00'),
            unit_cost=Decimal('8.00'),
            user_id=self.seller1.id,
            warehouse_id=self.warehouse.id
        )
        self.lot = entry1.lot
        
        # Crear ventas reales usando el endpoint de API
        from django.test import Client
        self.client = Client()
        
        # Venta del seller1
        self.client.force_login(self.seller1)
        response1 = self.client.post(
            '/api/v1/pos/sale',
            data={
                'items': [
                    {
                        'product_id': self.product.id,
                        'qty': '10.00',
                        'unit_price': '10.00'
                    }
                ]
            },
            content_type='application/json'
        )
        self.assertEqual(response1.status_code, 200)
        self.sale_id_seller1 = response1.json()['sale_id']
        
        # Venta del seller2
        self.client.force_login(self.seller2)
        response2 = self.client.post(
            '/api/v1/pos/sale',
            data={
                'items': [
                    {
                        'product_id': self.product.id,
                        'qty': '15.00',
                        'unit_price': '10.00'
                    }
                ]
            },
            content_type='application/json'
        )
        self.assertEqual(response2.status_code, 200)
        self.sale_id_seller2 = response2.json()['sale_id']
    
    def test_unauthenticated_access_denied(self):
        """Test que usuarios no autenticados no pueden acceder."""
        self.client.logout()
        response = self.client.get(f'/api/v1/pos/sale/{self.sale_id_seller1}/detail')
        self.assertEqual(response.status_code, 401)

    def test_seller_can_access_own_sale(self):
        """Test que un vendedor puede ver sus propias ventas."""
        self.client.force_login(self.seller1)
        response = self.client.get(f'/api/v1/pos/sale/{self.sale_id_seller1}/detail')
        self.assertEqual(response.status_code, 200)

    def test_seller_cannot_access_other_sale(self):
        """Test que un vendedor no puede ver ventas de otros."""
        self.client.force_login(self.seller1)
        response = self.client.get(f'/api/v1/pos/sale/{self.sale_id_seller2}/detail')
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_all_sales(self):
        """Test que un admin puede ver todas las ventas."""
        self.client.force_login(self.admin)
        response = self.client.get(f'/api/v1/pos/sale/{self.sale_id_seller1}/detail')
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(f'/api/v1/pos/sale/{self.sale_id_seller2}/detail')
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_sale_returns_404(self):
        """Test que una venta inexistente devuelve 404."""
        self.client.force_login(self.admin)
        response = self.client.get('/api/v1/pos/sale/nonexistent-sale-id/detail')
        self.assertEqual(response.status_code, 404)