#!/usr/bin/env python
"""
Script para manejar archivos que quedaron fuera de la reorganización de tests.
Categoriza y proporciona opciones para scripts de utilidad y tests no migrados.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

class RemainingFilesHandler:
    """Maneja archivos que quedaron fuera de la reorganización inicial."""
    
    def __init__(self, tests_dir: str = "tests"):
        self.tests_dir = Path(tests_dir)
        self.utility_scripts = []
        self.unmigrated_tests = []
        self.other_files = []
    
    def analyze_remaining_files(self) -> Dict[str, List[str]]:
        """Analiza y categoriza archivos restantes en el directorio tests."""
        print("🔍 Analizando archivos restantes...")
        
        # Buscar archivos Python en el directorio raíz de tests
        for file_path in self.tests_dir.glob("*.py"):
            if file_path.name in ["conftest.py", "reorganize_tests.py", "__init__.py", "handle_remaining_files.py"]:
                continue
                
            file_content = self._read_file_safely(file_path)
            category = self._categorize_file(file_path.name, file_content)
            
            if category == "utility":
                self.utility_scripts.append(str(file_path))
            elif category == "test":
                self.unmigrated_tests.append(str(file_path))
            else:
                self.other_files.append(str(file_path))
        
        return {
            "utility_scripts": self.utility_scripts,
            "unmigrated_tests": self.unmigrated_tests,
            "other_files": self.other_files
        }
    
    def _read_file_safely(self, file_path: Path) -> str:
        """Lee un archivo de forma segura."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"⚠️  Error leyendo {file_path}: {e}")
            return ""
    
    def _categorize_file(self, filename: str, content: str) -> str:
        """Categoriza un archivo basándose en su nombre y contenido."""
        # Scripts de utilidad
        if filename.startswith(("check_", "create_", "setup_", "verify_")):
            return "utility"
        
        # Tests que no siguen convención estándar
        if filename.startswith("test_") and ("def test_" in content or "class Test" in content):
            return "test"
        
        # Scripts que parecen ser de verificación o setup
        if any(keyword in content.lower() for keyword in [
            "print(", "verificar", "crear datos", "setup", "check", "verify"
        ]) and "def test_" not in content:
            return "utility"
        
        return "other"
    
    def create_utilities_directory(self):
        """Crea un directorio para scripts de utilidad."""
        utilities_dir = self.tests_dir / "utilities"
        utilities_dir.mkdir(exist_ok=True)
        
        # Crear __init__.py con documentación
        init_file = utilities_dir / "__init__.py"
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write('''"""
Scripts de utilidad para testing y verificación del sistema BFF.

Estos scripts NO son tests unitarios, sino herramientas de:
- Verificación del estado del sistema
- Creación de datos de prueba
- Diagnóstico y debugging
- Setup de entornos de desarrollo

Uso:
    python tests/utilities/check_b2b_orders.py
    python tests/utilities/create_test_data.py
"""
''')
        
        return utilities_dir
    
    def migrate_utility_scripts(self):
        """Migra scripts de utilidad al directorio utilities."""
        if not self.utility_scripts:
            print("✅ No hay scripts de utilidad para migrar")
            return
        
        utilities_dir = self.create_utilities_directory()
        print(f"📁 Creando directorio: {utilities_dir}")
        
        for script_path in self.utility_scripts:
            script_file = Path(script_path)
            destination = utilities_dir / script_file.name
            
            try:
                shutil.move(str(script_file), str(destination))
                print(f"✅ Migrado: {script_file.name} -> utilities/")
            except Exception as e:
                print(f"❌ Error migrando {script_file.name}: {e}")
    
    def migrate_unmigrated_tests(self):
        """Migra tests que no fueron categorizados automáticamente."""
        if not self.unmigrated_tests:
            print("✅ No hay tests sin migrar")
            return
        
        print("\n🧪 Migrando tests restantes...")
        
        for test_path in self.unmigrated_tests:
            test_file = Path(test_path)
            suggestion = self._suggest_test_location(test_file.name)
            destination_dir = self.tests_dir / suggestion
            destination_dir.mkdir(parents=True, exist_ok=True)
            destination = destination_dir / test_file.name
            
            try:
                shutil.move(str(test_file), str(destination))
                print(f"✅ Migrado: {test_file.name} -> {suggestion}/")
            except Exception as e:
                print(f"❌ Error migrando {test_file.name}: {e}")
    
    def _suggest_test_location(self, filename: str) -> str:
        """Sugiere la ubicación apropiada para un test."""
        filename_lower = filename.lower()
        
        # Mapeo de patrones a directorios
        patterns = {
            "integration": ["integration", "fefo_integration", "api"],
            "unit/core": ["simple", "basic", "core"],
            "security": ["auth", "security", "permissions"],
            "performance": ["performance", "load", "stress"],
            "e2e": ["e2e", "end_to_end", "full"],
        }
        
        for directory, keywords in patterns.items():
            if any(keyword in filename_lower for keyword in keywords):
                return directory
        
        return "integration"  # Default
    
    def clean_duplicates(self):
        """Identifica y elimina archivos duplicados."""
        print("\n🧹 Buscando archivos duplicados...")
        
        # Buscar archivos con nombres similares en diferentes ubicaciones
        all_files = {}
        for root, dirs, files in os.walk(self.tests_dir):
            for file in files:
                if file.endswith('.py') and file.startswith('test_'):
                    if file not in all_files:
                        all_files[file] = []
                    all_files[file].append(os.path.join(root, file))
        
        duplicates_found = False
        for filename, paths in all_files.items():
            if len(paths) > 1:
                duplicates_found = True
                print(f"🔍 Duplicado encontrado: {filename}")
                for i, path in enumerate(paths):
                    print(f"  {i+1}. {path}")
                
                # Mantener solo el que está en la estructura organizada
                organized_path = None
                root_path = None
                
                for path in paths:
                    if any(subdir in path for subdir in ['unit/', 'integration/', 'security/', 'e2e/', 'performance/']):
                        organized_path = path
                    elif path.startswith(str(self.tests_dir) + os.sep) and path.count(os.sep) == 1:
                        root_path = path
                
                if organized_path and root_path:
                    try:
                        os.remove(root_path)
                        print(f"  ✅ Eliminado duplicado: {root_path}")
                    except Exception as e:
                        print(f"  ❌ Error eliminando {root_path}: {e}")
        
        if not duplicates_found:
            print("✅ No se encontraron duplicados")
    
    def create_usage_guide(self):
        """Crea una guía de uso para archivos restantes."""
        guide_path = self.tests_dir / "REMAINING_FILES_GUIDE.md"
        
        with open(guide_path, 'w', encoding='utf-8') as f:
            f.write("""# 📋 Guía de Archivos Restantes

## 🛠️ Scripts de Utilidad (utilities/)

### Propósito
Scripts para verificación, diagnóstico y setup del sistema.

### Uso
```bash
# Verificar pedidos B2B
python tests/utilities/check_b2b_orders.py

# Verificar inventario
python tests/utilities/check_inventory.py

# Crear datos de prueba
python tests/utilities/create_test_data.py
```

### Cuándo usar
- **Desarrollo**: Verificar funcionalidad durante desarrollo
- **Debugging**: Diagnosticar problemas en el sistema
- **Setup**: Preparar datos para testing manual
- **CI/CD**: Verificaciones pre/post deployment

## 🧪 Tests Migrados

Todos los tests han sido migrados a su estructura organizada:

```bash
# Ejecutar por categoría
pytest tests/unit/ -v          # Tests unitarios
pytest tests/integration/ -v   # Tests de integración
pytest tests/security/ -v      # Tests de seguridad
pytest tests/e2e/ -v          # Tests end-to-end
```

## 📊 Comandos Útiles

```bash
# Ver estructura completa
find tests/ -name "*.py" -type f

# Ejecutar utilities (no son tests)
python tests/utilities/check_b2b_orders.py

# Ejecutar todos los tests
pytest tests/ -v

# Coverage completo
pytest tests/ --cov=apps/ --cov-report=html
```

## 🔄 Próximos Pasos

1. ✅ **Scripts migrados** - Utilities organizados
2. ✅ **Tests migrados** - Estructura organizada
3. ✅ **Duplicados eliminados** - Sin archivos redundantes
4. 🎯 **Usar estructura** - Seguir convenciones establecidas
""")
        
        print(f"📖 Guía creada: {guide_path}")
    
    def run_complete_cleanup(self):
        """Ejecuta el proceso completo de limpieza y organización."""
        print("🚀 LIMPIEZA COMPLETA DE ARCHIVOS RESTANTES")
        print("=" * 50)
        
        # Analizar archivos
        results = self.analyze_remaining_files()
        
        # Mostrar resultados
        print(f"\n📊 ARCHIVOS ENCONTRADOS:")
        print(f"  🛠️  Scripts de utilidad: {len(results['utility_scripts'])}")
        print(f"  🧪 Tests no migrados: {len(results['unmigrated_tests'])}")
        print(f"  📄 Otros archivos: {len(results['other_files'])}")
        
        # Ejecutar migraciones
        if results['utility_scripts'] or results['unmigrated_tests']:
            print(f"\n🔄 Ejecutando migraciones automáticas...")
            
            # Migrar utilities
            self.migrate_utility_scripts()
            
            # Migrar tests
            self.migrate_unmigrated_tests()
            
            # Limpiar duplicados
            self.clean_duplicates()
            
            # Crear guía
            self.create_usage_guide()
            
            print(f"\n✅ Limpieza completada!")
        else:
            print(f"\n✅ No hay archivos para migrar")
        
        return results

def main():
    """Función principal."""
    handler = RemainingFilesHandler()
    
    # Ejecutar limpieza completa
    results = handler.run_complete_cleanup()
    
    print(f"\n🎯 RESUMEN FINAL:")
    print(f"  📁 Estructura organizada: tests/")
    print(f"  🛠️  Utilities: tests/utilities/")
    print(f"  🧪 Tests: organizados por categoría")
    print(f"  🧹 Duplicados: eliminados")
    print(f"  📖 Guía: REMAINING_FILES_GUIDE.md")

if __name__ == "__main__":
    main()