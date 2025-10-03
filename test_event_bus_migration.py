#!/usr/bin/env python
"""
Script de prueba para validar la migración del EventBus en el dominio Stock.
Este script verifica que el EventBus centralizado funcione correctamente.
"""

import os
import sys
import django
from django.conf import settings

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

django.setup()

# Importar después de configurar Django
from decimal import Decimal
from datetime import date, datetime
from uuid import uuid4

def test_event_bus_initialization():
    """Prueba que el EventBus se inicialice correctamente."""
    print("🔧 Probando inicialización del EventBus...")
    
    try:
        from apps.core.events import EventBus
        
        # Verificar que el EventBus esté disponible
        assert hasattr(EventBus, 'publish'), "EventBus debe tener método publish"
        assert hasattr(EventBus, 'register_handler'), "EventBus debe tener método register_handler"
        
        print("✅ EventBus inicializado correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error al inicializar EventBus: {e}")
        return False

def test_stock_events_import():
    """Prueba que los eventos del dominio Stock se importen correctamente."""
    print("📦 Probando importación de eventos del dominio Stock...")
    
    try:
        from apps.stock.events import (
            StockEntryRequested,
            ProductValidated,
            StockEntryValidated,
            StockValidationRequested
        )
        
        print("✅ Eventos del dominio Stock importados correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error al importar eventos del Stock: {e}")
        return False

def test_stock_handlers_import():
    """Prueba que los handlers del dominio Stock se importen correctamente."""
    print("🔄 Probando importación de handlers del dominio Stock...")
    
    try:
        from apps.stock.event_handlers import (
            StockEntryHandler,
            StockValidationHandler
        )
        
        print("✅ Handlers del dominio Stock importados correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error al importar handlers del Stock: {e}")
        return False

def test_event_publication():
    """Prueba que se puedan publicar eventos usando EventBus."""
    print("📢 Probando publicación de eventos...")
    
    try:
        from apps.core.events import EventBus
        from apps.stock.events import StockEntryRequested
        
        # Crear un evento de prueba con todos los campos requeridos
        test_event = StockEntryRequested(
            event_id=str(uuid4()),
            occurred_at=datetime.now(),
            aggregate_id="TEST_ENTRY_123",
            aggregate_type="StockEntry",
            entry_id="TEST_ENTRY_123",
            product_id="TEST_PRODUCT_456",
            warehouse_id="TEST_WAREHOUSE_789",
            lot_code="TEST_LOT_001",
            expiry_date=date(2025, 12, 31),
            quantity=Decimal("10.00"),
            unit_cost=Decimal("5.50")
        )
        
        # Intentar publicar el evento
        EventBus.publish(test_event)
        
        print("✅ Evento publicado correctamente usando EventBus")
        return True
        
    except Exception as e:
        print(f"❌ Error al publicar evento: {e}")
        return False

def test_django_apps_configuration():
    """Prueba que la configuración de Django apps esté correcta."""
    print("⚙️ Probando configuración de Django apps...")
    
    try:
        from django.apps import apps
        
        # Verificar que la app core esté registrada
        core_app = apps.get_app_config('core')
        assert core_app is not None, "App 'core' debe estar registrada"
        
        # Verificar que la app stock esté registrada
        stock_app = apps.get_app_config('stock')
        assert stock_app is not None, "App 'stock' debe estar registrada"
        
        print("✅ Configuración de Django apps correcta")
        return True
        
    except Exception as e:
        print(f"❌ Error en configuración de Django apps: {e}")
        return False

def main():
    """Función principal que ejecuta todas las pruebas."""
    print("🚀 Iniciando pruebas de migración del EventBus...")
    print("=" * 60)
    
    tests = [
        test_django_apps_configuration,
        test_event_bus_initialization,
        test_stock_events_import,
        test_stock_handlers_import,
        test_event_publication
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Error inesperado en {test.__name__}: {e}")
            print()
    
    print("=" * 60)
    print(f"📊 Resultados: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron! La migración del EventBus fue exitosa.")
        return True
    else:
        print("⚠️ Algunas pruebas fallaron. Revisar la configuración.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)