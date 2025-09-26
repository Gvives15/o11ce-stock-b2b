# 📋 Guía de Archivos Restantes

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
