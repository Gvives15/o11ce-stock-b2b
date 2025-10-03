# Sistema de Tests con Docker

Este documento explica cómo usar el sistema de tests integrado con Docker Compose para ejecutar tests de integración de manera aislada y confiable.

## 🐳 Configuración Docker

### Archivos principales:
- `docker/docker-compose.test.yml` - Configuración de servicios para tests
- `config/settings/test.py` - Settings específicos para tests
- `docker/scripts/test.ps1` - Script PowerShell para ejecutar tests

### Servicios de test:
- **test-db**: PostgreSQL 16 aislada (puerto 5433)
- **test-redis**: Redis 7 aislado (puerto 6380)
- **test-runner**: Contenedor para ejecutar tests

## 🚀 Uso Rápido

### Ejecutar todos los tests de integración:
```powershell
.\docker\scripts\test.ps1
```

### Ejecutar tests específicos:
```powershell
.\docker\scripts\test.ps1 -TestPath "tests/integration/test_stock_event_bus.py"
```

### Ejecutar con cobertura:
```powershell
.\docker\scripts\test.ps1 -Coverage -Verbose
```

## 📋 Comandos Disponibles

### Script PowerShell (`.\docker\scripts\test.ps1`)

| Opción | Descripción |
|--------|-------------|
| `-TestPath <path>` | Ruta específica de tests a ejecutar |
| `-Options <opts>` | Opciones adicionales para pytest |
| `-Coverage` | Generar reporte de cobertura |
| `-Verbose` | Salida verbose |
| `-Setup` | Solo levantar servicios de test |
| `-Teardown` | Solo bajar servicios de test |
| `-Help` | Mostrar ayuda |

### Ejemplos:

```powershell
# Ejecutar tests específicos con verbose
.\docker\scripts\test.ps1 -TestPath "tests/integration/" -Verbose

# Solo levantar servicios (para desarrollo)
.\docker\scripts\test.ps1 -Setup

# Solo bajar servicios
.\docker\scripts\test.ps1 -Teardown

# Tests con cobertura
.\docker\scripts\test.ps1 -Coverage

# Tests con opciones personalizadas de pytest
.\docker\scripts\test.ps1 -Options "--tb=short --maxfail=1"
```

## 🔧 Comandos Docker Compose Directos

Si prefieres usar Docker Compose directamente:

```bash
# Levantar servicios de test
docker-compose -f docker/docker-compose.test.yml -p bff-test up -d test-db test-redis

# Ejecutar tests
docker-compose -f docker/docker-compose.test.yml -p bff-test run --rm test-runner python -m pytest tests/integration/

# Bajar servicios
docker-compose -f docker/docker-compose.test.yml -p bff-test down -v
```

## 📊 Tests de Integración Disponibles

### Stock Event Bus Tests (`tests/integration/test_stock_event_bus.py`)

**Clases de test:**
- `TestStockEventBusIntegration` - Tests principales de integración
- `TestStockEventBusConfiguration` - Tests de configuración

**Tests incluidos:**
- ✅ Inicialización del EventBus
- ✅ Creación de eventos (`StockEntryRequested`, `ProductValidated`, `StockValidationRequested`)
- ✅ Funcionamiento de handlers (`StockEntryHandler`, `StockValidationHandler`)
- ✅ Serialización de eventos
- ✅ Manejo de errores
- ✅ Configuración del sistema

## 🛠️ Configuración de Settings

### Settings de Test (`config/settings/test.py`)

**Características:**
- Base de datos PostgreSQL aislada o SQLite en memoria
- Cache Redis aislado o local
- Celery en modo eager (sin cola)
- Email backend en memoria
- Logging simplificado
- Configuración de seguridad relajada para tests

**Variables de entorno:**
- `USE_TEST_DB=postgres` - Usar PostgreSQL de test
- `USE_TEST_REDIS=true` - Usar Redis de test
- `TEST_DB_HOST`, `TEST_DB_PORT`, etc. - Configuración de BD

## 🔍 Debugging

### Ver logs de servicios:
```bash
docker-compose -f docker/docker-compose.test.yml -p bff-test logs test-db
docker-compose -f docker/docker-compose.test.yml -p bff-test logs test-redis
```

### Conectar a la base de datos de test:
```bash
docker exec -it bff-test-test-db-1 psql -U test_user -d test_bff
```

### Conectar a Redis de test:
```bash
docker exec -it bff-test-test-redis-1 redis-cli
```

## 📈 Resultados de Tests

Los tests se ejecutan exitosamente con la siguiente configuración:
- **10 tests pasaron** ✅
- **0 tests fallaron** ✅
- **3 warnings** (configuración menor, no afecta funcionalidad)

### Warnings actuales:
1. `STATICFILES_STORAGE` deprecado (Django 5.1+)
2. `EventBus.initialize` coroutine warning (no afecta tests)

## 🎯 Próximos Pasos

1. **Agregar más tests de integración** para otros dominios
2. **Configurar CI/CD** para ejecutar tests automáticamente
3. **Implementar tests E2E** con Selenium/Playwright
4. **Configurar métricas de cobertura** en CI

## 💡 Tips

- Los servicios de test usan puertos diferentes (5433, 6380) para no conflictar
- La base de datos se limpia automáticamente después de cada ejecución
- Usa `-Setup` para desarrollo iterativo sin recrear servicios constantemente
- Los tests usan configuración aislada que no afecta el entorno de desarrollo