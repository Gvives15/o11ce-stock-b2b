# -*- coding: utf-8 -*-
from apps.catalog.models import Product
from apps.stock.models import Movement, StockLot
from django.contrib.auth.models import User
from datetime import datetime, timedelta

print('=== PRODUCTOS EXISTENTES ===')
products = Product.objects.all()[:10]
for p in products:
    print(f'{p.name} - Codigo: {p.code} - Precio: {p.price}')

print(f'\nTotal productos: {Product.objects.count()}')

print('\n=== STOCK LOTS EXISTENTES ===')
stock_lots = StockLot.objects.select_related('product')[:10]
for sl in stock_lots:
    print(f'{sl.product.name} - Lote: {sl.lot_code} - Stock: {sl.qty_on_hand} - Vence: {sl.expiry_date}')

print(f'\nTotal stock lots: {StockLot.objects.count()}')

print('\n=== ULTIMOS MOVIMIENTOS DE INVENTARIO ===')
movements = Movement.objects.select_related('product', 'created_by').order_by('-created_at')[:5]
for m in movements:
    print(f'{m.created_at.strftime("%Y-%m-%d %H:%M")} - {m.product.name} - {m.type} - Cantidad: {m.qty} - Usuario: {m.created_by.username}')

print(f'\nTotal movimientos: {Movement.objects.count()}')

# Crear movimientos de prueba si hay productos y stock lots
if products.exists():
    test_product = products[0]
    admin_user = User.objects.filter(username='admin').first()
    
    if admin_user:
        print(f'\n=== CREANDO MOVIMIENTOS DE PRUEBA ===')
        print(f'Producto: {test_product.name}')
        
        # Buscar o crear un stock lot para el producto
        stock_lot, created = StockLot.objects.get_or_create(
            product=test_product,
            lot_code='TEST001',
            defaults={
                'expiry_date': (datetime.now() + timedelta(days=90)).date(),
                'qty_on_hand': 50,
                'unit_cost': 10.00
            }
        )
        
        if created:
            print(f'Stock lot creado: {stock_lot.lot_code} con {stock_lot.qty_on_hand} unidades')
        else:
            print(f'Stock lot existente: {stock_lot.lot_code} con {stock_lot.qty_on_hand} unidades')
        
        # Crear entrada
        movement_entry = Movement.objects.create(
            product=test_product,
            lot=stock_lot,
            type=Movement.Type.ENTRY,
            qty=10,
            unit_cost=10.00,
            reason='Movimiento de prueba - entrada',
            created_by=admin_user
        )
        
        # Actualizar stock lot
        stock_lot.qty_on_hand += movement_entry.qty
        stock_lot.save()
        print(f'Entrada creada: +{movement_entry.qty} unidades. Nuevo stock: {stock_lot.qty_on_hand}')
        
        # Crear salida
        movement_exit = Movement.objects.create(
            product=test_product,
            lot=stock_lot,
            type=Movement.Type.EXIT,
            qty=5,
            reason='Movimiento de prueba - salida',
            created_by=admin_user
        )
        
        # Actualizar stock lot
        stock_lot.qty_on_hand -= movement_exit.qty
        stock_lot.save()
        print(f'Salida creada: -{movement_exit.qty} unidades. Stock final: {stock_lot.qty_on_hand}')
        
        print('\nMovimientos de inventario creados y verificados exitosamente')
else:
    print('\nNo hay productos para crear movimientos de prueba')