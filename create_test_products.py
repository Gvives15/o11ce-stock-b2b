#!/usr/bin/env python
"""Script para crear productos de prueba con 'gas' en el nombre."""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Product
from decimal import Decimal

def create_test_products():
    """Crear productos de prueba con 'gas' en el nombre."""
    products = [
        {'code': 'GAS001', 'name': 'Gasolina Premium 95', 'price': Decimal('1.45'), 'unit': 'litro'},
        {'code': 'GAS002', 'name': 'Gasolina Regular 87', 'price': Decimal('1.35'), 'unit': 'litro'},
        {'code': 'GAS003', 'name': 'Gasóleo Diesel', 'price': Decimal('1.25'), 'unit': 'litro'},
    ]

    for p in products:
        product, created = Product.objects.get_or_create(
            code=p['code'],
            defaults={
                'name': p['name'],
                'price': p['price'],
                'unit': p['unit'],
                'tax_rate': Decimal('21.00'),
                'brand': 'Shell',
                'category': 'Combustibles',
                'is_active': True
            }
        )
        status = "creado" if created else "ya existe"
        print(f'Producto {product.code} - {product.name}: {status}')

if __name__ == '__main__':
    create_test_products()