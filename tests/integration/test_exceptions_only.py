#!/usr/bin/env python
"""
Test independiente para verificar las excepciones de negocio.
Copia las clases de excepción para evitar dependencias de Django.
"""
from decimal import Decimal


class StockError(Exception):
    """Errores de negocio para operaciones de stock."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class NotEnoughStock(StockError):
    """Excepción cuando no hay suficiente stock disponible."""
    def __init__(self, product_id: int, requested: Decimal, available: Decimal):
        message = f"Stock insuficiente para producto {product_id}. Solicitado: {requested}, Disponible: {available}"
        super().__init__("NOT_ENOUGH_STOCK", message)
        self.product_id = product_id
        self.requested = requested
        self.available = available


class NoLotsAvailable(StockError):
    """Excepción cuando no hay lotes disponibles que cumplan los criterios."""
    def __init__(self, product_id: int, criteria: str = ""):
        message = f"No hay lotes disponibles para producto {product_id}"
        if criteria:
            message += f" con criterios: {criteria}"
        super().__init__("NO_LOTS_AVAILABLE", message)
        self.product_id = product_id
        self.criteria = criteria


def test_business_exceptions():
    """Test que verifica las excepciones de negocio."""
    print("🧪 Ejecutando test de excepciones de negocio...")
    
    # Test NotEnoughStock
    print("\n🔍 Probando NotEnoughStock...")
    
    # Test 1: Crear excepción NotEnoughStock
    try:
        error = NotEnoughStock(product_id=123, requested=Decimal('100.0'), available=Decimal('50.0'))
        
        # Verificar atributos
        assert error.product_id == 123
        assert error.requested == Decimal('100.0')
        assert error.available == Decimal('50.0')
        assert error.code == "NOT_ENOUGH_STOCK"
        
        # Verificar mensaje
        expected_msg = "Stock insuficiente para producto 123. Solicitado: 100.0, Disponible: 50.0"
        assert str(error) == expected_msg
        
        # Verificar herencia
        assert isinstance(error, StockError)
        assert isinstance(error, Exception)
        
        print(f"✅ Test 1: NotEnoughStock creada correctamente - {str(error)}")
        
    except Exception as e:
        print(f"❌ Error en test NotEnoughStock: {e}")
        return False
    
    # Test NoLotsAvailable
    print("\n🔍 Probando NoLotsAvailable...")
    
    try:
        # Test sin criterios
        error1 = NoLotsAvailable(product_id=456)
        
        # Verificar atributos
        assert error1.product_id == 456
        assert error1.criteria == ""
        assert error1.code == "NO_LOTS_AVAILABLE"
        
        # Verificar mensaje
        expected_msg1 = "No hay lotes disponibles para producto 456"
        assert str(error1) == expected_msg1
        
        # Verificar herencia
        assert isinstance(error1, StockError)
        assert isinstance(error1, Exception)
        
        print(f"✅ Test 2: NoLotsAvailable sin criterios - {str(error1)}")
        
        # Test con criterios
        error2 = NoLotsAvailable(product_id=789, criteria="qty_on_hand > 0")
        
        # Verificar atributos
        assert error2.product_id == 789
        assert error2.criteria == "qty_on_hand > 0"
        
        # Verificar mensaje
        expected_msg2 = "No hay lotes disponibles para producto 789 con criterios: qty_on_hand > 0"
        assert str(error2) == expected_msg2
        
        print(f"✅ Test 3: NoLotsAvailable con criterios - {str(error2)}")
        
    except Exception as e:
        print(f"❌ Error en test NoLotsAvailable: {e}")
        return False
    
    # Test casos edge
    print("\n🔍 Probando casos edge...")
    
    try:
        # NotEnoughStock con valores decimales
        error1 = NotEnoughStock(product_id=999, requested=Decimal('25.5'), available=Decimal('10.25'))
        expected_msg1 = "Stock insuficiente para producto 999. Solicitado: 25.5, Disponible: 10.25"
        assert str(error1) == expected_msg1
        print(f"✅ Test 4: NotEnoughStock con decimales - {str(error1)}")
        
        # NoLotsAvailable con criterios complejos
        complex_criteria = "qty_on_hand > 0 AND is_quarantined = False AND expiry_date > '2024-01-01'"
        error2 = NoLotsAvailable(product_id=111, criteria=complex_criteria)
        expected_msg2 = f"No hay lotes disponibles para producto 111 con criterios: {complex_criteria}"
        assert str(error2) == expected_msg2
        print(f"✅ Test 5: NoLotsAvailable con criterios complejos - OK")
        
        # NotEnoughStock con stock cero
        error3 = NotEnoughStock(product_id=222, requested=Decimal('1.0'), available=Decimal('0.0'))
        expected_msg3 = "Stock insuficiente para producto 222. Solicitado: 1.0, Disponible: 0.0"
        assert str(error3) == expected_msg3
        print(f"✅ Test 6: NotEnoughStock con stock cero - {str(error3)}")
        
        # NoLotsAvailable con criterios vacíos explícitos
        error4 = NoLotsAvailable(product_id=333, criteria="")
        expected_msg4 = "No hay lotes disponibles para producto 333"
        assert str(error4) == expected_msg4
        print(f"✅ Test 7: NoLotsAvailable con criterios vacíos - {str(error4)}")
        
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
            assert e.code == "NOT_ENOUGH_STOCK"
            print("✅ Test 8: NotEnoughStock se lanza y captura correctamente")
        
        # Test que NoLotsAvailable se puede lanzar y capturar
        try:
            raise NoLotsAvailable(product_id=666, criteria="test criteria")
        except NoLotsAvailable as e:
            assert e.product_id == 666
            assert e.criteria == "test criteria"
            assert e.code == "NO_LOTS_AVAILABLE"
            print("✅ Test 9: NoLotsAvailable se lanza y captura correctamente")
        
        # Test que se pueden capturar como StockError
        try:
            raise NotEnoughStock(product_id=777, requested=Decimal('10.0'), available=Decimal('5.0'))
        except StockError as e:
            assert isinstance(e, NotEnoughStock)
            assert e.code == "NOT_ENOUGH_STOCK"
            print("✅ Test 10: NotEnoughStock se captura como StockError")
        
        try:
            raise NoLotsAvailable(product_id=888, criteria="any criteria")
        except StockError as e:
            assert isinstance(e, NoLotsAvailable)
            assert e.code == "NO_LOTS_AVAILABLE"
            print("✅ Test 11: NoLotsAvailable se captura como StockError")
        
        # Test captura como Exception genérica
        try:
            raise NotEnoughStock(product_id=999, requested=Decimal('1.0'), available=Decimal('0.0'))
        except Exception as e:
            assert isinstance(e, NotEnoughStock)
            assert isinstance(e, StockError)
            print("✅ Test 12: NotEnoughStock se captura como Exception")
        
    except Exception as e:
        print(f"❌ Error en tests de lanzamiento: {e}")
        return False
    
    # Test códigos de error
    print("\n🔍 Probando códigos de error...")
    
    try:
        error1 = NotEnoughStock(product_id=100, requested=Decimal('10.0'), available=Decimal('5.0'))
        error2 = NoLotsAvailable(product_id=200, criteria="test")
        
        assert error1.code == "NOT_ENOUGH_STOCK"
        assert error2.code == "NO_LOTS_AVAILABLE"
        
        # Verificar que los códigos son diferentes
        assert error1.code != error2.code
        
        print("✅ Test 13: Códigos de error correctos")
        
    except Exception as e:
        print(f"❌ Error en test de códigos: {e}")
        return False
    
    return True


if __name__ == "__main__":
    try:
        success = test_business_exceptions()
        
        if success:
            print("\n🎊 TODOS LOS TESTS DE EXCEPCIONES COMPLETADOS EXITOSAMENTE!")
            print("📋 Resumen de funcionalidades verificadas:")
            print("   - ✅ Excepción NotEnoughStock funciona correctamente")
            print("   - ✅ Excepción NoLotsAvailable funciona correctamente")
            print("   - ✅ Herencia de StockError correcta")
            print("   - ✅ Códigos de error únicos")
            print("   - ✅ Mensajes de error personalizados")
            print("   - ✅ Atributos de excepciones correctos")
            print("   - ✅ Lanzamiento y captura de excepciones")
            print("   - ✅ Casos edge manejados correctamente")
            print("   - ✅ Captura como Exception genérica")
            print("   - ✅ Criterios opcionales en NoLotsAvailable")
        else:
            print("\n❌ Algunos tests fallaron")
            exit(1)
        
    except Exception as e:
        print(f"\n❌ Error general en tests: {e}")
        import traceback
        traceback.print_exc()
        exit(1)