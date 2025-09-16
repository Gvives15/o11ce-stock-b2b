# -*- coding: utf-8 -*-
import os
import django
from decimal import Decimal
from datetime import date, timedelta

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem
from apps.orders.services import checkout
from apps.stock.models import StockLot, Movement
from apps.stock.services import record_entry, record_exit_fefo
from apps.notifications.models import Notification
from apps.customers.models import Customer
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

print("=== VERIFICACION DE PEDIDOS B2B ===")
print()

# 1. Verificar productos y stock disponible
print("1. PRODUCTOS Y STOCK DISPONIBLE:")
products = Product.objects.all()[:3]  # Tomar solo 3 productos para la prueba
for product in products:
    lots = StockLot.objects.filter(product=product, qty_on_hand__gt=0).order_by('expiry_date')
    total_stock = sum(lot.qty_on_hand for lot in lots)
    print(f"  - {product.code}: {product.name} | Stock total: {total_stock}")
    for lot in lots:
        days_to_expiry = (lot.expiry_date - date.today()).days
        print(f"    * Lote {lot.lot_code}: {lot.qty_on_hand} unidades, vence en {days_to_expiry} dias")
print()

# 2. Verificar clientes B2B
print("2. CLIENTES B2B DISPONIBLES:")
customers = Customer.objects.all()[:3]
for customer in customers:
    print(f"  - ID {customer.id}: {customer.name}")
print()

# 3. Crear pedido B2B de prueba
print("3. CREANDO PEDIDO B2B DE PRUEBA:")
if products and customers:
    test_customer = customers[0]
    test_product = products[0]
    
    # Verificar que hay stock suficiente
    available_stock = sum(lot.qty_on_hand for lot in StockLot.objects.filter(product=test_product, qty_on_hand__gt=0))
    
    if available_stock > 0:
        order_qty = min(Decimal('3.000'), available_stock)  # Pedir 3 unidades o el stock disponible
        
        print(f"  Creando pedido para cliente: {test_customer.name}")
        print(f"  Producto: {test_product.code} - {test_product.name}")
        print(f"  Cantidad solicitada: {order_qty}")
        
        try:
            # Crear pedido usando el servicio de checkout
            order = checkout(
                customer_id=test_customer.id,
                items=[
                    {
                        'product_id': test_product.id,
                        'qty': order_qty
                    }
                ],
                delivery_method='delivery',
                delivery_address_text='Direccion de prueba 123',
                client_req_id=f'TEST_B2B_{date.today().strftime("%Y%m%d")}_001'
            )
            
            print(f"  PEDIDO CREADO EXITOSAMENTE:")
            print(f"    - ID: {order.id}")
            print(f"    - Estado: {order.status}")
            print(f"    - Total: ${order.total}")
            print(f"    - Metodo entrega: {order.delivery_method}")
            print(f"    - Direccion: {order.delivery_address_text}")
            
            # Verificar items del pedido
            items = OrderItem.objects.filter(order=order)
            print(f"    - Items del pedido:")
            for item in items:
                print(f"      * {item.product.code}: {item.qty} x ${item.unit_price} = ${item.qty * item.unit_price}")
            
        except Exception as e:
            print(f"  ERROR al crear pedido: {e}")
    else:
        print(f"  No hay stock suficiente para {test_product.code}")
else:
    print("  No hay productos o clientes disponibles para la prueba")
print()

# 4. Verificar aplicacion de FEFO
print("4. VERIFICACION DE FEFO (First Expired, First Out):")
if products:
    test_product = products[0]
    
    # Mostrar lotes antes del pedido (ordenados por fecha de vencimiento)
    lots_before = StockLot.objects.filter(product=test_product).order_by('expiry_date')
    print(f"  Lotes de {test_product.code} ANTES del pedido (orden FEFO):")
    for lot in lots_before:
        days_to_expiry = (lot.expiry_date - date.today()).days
        print(f"    - {lot.lot_code}: {lot.qty_on_hand} unidades, vence en {days_to_expiry} dias")
    
    # Verificar movimientos de salida recientes
    recent_exits = Movement.objects.filter(
        product=test_product,
        type=Movement.Type.EXIT
    ).order_by('-created_at')[:5]
    
    print(f"  MOVIMIENTOS DE SALIDA RECIENTES (verificar FEFO):")
    for movement in recent_exits:
        days_to_expiry = (movement.lot.expiry_date - date.today()).days
        print(f"    - Lote {movement.lot.lot_code}: -{movement.qty} unidades (vencia en {days_to_expiry} dias)")
        print(f"      Razon: {movement.reason}, Orden: {movement.order_id if movement.order else 'N/A'}")
print()

# 5. Verificar notificaciones generadas
print("5. NOTIFICACIONES GENERADAS:")
recent_notifications = Notification.objects.all().order_by('-created_at')[:10]
if recent_notifications:
    for notif in recent_notifications:
        status = "Enviada" if notif.sent_at else "Pendiente"
        print(f"  - {notif.event} | {notif.channel} | {status} | {notif.created_at.strftime('%Y-%m-%d %H:%M')}")
        if notif.payload:
            print(f"    Datos: {notif.payload}")
else:
    print("  No hay notificaciones recientes")
print()

# 6. Verificar pedidos en estado PLACED
print("6. PEDIDOS EN ESTADO PLACED:")
placed_orders = Order.objects.filter(status=Order.Status.PLACED).order_by('-created_at')[:5]
if placed_orders:
    for order in placed_orders:
        print(f"  - Pedido #{order.id}: {order.customer.name} | ${order.total} | {order.created_at.strftime('%Y-%m-%d %H:%M')}")
        items_count = OrderItem.objects.filter(order=order).count()
        print(f"    Items: {items_count} | Entrega: {order.delivery_method}")
else:
    print("  No hay pedidos en estado PLACED")
print()

print("=== VERIFICACION COMPLETADA ===")