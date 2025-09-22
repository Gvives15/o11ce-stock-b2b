"""
Comando Django para actualizar métricas de lotes próximos a vencer.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict

from apps.stock.models import StockLot
from apps.core.metrics import update_near_expiry_lots


class Command(BaseCommand):
    help = 'Actualiza las métricas de lotes próximos a vencer'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Número de días para considerar "próximo a vencer" (default: 30)'
        )

    def handle(self, *args, **options):
        days = options['days']
        today = timezone.now().date()
        cutoff_date = today + timedelta(days=days)
        
        self.stdout.write(f'Actualizando métricas de lotes próximos a vencer (próximos {days} días)...')
        
        # Obtener lotes próximos a vencer con stock
        near_expiry_lots = StockLot.objects.filter(
            expiry_date__lte=cutoff_date,
            expiry_date__gte=today,  # No incluir ya vencidos
            qty_on_hand__gt=0
        ).select_related('product')
        
        # Agrupar por categoría y rango de días
        metrics_data = defaultdict(lambda: defaultdict(int))
        
        for lot in near_expiry_lots:
            days_to_expiry = (lot.expiry_date - today).days
            category = getattr(lot.product, 'category', 'unknown') or 'unknown'
            
            # Determinar rango de días
            if days_to_expiry <= 7:
                days_range = '0-7'
            elif days_to_expiry <= 15:
                days_range = '8-15'
            else:
                days_range = '16-30'
            
            metrics_data[category][days_range] += 1
        
        # Actualizar métricas
        total_updated = 0
        for category, ranges in metrics_data.items():
            for days_range, count in ranges.items():
                update_near_expiry_lots(
                    product_category=category,
                    days_range=days_range,
                    count=count
                )
                total_updated += 1
                self.stdout.write(
                    f'  - {category} ({days_range} días): {count} lotes'
                )
        
        # Resetear métricas para categorías sin lotes próximos a vencer
        # (esto es opcional, pero ayuda a mantener las métricas limpias)
        if not metrics_data:
            update_near_expiry_lots(
                product_category='unknown',
                days_range='0-7',
                count=0
            )
            total_updated += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Métricas actualizadas exitosamente. Total de métricas: {total_updated}'
            )
        )