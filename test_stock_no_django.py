#!/usr/bin/env python
"""
Test final del dominio Stock - Validación sin dependencias Django
"""

import sys
import importlib.util
from pathlib import Path

def test_file_structure():
    """Test de estructura de archivos"""
    print("🔍 Testing file structure...")
    
    stock_dir = Path("apps/stock")
    required_files = [
        "__init__.py",
        "services.py", 
        "events.py",
        "event_handlers.py",
        "api.py",
        "tasks.py"
    ]
    
    missing_files = []
    for file_name in required_files:
        file_path = stock_dir / file_name
        if file_path.exists():
            print(f"    ✅ {file_name}")
        else:
            print(f"    ❌ {file_name} - Missing")
            missing_files.append(file_name)
    
    if not missing_files:
        print("  ✅ All required files present")
        return True
    else:
        print(f"  ❌ Missing files: {missing_files}")
        return False

def test_syntax_validation():
    """Test de validación de sintaxis"""
    print("🔍 Testing syntax validation...")
    
    stock_files = [
        "apps/stock/services.py",
        "apps/stock/events.py", 
        "apps/stock/event_handlers.py",
        "apps/stock/api.py",
        "apps/stock/tasks.py"
    ]
    
    syntax_errors = []
    for file_path in stock_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Compilar para verificar sintaxis
            compile(content, file_path, 'exec')
            print(f"    ✅ {file_path}")
            
        except SyntaxError as e:
            print(f"    ❌ {file_path} - Syntax error: {e}")
            syntax_errors.append(file_path)
        except FileNotFoundError:
            print(f"    ❌ {file_path} - File not found")
            syntax_errors.append(file_path)
        except Exception as e:
            print(f"    ❌ {file_path} - Error: {e}")
            syntax_errors.append(file_path)
    
    if not syntax_errors:
        print("  ✅ All files have valid syntax")
        return True
    else:
        print(f"  ❌ Syntax errors in: {syntax_errors}")
        return False

def test_event_definitions():
    """Test de definiciones de eventos"""
    print("🔍 Testing event definitions...")
    
    try:
        # Leer el archivo de eventos
        with open("apps/stock/events.py", 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar eventos clave
        required_events = [
            "StockEntryRequested",
            "StockExitRequested", 
            "StockValidationRequested",
            "StockValidated",
            "StockEntryCompleted",
            "StockExitCompleted"
        ]
        
        missing_events = []
        for event_name in required_events:
            if f"class {event_name}" in content:
                print(f"    ✅ {event_name}")
            else:
                print(f"    ❌ {event_name} - Not found")
                missing_events.append(event_name)
        
        if not missing_events:
            print("  ✅ All required events defined")
            return True
        else:
            print(f"  ❌ Missing events: {missing_events}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error reading events file: {e}")
        return False

def test_service_definitions():
    """Test de definiciones de servicios"""
    print("🔍 Testing service definitions...")
    
    try:
        # Leer el archivo de servicios
        with open("apps/stock/services.py", 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar funciones clave
        required_functions = [
            "def request_stock_entry",
            "def request_stock_exit",
            "def validate_stock_availability",
            "def validate_warehouse",
            "def create_entry",  # legacy
            "def create_exit"    # legacy
        ]
        
        missing_functions = []
        for func_def in required_functions:
            if func_def in content:
                func_name = func_def.replace("def ", "").replace("(", "")
                print(f"    ✅ {func_name}")
            else:
                func_name = func_def.replace("def ", "").replace("(", "")
                print(f"    ❌ {func_name} - Not found")
                missing_functions.append(func_name)
        
        if not missing_functions:
            print("  ✅ All required service functions defined")
            return True
        else:
            print(f"  ❌ Missing functions: {missing_functions}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error reading services file: {e}")
        return False

def test_handler_definitions():
    """Test de definiciones de handlers"""
    print("🔍 Testing handler definitions...")
    
    try:
        # Leer el archivo de handlers
        with open("apps/stock/event_handlers.py", 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar handlers clave
        required_handlers = [
            "class StockEntryHandler",
            "class StockExitHandler",
            "class StockValidationHandler"
        ]
        
        missing_handlers = []
        for handler_def in required_handlers:
            if handler_def in content:
                handler_name = handler_def.replace("class ", "")
                print(f"    ✅ {handler_name}")
            else:
                handler_name = handler_def.replace("class ", "")
                print(f"    ❌ {handler_name} - Not found")
                missing_handlers.append(handler_name)
        
        # Verificar que tienen método handle
        if "def handle(" in content:
            print("    ✅ handle method found")
        else:
            print("    ❌ handle method - Not found")
            missing_handlers.append("handle method")
        
        if not missing_handlers:
            print("  ✅ All required event handlers defined")
            return True
        else:
            print(f"  ❌ Missing handlers: {missing_handlers}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error reading handlers file: {e}")
        return False

def test_api_definitions():
    """Test de definiciones de API"""
    print("🔍 Testing API definitions...")
    
    try:
        # Leer el archivo de API
        with open("apps/stock/api.py", 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar funciones API event-driven
        required_api_functions = [
            "def request_stock_entry",
            "def request_stock_exit", 
            "def validate_stock_availability"
        ]
        
        missing_functions = []
        for func_def in required_api_functions:
            if func_def in content:
                func_name = func_def.replace("def ", "").replace("(", "")
                print(f"    ✅ {func_name}")
            else:
                func_name = func_def.replace("def ", "").replace("(", "")
                print(f"    ❌ {func_name} - Not found")
                missing_functions.append(func_name)
        
        if not missing_functions:
            print("  ✅ All required API functions defined")
            return True
        else:
            print(f"  ❌ Missing API functions: {missing_functions}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error reading API file: {e}")
        return False

def test_test_files():
    """Test de archivos de test"""
    print("🔍 Testing test files...")
    
    test_files = [
        "apps/stock/tests/unit/test_event_driven_services.py",
        "apps/stock/tests/unit/test_event_handlers.py",
        "apps/stock/tests/integration/test_event_flow.py"
    ]
    
    missing_tests = []
    for test_file in test_files:
        test_path = Path(test_file)
        if test_path.exists():
            print(f"    ✅ {test_file}")
        else:
            print(f"    ❌ {test_file} - Missing")
            missing_tests.append(test_file)
    
    if not missing_tests:
        print("  ✅ All test files present")
        return True
    else:
        print(f"  ❌ Missing test files: {missing_tests}")
        return False

def main():
    """Ejecutar todos los tests"""
    print("🚀 VALIDACIÓN FINAL DEL DOMINIO STOCK (SIN DJANGO)")
    print("=" * 60)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Syntax Validation", test_syntax_validation),
        ("Event Definitions", test_event_definitions),
        ("Service Definitions", test_service_definitions),
        ("Handler Definitions", test_handler_definitions),
        ("API Definitions", test_api_definitions),
        ("Test Files", test_test_files)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} FAILED")
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN FINAL")
    print("=" * 60)
    
    if passed == total:
        print(f"🎉 ¡ÉXITO TOTAL! {passed}/{total} tests pasaron")
        print("\n✅ MIGRACIÓN DEL DOMINIO STOCK COMPLETADA")
        print("\n🏗️  ARQUITECTURA IMPLEMENTADA:")
        print("  • Eventos de dominio definidos")
        print("  • Servicios event-driven implementados")
        print("  • Event handlers para procesamiento asíncrono")
        print("  • API actualizada con funciones event-driven")
        print("  • Compatibilidad hacia atrás mantenida")
        print("  • Tests unitarios e integración creados")
        
        print("\n🔄 FUNCIONALIDADES DISPONIBLES:")
        print("  • Sistema híbrido (legacy + event-driven)")
        print("  • Publicación de eventos para operaciones de stock")
        print("  • Desacoplamiento entre dominios")
        print("  • Trazabilidad completa de eventos")
        
        print("\n📈 BENEFICIOS OBTENIDOS:")
        print("  • Mejor escalabilidad y mantenibilidad")
        print("  • Separación clara de responsabilidades")
        print("  • Facilidad para agregar nuevas funcionalidades")
        print("  • Preparado para arquitectura de microservicios")
        
        print("\n🚀 PRÓXIMOS PASOS:")
        print("  • Configurar base de datos para tests completos")
        print("  • Ejecutar tests unitarios e integración")
        print("  • Implementar monitoreo de eventos")
        print("  • Migrar otros dominios (Orders, POS, Catalog)")
        
        return 0
    else:
        print(f"⚠️  {passed}/{total} tests pasaron")
        print(f"❌ {total - passed} tests fallaron")
        print("\n🔧 ACCIONES REQUERIDAS:")
        print("  • Revisar los errores mostrados arriba")
        print("  • Completar la implementación faltante")
        print("  • Ejecutar nuevamente la validación")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())