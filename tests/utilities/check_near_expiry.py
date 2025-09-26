# -*- coding: utf-8 -*-
import os
import django
from decimal import Decimal
from datetime import date, timedelta

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.stock.models import StockLot
from apps.catalog.models import Product
from django.utils import timezone

print("=== VERIFICACION DE PRODUCTOS PROXIMOS A VENCER ===")
print()

# 1. Configuracion de dias para "near expiry"
NEAR_EXPIRY_DAYS = 30
today = date.today()
cutoff_date = today + timedelta(days=NEAR_EXPIRY_DAYS)

print(f"1. CONFIGURACION:")
print(f"  - Fecha actual: {today}")
print(f"  - Umbral 'Near Expiry': {NEAR_EXPIRY_DAYS} dias")
print(f"  - Fecha limite: {cutoff_date}")
print()

# 2. Buscar productos proximos a vencer (logica del dashboard)
print("2. PRODUCTOS PROXIMOS A VENCER (logica dashboard):")
near_expiry_lots = StockLot.objects.filter(
    qty_on_hand__gt=0,
    expiry_date__lte=cutoff_date,
    expiry_date__gte=today  # No incluir ya vencidos
).select_related('product').order_by('expiry_date')

print(f"  Total de lotes proximos a vencer: {near_expiry_lots.count()}")
print()

if near_expiry_lots:
    print("  DETALLE DE LOTES PROXIMOS A VENCER:")
    for lot in near_expiry_lots:
        days_remaining = (lot.expiry_date - today).days
        status = ""
        if days_remaining <= 7:
            status = "CRITICO"
        elif days_remaining <= 15:
            status = "ALERTA"
        else:
            status = "ATENCION"
        
        print(f"    - {lot.product.code}: {lot.product.name}")
        print(f"      Lote: {lot.lot_code} | Stock: {lot.qty_on_hand}")
        print(f"      Vence: {lot.expiry_date} ({days_remaining} dias) - {status}")
        print()
else:
    print("  No hay productos proximos a vencer en los proximos 30 dias")
    print()

# 3. Verificar productos ya vencidos
print("3. PRODUCTOS YA VENCIDOS:")
expired_lots = StockLot.objects.filter(
    qty_on_hand__gt=0,
    expiry_date__lt=today
).select_related('product').order_by('expiry_date')

print(f"  Total de lotes vencidos: {expired_lots.count()}")

if expired_lots:
    print("  DETALLE DE LOTES VENCIDOS:")
    for lot in expired_lots:
        days_expired = (today - lot.expiry_date).days
        print(f"    - {lot.product.code}: {lot.product.name}")
        print(f"      Lote: {lot.lot_code} | Stock: {lot.qty_on_hand}")
        print(f"      Vencio: {lot.expiry_date} (hace {days_expired} dias)")
        print()
else:
    print("  No hay productos vencidos con stock")
    print()

# 4. Estadisticas por rangos de vencimiento
print("4. ESTADISTICAS POR RANGOS DE VENCIMIENTO:")
ranges = [
    (0, 7, "Proximos 7 dias (CRITICO)"),
    (8, 15, "8-15 dias (ALERTA)"),
    (16, 30, "16-30 dias (ATENCION)"),
]

for min_days, max_days, label in ranges:
    start_date = today + timedelta(days=min_days)
    end_date = today + timedelta(days=max_days)
    
    count = StockLot.objects.filter(
        qty_on_hand__gt=0,
        expiry_date__gte=start_date,
        expiry_date__lte=end_date
    ).count()
    
    print(f"  - {label}: {count} lotes")

print()

# 5. Verificar datos del dashboard (simulacion de la vista)
print("5. SIMULACION DE DATOS DEL DASHBOARD:")
now = timezone.now()

# Replicar la logica exacta del dashboard
dashboard_near_expiry = StockLot.objects.filter(
    qty_on_hand__gt=0, 
    expiry_date__lte=(now.date() + timedelta(days=30))
).select_related("product").order_by("expiry_date")[:20]

print(f"  Productos que aparecerian en dashboard: {dashboard_near_expiry.count()}")
print(f"  (Limitado a primeros 20 por orden de vencimiento)")
print()

if dashboard_near_expiry:
    print("  LISTA DEL DASHBOARD (primeros 10):")
    for i, lot in enumerate(dashboard_near_expiry[:10], 1):
        days_remaining = (lot.expiry_date - today).days
        print(f"    {i}. {lot.product.name}")
        print(f"       Lote: {lot.lot_code} | Stock: {lot.qty_on_hand}")
        print(f"       Vence: {lot.expiry_date} ({days_remaining} dias)")
        print()

# 6. Resumen final
print("6. RESUMEN FINAL:")
total_near_expiry = near_expiry_lots.count()
total_expired = expired_lots.count()
total_products_with_stock = StockLot.objects.filter(qty_on_hand__gt=0).count()

print(f"  - Total lotes con stock: {total_products_with_stock}")
print(f"  - Lotes proximos a vencer (30 dias): {total_near_expiry}")
print(f"  - Lotes ya vencidos: {total_expired}")
print(f"  - Porcentaje proximo a vencer: {(total_near_expiry/total_products_with_stock*100):.1f}%" if total_products_with_stock > 0 else "  - No hay datos suficientes")

print()
print("=== VERIFICACION COMPLETADA ===")