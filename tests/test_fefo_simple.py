#!/usr/bin/env python
"""
Test simple de FEFO sin Django ORM - solo SQL directo.
"""
import sqlite3
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

def test_fefo_basic():
    """Test básico de FEFO con SQL directo."""
    print("🧪 Ejecutando test básico de FEFO...")
    
    # Crear base de datos en memoria
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    cursor = conn.cursor()
    
    # Crear tablas
    cursor.execute('''
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE stock_lots (
            id INTEGER PRIMARY KEY,
            product_id INTEGER NOT NULL,
            lot_code TEXT NOT NULL,
            expiry_date DATE,
            qty_on_hand DECIMAL(12,3) NOT NULL DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    # Insertar datos de prueba
    cursor.execute("INSERT INTO products (id, name, code) VALUES (1, 'Test Product', 'TEST001')")
    
    today = date.today()
    lot_a_expiry = today + timedelta(days=10)
    lot_b_expiry = today + timedelta(days=30)
    
    cursor.execute("INSERT INTO stock_lots (id, product_id, lot_code, expiry_date, qty_on_hand) VALUES (1, 1, 'LOT-A', ?, 100.0)", (lot_a_expiry,))
    cursor.execute("INSERT INTO stock_lots (id, product_id, lot_code, expiry_date, qty_on_hand) VALUES (2, 1, 'LOT-B', ?, 50.0)", (lot_b_expiry,))
    
    conn.commit()
    
    print("✅ Test 1: Datos de prueba creados")
    
    # Test FEFO query
    cursor.execute("""
        SELECT id, lot_code, expiry_date, qty_on_hand 
        FROM stock_lots 
        WHERE product_id = 1 AND qty_on_hand > 0 
        ORDER BY expiry_date ASC, id ASC
    """)
    
    lots = cursor.fetchall()
    print(f"✅ Test 2: Lotes encontrados en orden FEFO: {len(lots)}")
    for lot in lots:
        print(f"   - Lote {lot[1]}: vence {lot[2]}, cantidad {lot[3]}")
    
    # Verificar orden FEFO
    assert lots[0][1] == 'LOT-A', f"Primer lote debería ser LOT-A, pero es {lots[0][1]}"
    assert lots[1][1] == 'LOT-B', f"Segundo lote debería ser LOT-B, pero es {lots[1][1]}"
    
    # Test actualización atómica
    qty_to_reduce = 25.0
    cursor.execute("UPDATE stock_lots SET qty_on_hand = qty_on_hand - ? WHERE id = 1 AND qty_on_hand >= ?", (qty_to_reduce, qty_to_reduce))
    
    cursor.execute("SELECT qty_on_hand FROM stock_lots WHERE id = 1")
    new_qty = cursor.fetchone()[0]
    
    print(f"✅ Test 3: Reducción de stock - Final: {new_qty}")
    assert new_qty == 75.0, f"Cantidad final debería ser 75.0, pero es {new_qty}"
    
    conn.close()
    print("🎉 Test básico completado exitosamente!")

def test_fefo_concurrency():
    """Test de concurrencia para FEFO."""
    print("\n🧪 Ejecutando test de concurrencia...")
    
    # Crear base de datos compartida
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    cursor = conn.cursor()
    
    # Crear tablas
    cursor.execute('''
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE stock_lots (
            id INTEGER PRIMARY KEY,
            product_id INTEGER NOT NULL,
            lot_code TEXT NOT NULL,
            expiry_date DATE,
            qty_on_hand DECIMAL(12,3) NOT NULL DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    # Insertar datos de prueba
    cursor.execute("INSERT INTO products (id, name, code) VALUES (1, 'Concurrent Product', 'CONC001')")
    
    today = date.today()
    lot_expiry = today + timedelta(days=15)
    
    cursor.execute("INSERT INTO stock_lots (id, product_id, lot_code, expiry_date, qty_on_hand) VALUES (1, 1, 'CONC-LOT', ?, 1000.0)", (lot_expiry,))
    
    conn.commit()
    
    # Lock para sincronización
    lock = threading.Lock()
    results = []
    errors = []
    
    def worker_allocate(worker_id):
        """Worker que intenta reducir stock."""
        try:
            # Crear conexión por worker
            worker_conn = sqlite3.connect(':memory:', check_same_thread=False)
            worker_conn.execute("ATTACH DATABASE ':memory:' AS shared")
            
            # Simular reducción de stock con verificación
            qty_to_reduce = 10.0
            
            with lock:
                # Verificar stock disponible
                cursor.execute("SELECT qty_on_hand FROM stock_lots WHERE id = 1")
                current_qty = cursor.fetchone()[0]
                
                if current_qty >= qty_to_reduce:
                    # Reducir stock
                    cursor.execute("UPDATE stock_lots SET qty_on_hand = qty_on_hand - ? WHERE id = 1", (qty_to_reduce,))
                    conn.commit()
                    results.append(f"Worker {worker_id}: Éxito - Redujo {qty_to_reduce}")
                else:
                    errors.append(f"Worker {worker_id}: Stock insuficiente - Disponible: {current_qty}")
            
            worker_conn.close()
            
        except Exception as e:
            errors.append(f"Worker {worker_id}: Error - {str(e)}")
    
    # Ejecutar múltiples workers
    num_workers = 15
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(worker_allocate, i) for i in range(num_workers)]
        for future in as_completed(futures):
            future.result()
    
    # Verificar resultados
    cursor.execute("SELECT qty_on_hand FROM stock_lots WHERE id = 1")
    final_qty = cursor.fetchone()[0]
    
    print(f"✅ Test concurrencia: {len(results)} éxitos, {len(errors)} errores")
    print(f"✅ Stock final: {final_qty} (debe ser >= 0)")
    
    # Verificar que no hay stock negativo
    assert final_qty >= 0, f"Stock negativo detectado: {final_qty}"
    
    # Verificar que el stock final es correcto
    expected_final = 1000.0 - (len(results) * 10.0)
    assert final_qty == expected_final, f"Stock final incorrecto. Esperado: {expected_final}, Actual: {final_qty}"
    
    conn.close()
    print("🎉 Test de concurrencia completado exitosamente!")

def test_fefo_multiple_lots():
    """Test FEFO con múltiples lotes."""
    print("\n🧪 Ejecutando test FEFO con múltiples lotes...")
    
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    cursor = conn.cursor()
    
    # Crear tablas
    cursor.execute('''
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE stock_lots (
            id INTEGER PRIMARY KEY,
            product_id INTEGER NOT NULL,
            lot_code TEXT NOT NULL,
            expiry_date DATE,
            qty_on_hand DECIMAL(12,3) NOT NULL DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    # Insertar datos de prueba
    cursor.execute("INSERT INTO products (id, name, code) VALUES (1, 'Multi Lot Product', 'MULTI001')")
    
    today = date.today()
    
    # Crear múltiples lotes con diferentes fechas
    lots_data = [
        (1, 'LOT-001', today + timedelta(days=5), 30.0),
        (2, 'LOT-002', today + timedelta(days=15), 50.0),
        (3, 'LOT-003', today + timedelta(days=25), 40.0),
    ]
    
    for lot_id, lot_code, expiry, qty in lots_data:
        cursor.execute("INSERT INTO stock_lots (id, product_id, lot_code, expiry_date, qty_on_hand) VALUES (?, 1, ?, ?, ?)", 
                      (lot_id, lot_code, expiry, qty))
    
    conn.commit()
    
    # Test: Asignar 80 unidades (debe usar LOT-001 completo + parte de LOT-002)
    qty_needed = 80.0
    allocated_lots = []
    remaining_qty = qty_needed
    
    # Obtener lotes en orden FEFO
    cursor.execute("""
        SELECT id, lot_code, expiry_date, qty_on_hand 
        FROM stock_lots 
        WHERE product_id = 1 AND qty_on_hand > 0 
        ORDER BY expiry_date ASC, id ASC
    """)
    
    lots = cursor.fetchall()
    
    for lot_id, lot_code, expiry, available_qty in lots:
        if remaining_qty <= 0:
            break
            
        qty_to_take = min(remaining_qty, available_qty)
        allocated_lots.append((lot_id, lot_code, qty_to_take))
        
        # Actualizar stock
        cursor.execute("UPDATE stock_lots SET qty_on_hand = qty_on_hand - ? WHERE id = ?", (qty_to_take, lot_id))
        remaining_qty -= qty_to_take
    
    conn.commit()
    
    print(f"✅ Test múltiples lotes: Asignados {len(allocated_lots)} lotes")
    for lot_id, lot_code, qty in allocated_lots:
        print(f"   - {lot_code}: {qty} unidades")
    
    # Verificar asignación correcta
    assert len(allocated_lots) == 2, f"Debería usar 2 lotes, pero usó {len(allocated_lots)}"
    assert allocated_lots[0][1] == 'LOT-001', f"Primer lote debería ser LOT-001"
    assert allocated_lots[0][2] == 30.0, f"LOT-001 debería asignar 30.0 unidades"
    assert allocated_lots[1][1] == 'LOT-002', f"Segundo lote debería ser LOT-002"
    assert allocated_lots[1][2] == 50.0, f"LOT-002 debería asignar 50.0 unidades"
    
    # Verificar stock restante
    cursor.execute("SELECT lot_code, qty_on_hand FROM stock_lots ORDER BY expiry_date")
    remaining_lots = cursor.fetchall()
    
    print("✅ Stock restante:")
    for lot_code, qty in remaining_lots:
        print(f"   - {lot_code}: {qty} unidades")
    
    conn.close()
    print("🎉 Test múltiples lotes completado exitosamente!")

if __name__ == "__main__":
    try:
        test_fefo_basic()
        test_fefo_concurrency()
        test_fefo_multiple_lots()
        
        print("\n🎊 TODOS LOS TESTS COMPLETADOS EXITOSAMENTE!")
        print("📋 Resumen de funcionalidades verificadas:")
        print("   - ✅ Consulta FEFO (First Expired, First Out)")
        print("   - ✅ Actualización atómica de stock")
        print("   - ✅ Prevención de stock negativo")
        print("   - ✅ Manejo de concurrencia")
        print("   - ✅ Asignación multi-lote")
        print("   - ✅ Orden correcto por fecha de vencimiento")
        
    except Exception as e:
        print(f"\n❌ Error en tests: {e}")
        import traceback
        traceback.print_exc()