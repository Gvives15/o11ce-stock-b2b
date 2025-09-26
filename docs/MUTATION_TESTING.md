# Mutation Testing Setup

Este documento describe la configuración y uso del mutation testing en el proyecto usando `cosmic-ray`.

## ¿Qué es Mutation Testing?

El mutation testing es una técnica de testing que evalúa la calidad de los tests introduciendo pequeños cambios (mutaciones) en el código y verificando si los tests detectan estos cambios. Un buen conjunto de tests debería "matar" (detectar) la mayoría de las mutaciones.

## Configuración

### Archivos de Configuración

- **`cosmic-ray.toml`**: Configuración principal de cosmic-ray
- **`scripts/mutation_score.py`**: Script para calcular y reportar mutation scores
- **`.github/workflows/mutation-testing.yml`**: Workflow de CI para mutation testing automático

### Módulos Objetivo

El mutation testing está configurado para ejecutarse en los siguientes módulos críticos:

- `apps/catalog/pricing.py` - Lógica de precios y métricas
- `apps/catalog/utils.py` - Utilidades del catálogo
- `apps/core/metrics.py` - Sistema de métricas
- `apps/orders/services.py` - Servicios de órdenes

## Uso Local

### Ejecutar Mutation Testing

```bash
# 1. Inicializar sesión de mutation testing
cosmic-ray init cosmic-ray.toml session.sqlite

# 2. Ejecutar mutaciones
cosmic-ray exec cosmic-ray.toml session.sqlite

# 3. Ver resultados detallados
cosmic-ray dump session.sqlite | python scripts/mutation_score.py --format detailed

# 4. Ver solo el score
cosmic-ray dump session.sqlite | python scripts/mutation_score.py --format score_only
```

### Opciones del Script de Mutation Score

```bash
# Formato detallado (por defecto)
python scripts/mutation_score.py --format detailed

# Formato resumen
python scripts/mutation_score.py --format summary

# Solo el score numérico
python scripts/mutation_score.py --format score_only

# Cambiar threshold (por defecto 80%)
python scripts/mutation_score.py --threshold 90.0

# Salir con código de error si no pasa el threshold
python scripts/mutation_score.py --exit-code
```

## CI/CD Integration

### GitHub Actions Workflow

El workflow de mutation testing se ejecuta automáticamente en:

1. **Pull Requests** que modifican archivos en los módulos objetivo
2. **Manualmente** usando `workflow_dispatch` con parámetro opcional `target_module`

### Proceso del Workflow

1. **Setup**: Configura Python 3.11, PostgreSQL, Redis
2. **Baseline Tests**: Ejecuta tests normales para verificar que pasan
3. **Module Detection**: Determina qué módulo testear basado en archivos modificados
4. **Mutation Testing**: Ejecuta cosmic-ray con timeout de 30 minutos
5. **Score Calculation**: Calcula mutation score usando el script dedicado
6. **Threshold Check**: Verifica que el score sea >= 80%
7. **Reporting**: Genera reporte y comenta en el PR
8. **Artifacts**: Sube resultados como artifacts

### Threshold de Calidad

- **Mínimo requerido**: 80%
- **Recomendado**: 90%+

Un mutation score alto indica que los tests son efectivos detectando cambios en el código.

## Interpretación de Resultados

### Estados de Mutaciones

- **Killed**: La mutación fue detectada por los tests (✅ bueno)
- **Survived**: La mutación no fue detectada (❌ malo)
- **Incompetent**: La mutación causó errores de sintaxis
- **Timeout**: La mutación causó que los tests no terminen

### Mutation Score

```
Mutation Score = (Killed / Total) × 100%
```

### Ejemplo de Reporte

```
Mutation Testing Results:
========================
Total mutations: 140
Killed: 135
Survived: 5
Incompetent: 0
Timeout: 0

Mutation Score: 96.4%
✅ Good mutation score (>= 80.0%)
```

## Troubleshooting

### Problemas Comunes

1. **Tests fallan antes de mutation testing**
   - Verificar que todos los tests pasen normalmente
   - Revisar configuración de base de datos y servicios

2. **Mutation score muy bajo**
   - Revisar cobertura de tests
   - Añadir tests para casos edge
   - Verificar assertions en tests existentes

3. **Timeouts frecuentes**
   - Revisar tests que pueden tener loops infinitos
   - Optimizar tests lentos
   - Ajustar timeout en configuración

4. **Módulo no encontrado**
   - Verificar paths en `cosmic-ray.toml`
   - Asegurar que los módulos existen y son importables

### Configuración de Debugging

Para debugging local, usar:

```bash
# Ver mutaciones generadas sin ejecutar
cosmic-ray init cosmic-ray.toml debug.sqlite
cosmic-ray dump debug.sqlite | head -10

# Ejecutar solo algunas mutaciones
cosmic-ray exec cosmic-ray.toml debug.sqlite --timeout 60
```

## Mejores Prácticas

1. **Ejecutar localmente** antes de hacer push
2. **Revisar mutaciones supervivientes** para mejorar tests
3. **Mantener threshold alto** (>= 80%)
4. **Actualizar configuración** cuando se añadan nuevos módulos críticos
5. **Monitorear tiempo de ejecución** para optimizar CI

## Referencias

- [Cosmic Ray Documentation](https://cosmic-ray.readthedocs.io/)
- [Mutation Testing Concepts](https://en.wikipedia.org/wiki/Mutation_testing)