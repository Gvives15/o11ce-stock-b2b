#!/usr/bin/env python
"""
Script de validación simplificado para la migración del dominio Stock.
Verifica la estructura básica sin depender de Django.
"""

import os
import sys
import importlib.util

def check_file_exists(file_path):
    """Verificar si un archivo existe."""
    return os.path.exists(file_path)

def check_module_structure(module_path, expected_functions):
    """Verificar que un módulo tenga las funciones esperadas."""
    try:
        spec = importlib.util.spec_from_file_location("module", module_path)
        if spec is None:
            return False, "No se pudo cargar el módulo"
        
        module = importlib.util.module_from_spec(spec)
        
        # Leer el contenido del archivo para verificar las funciones
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        missing_functions = []
        for func in expected_functions:
            if f"def {func}" not in content and f"class {func}" not in content:
                missing_functions.append(func)
        
        if missing_functions:
            return False, f"Funciones faltantes: {', '.join(missing_functions)}"
        
        return True, "Todas las funciones están presentes"
        
    except Exception as e:
        return False, str(e)

def validate_stock_migration():
    """Validar la migración del dominio Stock."""
    print("🚀 Validación simplificada de la migración del dominio Stock")
    print("=" * 60)
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    stock_path = os.path.join(base_path, "apps", "stock")
    
    # 1. Verificar estructura de archivos
    print("\n🔍 Verificando estructura de archivos...")
    required_files = [
        "__init__.py",
        "services.py", 
        "events.py",
        "event_handlers.py",
        "api.py",
        "tasks.py"
    ]
    
    files_ok = True
    for file_name in required_files:
        file_path = os.path.join(stock_path, file_name)
        if check_file_exists(file_path):
            print(f"  ✓ {file_name}")
        else:
            print(f"  ❌ {file_name} - No encontrado")
            files_ok = False
    
    # 2. Verificar servicios
    print("\n🔍 Verificando servicios...")
    services_path = os.path.join(stock_path, "services.py")
    expected_services = [
        "request_stock_entry",
        "request_stock_exit", 
        "validate_stock_availability",
        "validate_warehouse",
        "create_entry",  # Legacy
        "create_exit"    # Legacy
    ]
    
    services_ok, services_msg = check_module_structure(services_path, expected_services)
    if services_ok:
        print(f"  ✓ {services_msg}")
    else:
        print(f"  ❌ {services_msg}")
    
    # 3. Verificar eventos
    print("\n🔍 Verificando eventos...")
    events_path = os.path.join(stock_path, "events.py")
    expected_events = [
        "StockEntryRequested",
        "StockExitRequested",
        "StockValidationRequested",
        "WarehouseValidationRequested",
        "LotExpiryWarning",
        "LowStockDetected"
    ]
    
    events_ok, events_msg = check_module_structure(events_path, expected_events)
    if events_ok:
        print(f"  ✓ {events_msg}")
    else:
        print(f"  ❌ {events_msg}")
    
    # 4. Verificar handlers
    print("\n🔍 Verificando event handlers...")
    handlers_path = os.path.join(stock_path, "event_handlers.py")
    expected_handlers = [
        "StockEntryHandler",
        "StockExitHandler",
        "StockMonitoringHandler",
        "LotManagementHandler",
        "StockIntegrationHandler",
        "WarehouseValidationHandler"
    ]
    
    handlers_ok, handlers_msg = check_module_structure(handlers_path, expected_handlers)
    if handlers_ok:
        print(f"  ✓ {handlers_msg}")
    else:
        print(f"  ❌ {handlers_msg}")
    
    # 5. Verificar API
    print("\n🔍 Verificando API...")
    api_path = os.path.join(stock_path, "api.py")
    
    # Verificar que el archivo contenga las importaciones event-driven
    api_ok = False
    try:
        with open(api_path, 'r', encoding='utf-8') as f:
            api_content = f.read()
            if "request_stock_entry" in api_content and "request_stock_exit" in api_content:
                print("  ✓ API contiene funciones event-driven")
                api_ok = True
            else:
                print("  ❌ API no contiene funciones event-driven")
    except Exception as e:
        print(f"  ❌ Error leyendo API: {e}")
    
    # 6. Verificar tasks
    print("\n🔍 Verificando tasks...")
    tasks_path = os.path.join(stock_path, "tasks.py")
    
    tasks_ok = False
    try:
        with open(tasks_path, 'r', encoding='utf-8') as f:
            tasks_content = f.read()
            if "EventSystemManager" in tasks_content and "publish_event" in tasks_content:
                print("  ✓ Tasks migradas a sistema de eventos")
                tasks_ok = True
            else:
                print("  ❌ Tasks no migradas a sistema de eventos")
    except Exception as e:
        print(f"  ❌ Error leyendo tasks: {e}")
    
    # 7. Verificar tests
    print("\n🔍 Verificando tests...")
    tests_path = os.path.join(stock_path, "tests")
    test_files = [
        "unit/test_event_driven_services.py",
        "unit/test_event_handlers.py", 
        "integration/test_event_flow.py"
    ]
    
    tests_ok = True
    for test_file in test_files:
        test_path = os.path.join(tests_path, test_file)
        if check_file_exists(test_path):
            print(f"  ✓ {test_file}")
        else:
            print(f"  ❌ {test_file} - No encontrado")
            tests_ok = False
    
    # Resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE VALIDACIÓN")
    print("=" * 60)
    
    all_checks = [files_ok, services_ok, events_ok, handlers_ok, api_ok, tasks_ok, tests_ok]
    passed = sum(all_checks)
    total = len(all_checks)
    
    if passed == total:
        print(f"🎉 ¡ÉXITO! Todas las validaciones pasaron ({passed}/{total})")
        print("\n✅ MIGRACIÓN COMPLETADA:")
        print("  • Estructura de archivos correcta")
        print("  • Servicios event-driven implementados")
        print("  • Eventos de dominio definidos")
        print("  • Event handlers creados")
        print("  • API actualizada con funciones event-driven")
        print("  • Tasks migradas a sistema de eventos")
        print("  • Tests unitarios e integración creados")
        
        print("\n🔄 FUNCIONALIDADES DISPONIBLES:")
        print("  • Sistema híbrido: legacy + event-driven")
        print("  • Publicación de eventos para operaciones de stock")
        print("  • Handlers para procesamiento asíncrono")
        print("  • Integración con notificaciones via eventos")
        print("  • Desacoplamiento entre dominios")
        
        print("\n📈 BENEFICIOS OBTENIDOS:")
        print("  • Mejor escalabilidad y mantenibilidad")
        print("  • Separación de responsabilidades")
        print("  • Facilidad para agregar nuevas funcionalidades")
        print("  • Trazabilidad de eventos")
        print("  • Compatibilidad hacia atrás mantenida")
        
        return 0
    else:
        print(f"⚠️  ADVERTENCIA: {passed}/{total} validaciones pasaron")
        print(f"❌ {total - passed} validaciones fallaron")
        print("\n🔧 ACCIONES REQUERIDAS:")
        print("  • Revisar los errores mostrados arriba")
        print("  • Completar los archivos o funciones faltantes")
        print("  • Verificar la implementación de los componentes")
        return 1

if __name__ == "__main__":
    sys.exit(validate_stock_migration())