"""
Management command to create database indexes for performance optimization.
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Create database indexes for performance optimization'

    def handle(self, *args, **options):
        """Create the required database indexes."""
        
        with connection.cursor() as cursor:
            # Índice para StockLot(product_id, expiry_date)
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_stocklot_product_expiry 
                    ON stock_stocklot (product_id, expiry_date);
                """)
                self.stdout.write(
                    self.style.SUCCESS('✓ Índice idx_stocklot_product_expiry creado')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'⚠ Índice idx_stocklot_product_expiry ya existe o error: {e}')
                )

            # Índice para Movement(product_id, created_at) - ya existe en migración
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_movement_product_created 
                    ON stock_movement (product_id, created_at);
                """)
                self.stdout.write(
                    self.style.SUCCESS('✓ Índice idx_movement_product_created verificado')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'⚠ Índice idx_movement_product_created: {e}')
                )

            # Índice para Benefit(segment, active_from, active_to) - ya existe en modelo
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_benefit_segment_dates 
                    ON catalog_benefit (segment, active_from, active_to);
                """)
                self.stdout.write(
                    self.style.SUCCESS('✓ Índice idx_benefit_segment_dates creado')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'⚠ Índice idx_benefit_segment_dates ya existe o error: {e}')
                )

        self.stdout.write(
            self.style.SUCCESS('\n🎯 Índices de performance creados/verificados correctamente')
        )