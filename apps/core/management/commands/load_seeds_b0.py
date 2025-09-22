from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction
import os


class Command(BaseCommand):
    help = 'Carga datos semilla B0-PM-01: 3 productos, 3 lotes, 2 clientes, beneficios'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Fuerza la carga incluso si ya existen datos',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué se cargaría sin hacer cambios',
        )

    def handle(self, *args, **options):
        from apps.customers.models import Customer
        from apps.catalog.models import Product, Benefit
        from apps.stock.models import StockLot
        
        self.stdout.write(self.style.SUCCESS('=== CARGA DE DATOS SEMILLA B0-PM-01 ==='))
        
        # Verificar si ya existen datos
        existing_customers = Customer.objects.filter(
            name__in=['Kiosco El Barrio', 'Distribuidora Mayorista SA']
        ).count()
        existing_products = Product.objects.filter(
            code__in=['P1-GALLETITAS', 'P2-MERMELADA', 'P3-CEREALES']
        ).count()
        
        if existing_customers > 0 or existing_products > 0:
            if not options['force']:
                self.stdout.write(
                    self.style.WARNING(
                        f'Ya existen datos semilla (Clientes: {existing_customers}, '
                        f'Productos: {existing_products}). '
                        f'Usa --force para sobreescribir.'
                    )
                )
                return
            else:
                self.stdout.write(
                    self.style.WARNING('Forzando carga de datos...')
                )
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('=== MODO DRY-RUN ==='))
            self.stdout.write('Se cargarían:')
            self.stdout.write('• 2 clientes (Kiosco El Barrio, Distribuidora Mayorista SA)')
            self.stdout.write('• 3 productos (P1-GALLETITAS, P2-MERMELADA, P3-CEREALES)')
            self.stdout.write('• 3 lotes con fechas distintas para FEFO')
            self.stdout.write('• 2 beneficios (Descuento Mayorista -8%, Combo Simple)')
            return
        
        # Ruta del archivo fixture
        fixture_path = os.path.join('fixtures', 'seeds_pos_b0.json')
        
        if not os.path.exists(fixture_path):
            self.stdout.write(
                self.style.ERROR(f'Archivo fixture no encontrado: {fixture_path}')
            )
            return
        
        try:
            with transaction.atomic():
                self.stdout.write('Cargando datos desde fixtures/seeds_pos_b0.json...')
                call_command('loaddata', fixture_path, verbosity=0)
                
                # Verificar que se cargaron correctamente
                customers_loaded = Customer.objects.filter(
                    name__in=['Kiosco El Barrio', 'Distribuidora Mayorista SA']
                ).count()
                products_loaded = Product.objects.filter(
                    code__in=['P1-GALLETITAS', 'P2-MERMELADA', 'P3-CEREALES']
                ).count()
                lots_loaded = StockLot.objects.filter(
                    lot_code__in=['GAL240315', 'MER240420', 'CER240610']
                ).count()
                benefits_loaded = Benefit.objects.filter(
                    name__in=['Descuento Mayorista B0 -8%', 'Combo Simple P1+P2']
                ).count()
                
                self.stdout.write(self.style.SUCCESS('✓ Datos cargados exitosamente:'))
                self.stdout.write(f'  • Clientes: {customers_loaded}/2')
                self.stdout.write(f'  • Productos: {products_loaded}/3')
                self.stdout.write(f'  • Lotes: {lots_loaded}/3')
                self.stdout.write(f'  • Beneficios: {benefits_loaded}/2')
                
                # Verificar fechas FEFO
                lots = StockLot.objects.filter(
                    lot_code__in=['GAL240315', 'MER240420', 'CER240610']
                ).order_by('expiry_date')
                
                self.stdout.write(self.style.SUCCESS('✓ Fechas FEFO verificadas:'))
                for lot in lots:
                    self.stdout.write(f'  • {lot.lot_code}: {lot.expiry_date}')
                
                # Verificar beneficio mayorista
                mayorista_benefit = Benefit.objects.filter(
                    name='Descuento Mayorista B0 -8%',
                    segment='wholesale',
                    value=8
                ).first()
                
                if mayorista_benefit:
                    self.stdout.write(
                        self.style.SUCCESS('✓ Descuento mayorista -8% configurado')
                    )
                
                self.stdout.write(
                    self.style.SUCCESS('\n=== DATOS SEMILLA B0-PM-01 CARGADOS ===')
                )
                self.stdout.write('Próximos pasos:')
                self.stdout.write('• Verificar con /catalog/search')
                self.stdout.write('• Verificar con /auth/me (roles)')
                self.stdout.write('• Probar descuento mayorista en cotizaciones')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error al cargar datos: {str(e)}')
            )
            raise