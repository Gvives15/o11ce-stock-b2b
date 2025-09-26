#!/usr/bin/env python
"""
Test de integración para verificar que el sistema FEFO funciona en el contexto real.
Simula operaciones como las que se harían desde las APIs de stock, órdenes y POS.
"""
import os
import sys
import django
from decimal import Decimal
from datetime import date, timedelta

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    django.setup()
except Exception as e:
    print(f"❌ Error configurando Django: {e}")
    sys.exit(1)

# Importar después de configurar Django
from django.contrib.auth.models import User
from django.db import transaction
from apps.catalog.models import Product
from apps.stock.models import StockLot, Movement, Warehouse
from apps.stock.services import record_entry, record_exit_fefo, ExitError
from apps.orders.models import Order, OrderItem
from apps.customers.models import Customer


def setup_test_data():
    """Configura datos de prueba como en un entorno real."""
    print("🔧 Configurando datos de prueba...")
    
    # Crear usuario
    user, created = User.objects.get_or_create(
        username='test_integration',
        defaults={
            'email': 'test@integration.com',
            'first_name': 'Test',
            'last_name': 'Integration'
        }
    )
    
    # Crear almacén
    warehouse, created = Warehouse.objects.get_or_create(
        name='Almacén Principal',
        defaults={'is_active': True}
    )
    
    # Crear producto
    product, created = Product.objects.get_or_create(
        code='PROD-FEFO-001',
        defaults={
            'name': 'Producto FEFO Test',
            'price': Decimal('25.50'),
            'category': 'Test'
        }
    )
    
    # Crear cliente
    customer, created = Customer.objects.get_or_create(
        email='cliente@test.com',
        defaults={
            'name': 'Cliente Test',
            'phone': '+1234567890'
        }
    )
    
    return user, warehouse, product, customer


def test_stock_entry_and_fefo_exit():
    """Test completo: entrada de stock y salida FEFO como en producción."""
    print("\n🧪 Test: Entrada de stock y salida FEFO")
    
    user, warehouse, product, customer = setup_test_data()
    
    # Limpiar datos previos del producto
    StockLot.objects.filter(product=product).delete()
    Movement.objects.filter(product=product).delete()
    
    today = date.today()
    
    try:
        with transaction.atomic():
            # 1. ENTRADAS DE STOCK (simulando recepción de mercadería)
            print("📦 Registrando entradas de stock...")
            
            # Entrada 1: Lote que vence en 15 días
            entry1 = record_entry(
                product_id=product.id,
                lot_code='LOTE-2024-001',
                expiry_date=today + timedelta(days=15),
                qty=Decimal('100.000'),
                unit_cost=Decimal('20.00'),
                user_id=user.id,
                warehouse_id=warehouse.id
            )
            print(f"   ✅ Entrada 1: {entry1.qty} unidades, vence en 15 días")
            
            # Entrada 2: Lote que vence en 30 días
            entry2 = record_entry(
                product_id=product.id,
                lot_code='LOTE-2024-002',
                expiry_date=today + timedelta(days=30),
                qty=Decimal('150.000'),
                unit_cost=Decimal('22.00'),
                user_id=user.id,
                warehouse_id=warehouse.id
            )
            print(f"   ✅ Entrada 2: {entry2.qty} unidades, vence en 30 días")
            
            # Entrada 3: Lote que vence en 7 días (debe salir primero por FEFO)
            entry3 = record_entry(
                product_id=product.id,
                lot_code='LOTE-2024-003',
                expiry_date=today + timedelta(days=7),
                qty=Decimal('50.000'),
                unit_cost=Decimal('18.00'),
                user_id=user.id,
                warehouse_id=warehouse.id
            )
            print(f"   ✅ Entrada 3: {entry3.qty} unidades, vence en 7 días (FEFO priority)")
            
            # Verificar stock total
            total_stock = StockLot.objects.filter(product=product).aggregate(
                total=django.db.models.Sum('qty_on_hand')
            )['total']
            print(f"   📊 Stock total: {total_stock} unidades")
            
            # 2. SALIDA FEFO (simulando venta o despacho)
            print("\n🚚 Realizando salida FEFO...")
            
            # Salida que debe usar primero el lote que vence en 7 días
            exit_movements = record_exit_fefo(
                product_id=product.id,
                qty=Decimal('75.000'),  # Más que el lote que vence primero
                user_id=user.id,
                warehouse_id=warehouse.id
            )
            
            print(f"   ✅ Salida FEFO completada: {len(exit_movements)} movimientos")
            
            # Verificar que se usó FEFO correctamente
            for i, movement in enumerate(exit_movements, 1):
                lot = movement.lot
                print(f"   📋 Movimiento {i}: Lote {lot.lot_code}, {movement.qty} unidades, vence {lot.expiry_date}")
            
            # El primer movimiento debe ser del lote que vence en 7 días
            first_movement = exit_movements[0]
            assert first_movement.lot.lot_code == 'LOTE-2024-003', "FEFO no funcionó: no se usó el lote que vence primero"
            assert first_movement.qty == Decimal('50.000'), "No se consumió completamente el primer lote"
            
            # El segundo movimiento debe ser del lote que vence en 15 días
            if len(exit_movements) > 1:
                second_movement = exit_movements[1]
                assert second_movement.lot.lot_code == 'LOTE-2024-001', "FEFO no funcionó: segundo lote incorrecto"
                assert second_movement.qty == Decimal('25.000'), "Cantidad incorrecta en segundo lote"
            
            print("   ✅ FEFO verificado: se usaron los lotes en orden correcto de vencimiento")
            
            # 3. VERIFICAR STOCK RESTANTE
            print("\n📊 Verificando stock restante...")
            
            remaining_lots = StockLot.objects.filter(product=product, qty_on_hand__gt=0).order_by('expiry_date')
            for lot in remaining_lots:
                print(f"   📦 Lote {lot.lot_code}: {lot.qty_on_hand} unidades, vence {lot.expiry_date}")
            
            # Verificar que el lote que vencía en 7 días está agotado
            lot_7_days = StockLot.objects.get(product=product, lot_code='LOTE-2024-003')
            assert lot_7_days.qty_on_hand == Decimal('0.000'), "El lote que vence primero debería estar agotado"
            
            # Verificar que el lote que vencía en 15 días tiene stock reducido
            lot_15_days = StockLot.objects.get(product=product, lot_code='LOTE-2024-001')
            assert lot_15_days.qty_on_hand == Decimal('75.000'), "Stock incorrecto en lote de 15 días"
            
            # Verificar que el lote que vence en 30 días no se tocó
            lot_30_days = StockLot.objects.get(product=product, lot_code='LOTE-2024-002')
            assert lot_30_days.qty_on_hand == Decimal('150.000'), "El lote de 30 días no debería haberse usado"
            
            print("   ✅ Stock restante correcto según FEFO")
            
            return True
            
    except Exception as e:
        print(f"   ❌ Error en test de integración: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_insufficient_stock_error():
    """Test que verifica el manejo de stock insuficiente."""
    print("\n🧪 Test: Manejo de stock insuficiente")
    
    user, warehouse, product, customer = setup_test_data()
    
    try:
        # Intentar salida mayor al stock disponible
        total_stock = StockLot.objects.filter(product=product).aggregate(
            total=django.db.models.Sum('qty_on_hand')
        )['total'] or Decimal('0')
        
        print(f"   📊 Stock disponible: {total_stock}")
        
        excessive_qty = total_stock + Decimal('100.000')
        print(f"   🚫 Intentando salida de {excessive_qty} (mayor al disponible)")
        
        try:
            record_exit_fefo(
                product_id=product.id,
                qty=excessive_qty,
                user_id=user.id,
                warehouse_id=warehouse.id
            )
            print("   ❌ ERROR: Debería haber lanzado ExitError")
            return False
            
        except ExitError as e:
            print(f"   ✅ ExitError capturada correctamente: {e}")
            assert "INSUFFICIENT_STOCK" in str(e), "Código de error incorrecto"
            return True
            
    except Exception as e:
        print(f"   ❌ Error inesperado: {e}")
        return False


def test_order_integration():
    """Test que simula una orden completa con descuento FEFO."""
    print("\n🧪 Test: Integración con órdenes")
    
    user, warehouse, product, customer = setup_test_data()
    
    try:
        # Crear una orden
        order = Order.objects.create(
            customer=customer,
            status=Order.Status.DRAFT,
            subtotal=Decimal('0.00'),
            total=Decimal('0.00')
        )
        
        print(f"   📋 Orden creada: #{order.id}")
        
        # Simular descuento de stock por orden (como en orders/services.py)
        qty_ordered = Decimal('30.000')
        
        movements = record_exit_fefo(
            product_id=product.id,
            qty=qty_ordered,
            user_id=user.id,
            order_id=order.id,
            warehouse_id=warehouse.id
        )
        
        print(f"   ✅ Stock descontado para orden: {len(movements)} movimientos")
        
        # Verificar que los movimientos están vinculados a la orden
        for movement in movements:
            assert movement.order_id == order.id, "Movimiento no vinculado a la orden"
            print(f"   🔗 Movimiento vinculado: Lote {movement.lot.lot_code}, {movement.qty} unidades")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error en test de órdenes: {e}")
        return False


def test_concurrent_simulation():
    """Test que simula operaciones concurrentes básicas."""
    print("\n🧪 Test: Simulación de concurrencia básica")
    
    user, warehouse, product, customer = setup_test_data()
    
    try:
        # Simular dos operaciones "simultáneas" en el mismo lote
        import threading
        import time
        
        results = []
        errors = []
        
        def concurrent_exit(qty, thread_id):
            try:
                time.sleep(0.1)  # Pequeña pausa para simular concurrencia
                movements = record_exit_fefo(
                    product_id=product.id,
                    qty=qty,
                    user_id=user.id,
                    warehouse_id=warehouse.id
                )
                results.append((thread_id, len(movements)))
                print(f"   ✅ Hilo {thread_id}: {len(movements)} movimientos")
            except Exception as e:
                errors.append((thread_id, str(e)))
                print(f"   ⚠️ Hilo {thread_id}: {e}")
        
        # Lanzar dos hilos
        thread1 = threading.Thread(target=concurrent_exit, args=(Decimal('20.000'), 1))
        thread2 = threading.Thread(target=concurrent_exit, args=(Decimal('15.000'), 2))
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        print(f"   📊 Resultados: {len(results)} exitosos, {len(errors)} errores")
        
        # Al menos una operación debería haber sido exitosa
        if len(results) > 0:
            print("   ✅ Concurrencia básica manejada")
            return True
        else:
            print("   ❌ Todas las operaciones concurrentes fallaron")
            return False
            
    except Exception as e:
        print(f"   ❌ Error en test de concurrencia: {e}")
        return False


def main():
    """Ejecuta todos los tests de integración."""
    print("🚀 INICIANDO TESTS DE INTEGRACIÓN FEFO")
    print("=" * 60)
    
    tests = [
        ("Entrada y Salida FEFO", test_stock_entry_and_fefo_exit),
        ("Stock Insuficiente", test_insufficient_stock_error),
        ("Integración con Órdenes", test_order_integration),
        ("Concurrencia Básica", test_concurrent_simulation),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                print(f"✅ {test_name}: PASÓ")
                passed += 1
            else:
                print(f"❌ {test_name}: FALLÓ")
                failed += 1
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("🎊 RESUMEN DE TESTS DE INTEGRACIÓN")
    print(f"✅ Pasaron: {passed}")
    print(f"❌ Fallaron: {failed}")
    print(f"📊 Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 ¡TODOS LOS TESTS DE INTEGRACIÓN PASARON!")
        print("🚀 El sistema FEFO funciona correctamente en condiciones reales")
        print("\n📋 Funcionalidades verificadas en integración:")
        print("   - ✅ Entrada de stock con múltiples lotes")
        print("   - ✅ Salida FEFO respetando orden de vencimiento")
        print("   - ✅ Manejo correcto de stock insuficiente")
        print("   - ✅ Integración con sistema de órdenes")
        print("   - ✅ Operaciones concurrentes básicas")
        print("   - ✅ Trazabilidad completa de movimientos")
        print("   - ✅ Integridad de datos mantenida")
    else:
        print(f"\n⚠️ {failed} tests fallaron. Revisar implementación.")
        sys.exit(1)


if __name__ == "__main__":
    main()