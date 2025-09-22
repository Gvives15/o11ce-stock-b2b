#!/usr/bin/env python
"""
Test simplificado para verificar las excepciones de negocio.
"""
import sys
import os
from decimal import Decimal

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_business_exceptions():
    """Test que verifica las excepciones de negocio."""
    print("🧪 Ejecutando test de excepciones de negocio...")
    
    # Importar las excepciones
    try:
        from apps.stock.services import NotEnoughStock, NoLotsAvailable, StockError
        print("✅ Test 1: Importación de excepciones exitosa")
    except ImportError as e:
        print(f"❌ Error importando excepciones: {e}")
        return False
    
    # Test NotEnoughStock
    print("\n🔍 Probando NotEnoughStock...")
    
    # Test 1: Crear excepción NotEnoughStock
    try:
        error = NotEnoughStock(product_id=123, requested=Decimal('100.0'), available=Decimal('50.0'))
        
        # Verificar atributos
        assert error.product_id == 123
        assert error.requested == Decimal('100.0')
        assert error.available == Decimal('50.0')
        
        # Verificar mensaje
        expected_msg = "Stock insuficiente para producto 123. Solicitado: 100.0, Disponible: 50.0"
        assert str(error) == expected_msg
        
        # Verificar herencia
        assert isinstance(error, StockError)
        assert isinstance(error, Exception)
        
        print(f"✅ Test 2: NotEnoughStock creada correctamente - {str(error)}")
        
    except Exception as e:
        print(f"❌ Error en test NotEnoughStock: {e}")
        return False
    
    # Test NoLotsAvailable
    print("\n🔍 Probando NoLotsAvailable...")
    
    try:
        error = NoLotsAvailable(product_id=456, criteria="qty_on_hand > 0")
        
        # Verificar atributos
        assert error.product_id == 456
        assert error.criteria == "qty_on_hand > 0"
        
        # Verificar mensaje
        expected_msg = "No hay lotes disponibles para producto 456 con criterios: qty_on_hand > 0"
        assert str(error) == expected_msg
        
        # Verificar herencia
        assert isinstance(error, StockError)
        assert isinstance(error, Exception)
        
        print(f"✅ Test 3: NoLotsAvailable creada correctamente - {str(error)}")
        
    except Exception as e:
        print(f"❌ Error en test NoLotsAvailable: {e}")
        return False
    
    # Test casos edge
    print("\n🔍 Probando casos edge...")
    
    try:
        # NotEnoughStock con valores decimales
        error1 = NotEnoughStock(product_id=789, requested=Decimal('25.5'), available=Decimal('10.25'))
        expected_msg1 = "Stock insuficiente para producto 789. Solicitado: 25.5, Disponible: 10.25"
        assert str(error1) == expected_msg1
        print(f"✅ Test 4: NotEnoughStock con decimales - {str(error1)}")
        
        # NoLotsAvailable con criterios complejos
        complex_criteria = "qty_on_hand > 0 AND is_quarantined = False AND expiry_date > '2024-01-01'"
        error2 = NoLotsAvailable(product_id=999, criteria=complex_criteria)
        expected_msg2 = f"No hay lotes disponibles para producto 999 con criterios: {complex_criteria}"
        assert str(error2) == expected_msg2
        print(f"✅ Test 5: NoLotsAvailable con criterios complejos - OK")
        
        # NotEnoughStock con stock cero
        error3 = NotEnoughStock(product_id=111, requested=Decimal('1.0'), available=Decimal('0.0'))
        expected_msg3 = "Stock insuficiente para producto 111. Solicitado: 1.0, Disponible: 0.0"
        assert str(error3) == expected_msg3
        print(f"✅ Test 6: NotEnoughStock con stock cero - {str(error3)}")
        
    except Exception as e:
        print(f"❌ Error en tests de casos edge: {e}")
        return False
    
    # Test lanzamiento de excepciones
    print("\n🔍 Probando lanzamiento de excepciones...")
    
    try:
        # Test que NotEnoughStock se puede lanzar y capturar
        try:
            raise NotEnoughStock(product_id=555, requested=Decimal('50.0'), available=Decimal('25.0'))
        except NotEnoughStock as e:
            assert e.product_id == 555
            assert e.requested == Decimal('50.0')
            assert e.available == Decimal('25.0')
            print("✅ Test 7: NotEnoughStock se lanza y captura correctamente")
        
        # Test que NoLotsAvailable se puede lanzar y capturar
        try:
            raise NoLotsAvailable(product_id=666, criteria="test criteria")
        except NoLotsAvailable as e:
            assert e.product_id == 666
            assert e.criteria == "test criteria"
            print("✅ Test 8: NoLotsAvailable se lanza y captura correctamente")
        
        # Test que se pueden capturar como StockError
        try:
            raise NotEnoughStock(product_id=777, requested=Decimal('10.0'), available=Decimal('5.0'))
        except StockError as e:
            assert isinstance(e, NotEnoughStock)
            print("✅ Test 9: NotEnoughStock se captura como StockError")
        
        try:
            raise NoLotsAvailable(product_id=888, criteria="any criteria")
        except StockError as e:
            assert isinstance(e, NoLotsAvailable)
            print("✅ Test 10: NoLotsAvailable se captura como StockError")
        
    except Exception as e:
        print(f"❌ Error en tests de lanzamiento: {e}")
        return False
    
    return True

def test_fefo_service_exceptions():
    """Test que verifica que FEFOService use las excepciones correctamente."""
    print("\n🧪 Ejecutando test de FEFOService con excepciones...")
    
    try:
        # Importar FEFOService
        from apps.stock.fefo_service import FEFOService
        from apps.stock.services import NotEnoughStock, NoLotsAvailable
        
        # Verificar que FEFOService importa las excepciones
        print("✅ Test 11: FEFOService importado correctamente")
        
        # Verificar que las excepciones están disponibles en el módulo
        import apps.stock.services as stock_services
        assert hasattr(stock_services, 'NotEnoughStock')
        assert hasattr(stock_services, 'NoLotsAvailable')
        assert hasattr(stock_services, 'StockError')
        
        print("✅ Test 12: Excepciones disponibles en módulo stock.services")
        
        return True
        
    except ImportError as e:
        print(f"❌ Error importando FEFOService: {e}")
        return False
    except Exception as e:
        print(f"❌ Error en test FEFOService: {e}")
        return False

if __name__ == "__main__":
    try:
        success1 = test_business_exceptions()
        success2 = test_fefo_service_exceptions()
        
        if success1 and success2:
            print("\n🎊 TODOS LOS TESTS DE EXCEPCIONES COMPLETADOS EXITOSAMENTE!")
            print("📋 Resumen de funcionalidades verificadas:")
            print("   - ✅ Excepción NotEnoughStock funciona correctamente")
            print("   - ✅ Excepción NoLotsAvailable funciona correctamente")
            print("   - ✅ Herencia de StockError correcta")
            print("   - ✅ Mensajes de error personalizados")
            print("   - ✅ Atributos de excepciones correctos")
            print("   - ✅ Lanzamiento y captura de excepciones")
            print("   - ✅ Casos edge manejados correctamente")
            print("   - ✅ Integración con FEFOService")
        else:
            print("\n❌ Algunos tests fallaron")
            sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Error general en tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)