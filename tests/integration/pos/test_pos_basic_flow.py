from django.test import TestCase, Client
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date, timedelta

from apps.catalog.models import Product
from apps.stock.models import Warehouse
from apps.stock.services import record_entry
from apps.panel.models import UserScope


class POSBasicFlowTestCase(TestCase):
    """Tests mínimos y estables para el flujo básico de POS: creación de venta y acceso a detalle."""

    def setUp(self):
        self.client = Client()
        # Usuarios
        self.seller1 = User.objects.create_user(
            username='seller1', password='testpass123', email='seller1@test.com'
        )
        self.seller2 = User.objects.create_user(
            username='seller2', password='testpass123', email='seller2@test.com'
        )
        self.admin = User.objects.create_user(
            username='admin', password='testpass123', email='admin@test.com'
        )

        # Scopes (reportes para admin)
        UserScope.objects.get_or_create(user=self.seller1, defaults={'has_scope_reports': False})
        UserScope.objects.get_or_create(user=self.seller2, defaults={'has_scope_reports': False})
        admin_scope, created = UserScope.objects.get_or_create(
            user=self.admin, defaults={'has_scope_reports': True}
        )
        if not created:
            admin_scope.has_scope_reports = True
            admin_scope.save()

        # Almacén y producto
        self.warehouse = Warehouse.objects.create(name='Almacén Principal')
        self.product = Product.objects.create(
            code='PROD-1', name='Producto 1', price=Decimal('10.00')
        )

        # Lotes de stock (FEFO: el que expira primero debe usarse primero)
        today = date.today()
        entry1 = record_entry(
            product_id=self.product.id,
            lot_code='LOT-1',
            expiry_date=today + timedelta(days=10),
            qty=Decimal('5.000'),
            unit_cost=Decimal('8.00'),
            user_id=self.seller1.id,
            warehouse_id=self.warehouse.id,
        )
        entry2 = record_entry(
            product_id=self.product.id,
            lot_code='LOT-2',
            expiry_date=today + timedelta(days=30),
            qty=Decimal('10.000'),
            unit_cost=Decimal('8.50'),
            user_id=self.seller1.id,
            warehouse_id=self.warehouse.id,
        )
        self.lot1 = entry1.lot
        self.lot2 = entry2.lot

    def test_sale_creation_uses_fefo(self):
        """Crear una venta sin lot_id debe usar FEFO (lote con menor fecha de vencimiento)."""
        self.client.force_login(self.seller1)
        payload = {
            'items': [
                {
                    'product_id': self.product.id,
                    'qty': '3.000',
                }
            ]
        }
        response = self.client.post('/api/v1/pos/sale', data=payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('sale_id', data)
        self.assertEqual(len(data['movements']), 1)
        movement = data['movements'][0]
        self.assertEqual(movement['product_id'], self.product.id)
        self.assertEqual(movement['lot_id'], self.lot1.id)  # FEFO → LOT-1
        self.assertEqual(movement['lot_code'], 'LOT-1')

    def test_sale_detail_access_control(self):
        """Validar control de acceso al detalle de venta: 401 (no auth), 200 propio, 403 otros, 200 admin."""
        # Venta seller1
        self.client.force_login(self.seller1)
        resp1 = self.client.post(
            '/api/v1/pos/sale',
            data={
                'items': [
                    {'product_id': self.product.id, 'qty': '1.000', 'unit_price': '10.00'}
                ]
            },
            content_type='application/json',
        )
        self.assertEqual(resp1.status_code, 200)
        sale_id_seller1 = resp1.json()['sale_id']

        # Venta seller2
        self.client.force_login(self.seller2)
        resp2 = self.client.post(
            '/api/v1/pos/sale',
            data={
                'items': [
                    {'product_id': self.product.id, 'qty': '2.000', 'unit_price': '10.00'}
                ]
            },
            content_type='application/json',
        )
        self.assertEqual(resp2.status_code, 200)
        sale_id_seller2 = resp2.json()['sale_id']

        # No autenticado → 401
        self.client.logout()
        r = self.client.get(f'/api/v1/pos/sale/{sale_id_seller1}/detail')
        self.assertEqual(r.status_code, 401)

        # Vendedor puede ver su propia venta → 200
        self.client.force_login(self.seller1)
        r = self.client.get(f'/api/v1/pos/sale/{sale_id_seller1}/detail')
        self.assertEqual(r.status_code, 200)

        # Vendedor NO puede ver venta de otro → 403
        r = self.client.get(f'/api/v1/pos/sale/{sale_id_seller2}/detail')
        self.assertEqual(r.status_code, 403)

        # Admin con scope de reportes puede ver todas → 200
        self.client.force_login(self.admin)
        r = self.client.get(f'/api/v1/pos/sale/{sale_id_seller1}/detail')
        self.assertEqual(r.status_code, 200)
        r = self.client.get(f'/api/v1/pos/sale/{sale_id_seller2}/detail')
        self.assertEqual(r.status_code, 200)