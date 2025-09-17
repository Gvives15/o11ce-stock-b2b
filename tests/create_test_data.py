#!/usr/bin/env python
"""
Script para crear datos de prueba para el sistema BFF
"""

import os
import sys
import django
from decimal import Decimal
from datetime import date, timedelta

# Agregar el directorio padre al PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from apps.catalog.models import Product
from apps.stock.models import Warehouse, StockLot
from apps.customers.models import Customer
from apps.orders.models import Order
from apps.notifications.models import Notification

def create_test_data():
    print("Creando datos de prueba...")
    
    # Crear usuarios con diferentes roles
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@bff.com',
            'first_name': 'Admin',
            'last_name': 'User',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print(f"✓ Usuario admin creado")
    
    manager_user, created = User.objects.get_or_create(
        username='manager',
        defaults={
            'email': 'manager@bff.com',
            'first_name': 'Manager',
            'last_name': 'User',
            'is_staff': True
        }
    )
    if created:
        manager_user.set_password('manager123')
        manager_user.save()
        print(f"✓ Usuario manager creado")
    
    operator_user, created = User.objects.get_or_create(
        username='operator',
        defaults={
            'email': 'operator@bff.com',
            'first_name': 'Operator',
            'last_name': 'User'
        }
    )
    if created:
        operator_user.set_password('operator123')
        operator_user.save()
        print(f"✓ Usuario operator creado")
    
    # Crear almacén
    warehouse, created = Warehouse.objects.get_or_create(
        name='Almacén Principal',
        defaults={'is_active': True}
    )
    if created:
        print(f"✓ Almacén creado")
    
    # Crear productos
    products_data = [
        {'name': 'Producto A', 'code': 'PROD-A-001', 'price': '25.50'},
        {'name': 'Producto B', 'code': 'PROD-B-002', 'price': '15.75'},
        {'name': 'Producto C', 'code': 'PROD-C-003', 'price': '45.00'},
        {'name': 'Producto D', 'code': 'PROD-D-004', 'price': '12.25'},
        {'name': 'Producto E', 'code': 'PROD-E-005', 'price': '33.80'},
    ]
    
    products = []
    for prod_data in products_data:
        product, created = Product.objects.get_or_create(
            code=prod_data['code'],
            defaults={
                'name': prod_data['name'],
                'price': Decimal(prod_data['price']),
                'is_active': True
            }
        )
        products.append(product)
        if created:
            print(f"✓ Producto {product.name} creado")
    
    # Crear stock
    for i, product in enumerate(products):
        # Stock normal
        StockLot.objects.get_or_create(
            product=product,
            warehouse=warehouse,
            lot_code=f'LOT-{product.code}-001',
            defaults={
                'qty_on_hand': Decimal('100'),
                'unit_cost': product.price * Decimal('0.7'),  # Costo del 70% del precio
                'expiry_date': date.today() + timedelta(days=90 + i*30)
            }
        )
        
        # Stock próximo a vencer (para alertas)
        if i < 2:
            StockLot.objects.get_or_create(
                product=product,
                warehouse=warehouse,
                lot_code=f'LOT-{product.code}-002',
                defaults={
                    'qty_on_hand': Decimal('25'),
                    'unit_cost': product.price * Decimal('0.7'),  # Costo del 70% del precio
                    'expiry_date': date.today() + timedelta(days=15)
                }
            )
    
    print(f"✓ Stock creado para {len(products)} productos")
    
    # Crear clientes
    customers_data = [
        {'name': 'Cliente Premium S.A.', 'email': 'premium@cliente.com', 'segment': 'wholesale'},
        {'name': 'Distribuidora Norte', 'email': 'norte@distribuidor.com', 'segment': 'wholesale'},
        {'name': 'Comercial Sur Ltda.', 'email': 'sur@comercial.com', 'segment': 'retail'},
    ]
    
    customers = []
    for cust_data in customers_data:
        customer, created = Customer.objects.get_or_create(
            email=cust_data['email'],
            defaults={
                'name': cust_data['name'],
                'segment': cust_data['segment']
            }
        )
        customers.append(customer)
        if created:
            print(f"✓ Cliente {customer.name} creado")
    
    # Crear órdenes
    for i, customer in enumerate(customers):
        order, created = Order.objects.get_or_create(
            customer=customer,
            defaults={
                'status': 'draft' if i % 2 == 0 else 'placed',
                'total': Decimal('150.00') + Decimal(str(i * 50)),
                'delivery_method': 'delivery'
            }
        )
        if created:
            print(f"✓ Orden para {customer.name} creada")
    
    # Crear notificaciones de prueba
    notifications_data = [
        {'event': 'LOW_STOCK', 'payload': {'product_id': products[0].id, 'current_stock': 5}},
        {'event': 'NEAR_EXPIRY', 'payload': {'product_id': products[1].id, 'days_to_expiry': 10}},
        {'event': 'NEW_ORDER', 'payload': {'order_id': 1, 'customer': 'Cliente Premium S.A.'}},
    ]
    
    for notif_data in notifications_data:
        notification, created = Notification.objects.get_or_create(
            event=notif_data['event'],
            channel='PANEL',
            payload=notif_data['payload'],
            defaults={}
        )
        if created:
            print(f"✓ Notificación {notification.event} creada")
    
    print("\n🎉 Datos de prueba creados exitosamente!")
    print("\nUsuarios creados:")
    print("- admin / admin123 (Superusuario)")
    print("- manager / manager123 (Staff)")
    print("- operator / operator123 (Usuario normal)")
    print("\nPuedes acceder al panel en: http://127.0.0.1:8000/panel/")

if __name__ == '__main__':
    create_test_data()