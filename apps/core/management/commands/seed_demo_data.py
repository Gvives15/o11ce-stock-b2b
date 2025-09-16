from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from datetime import date, timedelta
from decimal import Decimal

from apps.customers.models import Customer
from apps.catalog.models import Product
from apps.stock.models import Warehouse, StockLot


class Command(BaseCommand):
    help = 'Crea datos demo para Sprint 0: 1 cliente mayorista, 2 productos, 2 lotes'

    def handle(self, *args, **options):
        self.stdout.write('Creando datos demo...')
        
        # Crear usuario admin si no existe
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@o11ce.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write('✓ Usuario admin creado')
        
        # Crear cliente mayorista
        customer, created = Customer.objects.get_or_create(
            name='Distribuidora San Martín',
            defaults={
                'segment': Customer.Segment.WHOLESALE,
                'email': 'compras@sanmartin.com',
                'phone': '+54 11 4567-8900',
                'tax_id': '30-12345678-9',
                'tax_condition': 'IVA Responsable Inscripto'
            }
        )
        if created:
            self.stdout.write('✓ Cliente mayorista creado')
        
        # Crear almacén
        warehouse, created = Warehouse.objects.get_or_create(
            name='Depósito Central',
            defaults={'is_active': True}
        )
        if created:
            self.stdout.write('✓ Almacén creado')
        
        # Crear productos
        products_data = [
            {
                'code': 'CHOC001',
                'name': 'Chocolate Amargo 70% Cacao',
                'brand': 'Felfort',
                'unit': 'UN',
                'category': 'Chocolates',
                'price': Decimal('850.00'),
                'tax_rate': Decimal('21.00'),
                'low_stock_threshold': Decimal('50.000')
            },
            {
                'code': 'GALL002', 
                'name': 'Galletas Dulces Surtidas',
                'brand': 'Bagley',
                'unit': 'UN',
                'category': 'Galletitas',
                'price': Decimal('420.00'),
                'tax_rate': Decimal('21.00'),
                'low_stock_threshold': Decimal('30.000')
            }
        ]
        
        products = []
        for product_data in products_data:
            product, created = Product.objects.get_or_create(
                code=product_data['code'],
                defaults=product_data
            )
            products.append(product)
            if created:
                self.stdout.write(f'✓ Producto {product.code} creado')
        
        # Crear lotes con vencimientos distintos
        lots_data = [
            {
                'product': products[0],  # Chocolate
                'lot_code': 'LOT001-2024',
                'expiry_date': date.today() + timedelta(days=90),  # 3 meses
                'qty_on_hand': Decimal('120.000'),
                'unit_cost': Decimal('680.00')
            },
            {
                'product': products[0],  # Chocolate (otro lote)
                'lot_code': 'LOT002-2024',
                'expiry_date': date.today() + timedelta(days=180),  # 6 meses
                'qty_on_hand': Decimal('88.000'),
                'unit_cost': Decimal('675.00')
            },
            {
                'product': products[1],  # Galletas
                'lot_code': 'GAL001-2024',
                'expiry_date': date.today() + timedelta(days=60),  # 2 meses
                'qty_on_hand': Decimal('75.000'),
                'unit_cost': Decimal('320.00')
            },
            {
                'product': products[1],  # Galletas (otro lote)
                'lot_code': 'GAL002-2024',
                'expiry_date': date.today() + timedelta(days=120),  # 4 meses
                'qty_on_hand': Decimal('45.000'),
                'unit_cost': Decimal('315.00')
            }
        ]
        
        for lot_data in lots_data:
            lot_data['warehouse'] = warehouse
            lot, created = StockLot.objects.get_or_create(
                product=lot_data['product'],
                lot_code=lot_data['lot_code'],
                warehouse=lot_data['warehouse'],
                defaults=lot_data
            )
            if created:
                self.stdout.write(f'✓ Lote {lot.lot_code} creado (vence: {lot.expiry_date})')
        
        self.stdout.write(
            self.style.SUCCESS('\n🎉 Datos demo creados exitosamente!')
        )
        self.stdout.write('Resumen:')
        self.stdout.write(f'- 1 Cliente mayorista: {customer.name}')
        self.stdout.write(f'- {len(products)} Productos: {[p.code for p in products]}')
        self.stdout.write(f'- {len(lots_data)} Lotes con vencimientos distintos')
        self.stdout.write('- 1 Usuario admin (admin/admin123)')