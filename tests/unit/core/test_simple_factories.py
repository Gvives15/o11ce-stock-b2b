"""
Test simple para verificar que las factories se pueden importar y usar básicamente.
"""
import sys
import os

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(__file__))

def test_factories_import():
    """Test que las factories se pueden importar."""
    try:
        from tests.factories import (
            ProductFactory,
            StockLotFactory,
            BenefitFactory,
            OrderFactory,
            FEFOProductFactory,
            PromotionProductFactory,
            StockAlertProductFactory,
        )
        print("✅ Todas las factories se importaron correctamente")
        return True
    except ImportError as e:
        print(f"❌ Error importando factories: {e}")
        return False


def test_factory_boy_available():
    """Test que factory_boy está disponible."""
    try:
        import factory
        print(f"✅ factory_boy disponible: versión {factory.__version__}")
        return True
    except ImportError as e:
        print(f"❌ factory_boy no disponible: {e}")
        return False


def test_faker_available():
    """Test que Faker está disponible."""
    try:
        import faker
        fake = faker.Faker()
        sample_name = fake.name()
        print(f"✅ Faker disponible, ejemplo: {sample_name}")
        return True
    except ImportError as e:
        print(f"❌ Faker no disponible: {e}")
        return False


def test_factories_file_exists():
    """Test que el archivo factories.py existe."""
    factories_path = os.path.join(os.path.dirname(__file__), "tests", "factories.py")
    
    if os.path.exists(factories_path):
        print(f"✅ Archivo factories.py existe: {factories_path}")
        
        # Verificar que tiene contenido
        with open(factories_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if len(content) > 1000:
            print(f"✅ factories.py tiene contenido significativo: {len(content)} caracteres")
            return True
        else:
            print(f"❌ factories.py muy pequeño: {len(content)} caracteres")
            return False
    else:
        print(f"❌ Archivo factories.py no existe: {factories_path}")
        return False


def test_fixtures_file_exists():
    """Test que el archivo fixtures.py existe."""
    fixtures_path = os.path.join(os.path.dirname(__file__), "tests", "fixtures.py")
    
    if os.path.exists(fixtures_path):
        print(f"✅ Archivo fixtures.py existe: {fixtures_path}")
        
        # Verificar que tiene contenido
        with open(fixtures_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if len(content) > 1000:
            print(f"✅ fixtures.py tiene contenido significativo: {len(content)} caracteres")
            return True
        else:
            print(f"❌ fixtures.py muy pequeño: {len(content)} caracteres")
            return False
    else:
        print(f"❌ Archivo fixtures.py no existe: {fixtures_path}")
        return False


def test_ci_workflow_exists():
    """Test que el workflow de CI existe."""
    ci_path = os.path.join(os.path.dirname(__file__), ".github", "workflows", "ci.yml")
    
    if os.path.exists(ci_path):
        print(f"✅ Workflow CI existe: {ci_path}")
        
        # Verificar que menciona Redis
        with open(ci_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'redis' in content.lower():
            print("✅ Workflow CI incluye Redis")
            return True
        else:
            print("❌ Workflow CI no incluye Redis")
            return False
    else:
        print(f"❌ Workflow CI no existe: {ci_path}")
        return False


def test_test_files_exist():
    """Test que los archivos de test existen."""
    test_files = [
        "tests/test_factories_build.py",
        "tests/test_ci_redis.py",
        "tests/test_runbook_links.py",
        "tests/test_celery_tasks.py",
        "tests/test_comprehensive_suite.py",
        "tests/settings_test.py",
    ]
    
    missing_files = []
    existing_files = []
    
    for test_file in test_files:
        full_path = os.path.join(os.path.dirname(__file__), test_file)
        if os.path.exists(full_path):
            existing_files.append(test_file)
        else:
            missing_files.append(test_file)
    
    print(f"✅ Archivos de test existentes: {len(existing_files)}")
    for file in existing_files:
        print(f"   - {file}")
    
    if missing_files:
        print(f"❌ Archivos de test faltantes: {len(missing_files)}")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    return True


if __name__ == "__main__":
    print("🧪 Ejecutando tests simples de factories y archivos...")
    
    tests = [
        test_factory_boy_available,
        test_faker_available,
        test_factories_file_exists,
        test_fixtures_file_exists,
        test_ci_workflow_exists,
        test_test_files_exist,
        test_factories_import,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"💥 Error en {test.__name__}: {e}")
            failed += 1
    
    print(f"\n📊 Resultados: {passed} pasaron, {failed} fallaron")
    
    if failed == 0:
        print("🎉 Todos los tests simples pasaron exitosamente!")
        print("✅ Factories, fixtures, CI y archivos de test están listos")
    else:
        print("❌ Algunos tests fallaron")
        exit(1)