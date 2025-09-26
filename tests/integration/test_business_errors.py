#!/usr/bin/env python
"""
Test para verificar que las excepciones de negocio se lancen correctamente.
"""
import os
import sys
import django
from django.conf import settings

if __name__ == "__main__":
    # Configuración mínima para tests
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'apps.catalog',
                'apps.stock',
            ],
            SECRET_KEY='test-secret-key-for-business-errors',
            USE_TZ=True,
        )
    
    django.setup()
    
    # Crear tablas básicas
    from django.core.management import call_command
    from django.db import connection
    
    # Crear tablas manualmente para evitar problemas de migración
    cursor = connection.cursor()
    
    # Crear tabla de usuarios
    cursor.execute('''
        CREATE TABLE auth_user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(150) UNIQUE NOT NULL,
            email VARCHAR(254),
            password VARCHAR(128) NOT NULL,
            is_superuser BOOLEAN NOT NULL DEFAULT 0,
            is_staff BOOLEAN NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            date_joined TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            first_name VARCHAR(150),
            last_name VARCHAR(150)
        )
    ''')
    
    # Crear tabla de productos
    cursor.execute('''
        CREATE TABLE catalog_product (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(200) NOT NULL,
            code VARCHAR(50) UNIQUE NOT NULL,
            category VARCHAR(100),
            price DECIMAL(10,2) NOT NULL
        )
    ''')
    
    # Crear tabla de almacenes
    cursor.execute('''
        CREATE TABLE stock_warehouse (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(200) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT 1
        )
    ''')
    
    # Crear tabla de lotes
    cursor.execute('''
        CREATE TABLE stock_stocklot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            warehouse_id INTEGER NOT NULL,
            lot_code VARCHAR(100) NOT NULL,
            expiry_date DATE,
            qty_on_hand DECIMAL(12,3) NOT NULL DEFAULT 0,
            unit_cost DECIMAL(10,2) NOT NULL,
            is_quarantined BOOLEAN NOT NULL DEFAULT 0,
            is_reserved BOOLEAN NOT NULL DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES catalog_product (id),
            FOREIGN KEY (warehouse_id) REFERENCES stock_warehouse (id)
        )
    ''')
    
    # Crear tabla de movimientos
    cursor.execute('''
        CREATE TABLE stock_movement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type VARCHAR(20) NOT NULL,
            product_id INTEGER NOT NULL,
            lot_id INTEGER,
            qty DECIMAL(12,3) NOT NULL,
            reason VARCHAR(200),
            created_by_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES catalog_product (id),
            FOREIGN KEY (lot_id) REFERENCES stock_stocklot (id),
            FOREIGN KEY (created_by_id) REFERENCES auth_user (id)
        )
    ''')
    
    connection.commit()
    
    # Importar modelos y servicios
    from datetime import date, timedelta
    from decimal import Decimal
    from django.contrib.auth.models import User
    from apps.catalog.models import Product
    from apps.stock.models import StockLot, Warehouse
    from apps.stock.fefo_service import FEFOService
    from apps.stock.services import NotEnoughStock, NoLotsAvailable
    
    def test_not_enough_stock_error():
        """Test que verifica que se lance NotEnoughStock cuando no hay suficiente stock."""
        print("🧪 Ejecutando test de excepción NotEnoughStock...")
        
        # Crear datos de prueba
        user = User.objects.create_user(username='test_user', password='test123')
        warehouse = Warehouse.objects.create(name='Test Warehouse', is_active=True)
        product = Product.objects.create(
            name='Test Product',
            code='TEST001',
            category='Test',
            price=Decimal('100.00')
        )
        
        # Crear lote con stock limitado
        today = date.today()
        lot = StockLot.objects.create(
            product=product,
            warehouse=warehouse,
            lot_code='LIMITED-LOT',
            expiry_date=today + timedelta(days=30),
            qty_on_hand=Decimal('50.0'),
            unit_cost=Decimal('10.00')
        )
        
        fefo_service = FEFOService()
        
        # Test 1: Intentar asignar más stock del disponible
        try:
            fefo_service.allocate_stock(product.id, Decimal('100.0'), user.id)
            assert False, "Debería haber lanzado NotEnoughStock"
        except NotEnoughStock as e:
            assert e.product_id == product.id
            assert e.requested == Decimal('100.0')
            assert e.available == Decimal('50.0')
            print(f"✅ Test 1 pasado: NotEnoughStock lanzada correctamente - Solicitado: {e.requested}, Disponible: {e.available}")
        
        # Test 2: Verificar mensaje de error
        try:
            fefo_service.allocate_stock(product.id, Decimal('75.0'), user.id)
            assert False, "Debería haber lanzado NotEnoughStock"
        except NotEnoughStock as e:
            expected_msg = f"Stock insuficiente para producto {product.id}. Solicitado: 75.0, Disponible: 50.0"
            assert str(e) == expected_msg
            print(f"✅ Test 2 pasado: Mensaje de error correcto - {str(e)}")
        
        print("🎉 Test NotEnoughStock completado exitosamente!")
    
    def test_no_lots_available_error():
        """Test que verifica que se lance NoLotsAvailable cuando no hay lotes disponibles."""
        print("\n🧪 Ejecutando test de excepción NoLotsAvailable...")
        
        # Crear datos de prueba
        user = User.objects.create_user(username='test_user2', password='test123')
        warehouse = Warehouse.objects.create(name='Test Warehouse 2', is_active=True)
        product = Product.objects.create(
            name='No Lots Product',
            code='NOLOTS001',
            category='Test',
            price=Decimal('50.00')
        )
        
        # No crear lotes - producto sin stock
        
        fefo_service = FEFOService()
        
        # Test 1: Intentar asignar stock cuando no hay lotes
        try:
            fefo_service.allocate_stock(product.id, Decimal('10.0'), user.id)
            assert False, "Debería haber lanzado NoLotsAvailable"
        except NoLotsAvailable as e:
            assert e.product_id == product.id
            print(f"✅ Test 1 pasado: NoLotsAvailable lanzada correctamente para producto {e.product_id}")
        
        # Test 2: Crear lotes pero con stock cero
        today = date.today()
        lot_empty = StockLot.objects.create(
            product=product,
            warehouse=warehouse,
            lot_code='EMPTY-LOT',
            expiry_date=today + timedelta(days=30),
            qty_on_hand=Decimal('0.0'),
            unit_cost=Decimal('10.00')
        )
        
        try:
            fefo_service.allocate_stock(product.id, Decimal('5.0'), user.id)
            assert False, "Debería haber lanzado NoLotsAvailable"
        except NoLotsAvailable as e:
            assert e.product_id == product.id
            print(f"✅ Test 2 pasado: NoLotsAvailable lanzada con lotes vacíos para producto {e.product_id}")
        
        # Test 3: Crear lotes en cuarentena
        lot_quarantined = StockLot.objects.create(
            product=product,
            warehouse=warehouse,
            lot_code='QUARANTINED-LOT',
            expiry_date=today + timedelta(days=30),
            qty_on_hand=Decimal('20.0'),
            unit_cost=Decimal('10.00'),
            is_quarantined=True
        )
        
        try:
            fefo_service.allocate_stock(product.id, Decimal('5.0'), user.id)
            assert False, "Debería haber lanzado NoLotsAvailable"
        except NoLotsAvailable as e:
            assert e.product_id == product.id
            print(f"✅ Test 3 pasado: NoLotsAvailable lanzada con lotes en cuarentena para producto {e.product_id}")
        
        print("🎉 Test NoLotsAvailable completado exitosamente!")
    
    def test_error_messages():
        """Test que verifica los mensajes de error personalizados."""
        print("\n🧪 Ejecutando test de mensajes de error...")
        
        # Test NotEnoughStock message
        error1 = NotEnoughStock(product_id=123, requested=Decimal('100.0'), available=Decimal('50.0'))
        expected_msg1 = "Stock insuficiente para producto 123. Solicitado: 100.0, Disponible: 50.0"
        assert str(error1) == expected_msg1
        print(f"✅ Test 1 pasado: Mensaje NotEnoughStock - {str(error1)}")
        
        # Test NoLotsAvailable message
        error2 = NoLotsAvailable(product_id=456, criteria="qty_on_hand > 0 AND is_quarantined = False")
        expected_msg2 = "No hay lotes disponibles para producto 456 con criterios: qty_on_hand > 0 AND is_quarantined = False"
        assert str(error2) == expected_msg2
        print(f"✅ Test 2 pasado: Mensaje NoLotsAvailable - {str(error2)}")
        
        # Test error attributes
        assert error1.product_id == 123
        assert error1.requested == Decimal('100.0')
        assert error1.available == Decimal('50.0')
        
        assert error2.product_id == 456
        assert error2.criteria == "qty_on_hand > 0 AND is_quarantined = False"
        
        print("✅ Test 3 pasado: Atributos de errores correctos")
        print("🎉 Test de mensajes de error completado exitosamente!")
    
    # Ejecutar todos los tests
    try:
        test_not_enough_stock_error()
        test_no_lots_available_error()
        test_error_messages()
        
        print("\n🎊 TODOS LOS TESTS DE EXCEPCIONES COMPLETADOS EXITOSAMENTE!")
        print("📋 Resumen de funcionalidades verificadas:")
        print("   - ✅ Excepción NotEnoughStock se lanza correctamente")
        print("   - ✅ Excepción NoLotsAvailable se lanza correctamente")
        print("   - ✅ Mensajes de error personalizados")
        print("   - ✅ Atributos de excepciones correctos")
        print("   - ✅ Manejo de casos edge (lotes vacíos, cuarentena)")
        
    except Exception as e:
        print(f"\n❌ Error en tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)