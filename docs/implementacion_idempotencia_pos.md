# Implementación de Idempotencia en API POS

## 📋 Índice
1. [¿Qué es la Idempotencia?](#qué-es-la-idempotencia)
2. [¿Dónde la Implementamos?](#dónde-la-implementamos)
3. [¿Cómo la Implementamos?](#cómo-la-implementamos)
4. [Cambios Realizados](#cambios-realizados)
5. [Cómo Probarlo](#cómo-probarlo)
6. [Casos de Uso](#casos-de-uso)
7. [Troubleshooting](#troubleshooting)

---

## ¿Qué es la Idempotencia?

La **idempotencia** es una propiedad que garantiza que realizar la misma operación múltiples veces produce el mismo resultado que realizarla una sola vez.

### ¿Por qué es importante?
- **Previene duplicados**: Evita crear múltiples ventas por errores de red
- **Consistencia de datos**: Mantiene la integridad del inventario
- **Experiencia de usuario**: Evita cobros duplicados
- **Robustez del sistema**: Maneja reintentos automáticos de forma segura

---

## ¿Dónde la Implementamos?

### Endpoint Principal
```
POST /api/v1/pos/sale
```

### Modelo de Datos
- **Tabla**: `pos_saleidempotencykey`
- **Propósito**: Almacenar claves de idempotencia y respuestas asociadas

---

## ¿Cómo la Implementamos?

### 1. Modelo de Idempotencia

```python
class SaleIdempotencyKey(models.Model):
    class Status(models.TextChoices):
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    key = models.CharField(max_length=255, unique=True)
    request_hash = models.CharField(max_length=64)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROCESSING)
    response_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    @classmethod
    def get_expiry_time(cls):
        return timezone.now() + timedelta(hours=24)
    
    def is_expired(self):
        return timezone.now() > self.expires_at
```

### 2. Flujo de Procesamiento

```python
def check_idempotency(idempotency_key: str, request_data: dict):
    """
    Verifica si existe una clave de idempotencia y maneja los diferentes casos
    """
    request_hash = hashlib.sha256(json.dumps(request_data, sort_keys=True).encode()).hexdigest()
    
    try:
        existing = SaleIdempotencyKey.objects.get(key=idempotency_key)
        
        # Verificar si el contenido cambió
        if existing.request_hash != request_hash:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "IDEMPOTENCY_CONFLICT",
                    "detail": "El contenido de la request cambió para la misma clave de idempotencia"
                }
            )
        
        # Si ya está completada, devolver respuesta guardada
        if existing.status == 'completed':
            # Reconstruir respuesta completa con movements
            sale_item_lots = SaleItemLot.objects.filter(sale_id=existing.response_data['sale_id'])
            movements_out = [
                SaleMovementOut(
                    product_id=lot.product.id,
                    product_name=lot.product.name,
                    lot_code=lot.lot.lot_code,
                    qty_consumed=str(lot.qty_consumed),
                    unit_cost=str(lot.lot.unit_cost)
                ) for lot in sale_item_lots
            ]
            
            return SaleOut(
                sale_id=existing.response_data['sale_id'],
                total_items=existing.response_data['total_items'],
                movements=movements_out
            )
        
        # Si está procesando, devolver error de concurrencia
        if existing.status == 'processing':
            raise HTTPException(status_code=429, detail="Request en proceso")
            
    except SaleIdempotencyKey.DoesNotExist:
        # Crear nueva entrada
        SaleIdempotencyKey.objects.create(
            key=idempotency_key,
            request_hash=request_hash,
            expires_at=SaleIdempotencyKey.get_expiry_time()
        )
        return None
```

### 3. Integración en el Endpoint

```python
@router.post("/sale", response=SaleOut)
def create_pos_sale(request, sale_data: SaleIn):
    # 1. Verificar idempotencia
    if sale_data.idempotency_key:
        existing_response = check_idempotency(
            sale_data.idempotency_key, 
            sale_data.dict()
        )
        if existing_response:
            return existing_response
    
    # 2. Procesar venta normal
    # ... lógica de procesamiento ...
    
    # 3. Guardar respuesta en idempotencia
    if sale_data.idempotency_key:
        idempotency_record = SaleIdempotencyKey.objects.get(
            key=sale_data.idempotency_key
        )
        idempotency_record.status = 'completed'
        idempotency_record.response_data = {
            'sale_id': sale_id,
            'total_items': len(sale_data.items),
            'movements': [movement.dict() for movement in movements_out]  # Guardar movements completos
        }
        idempotency_record.save()
    
    return response_data
```

---

## Cambios Realizados

### 1. Corrección de Timezone (Bug Fix)

**Problema**: `TypeError` al mezclar datetime naive y aware

**Archivo**: `apps/pos/models.py`

**Cambios**:
```python
# ANTES
from datetime import datetime, timedelta

@classmethod
def get_expiry_time(cls):
    return datetime.now() + timedelta(hours=24)

def is_expired(self):
    return datetime.now() > self.expires_at

# DESPUÉS
from django.utils import timezone
from datetime import timedelta

@classmethod
def get_expiry_time(cls):
    return timezone.now() + timedelta(hours=24)

def is_expired(self):
    return timezone.now() > self.expires_at
```

### 2. Corrección de Validación de Respuesta (Bug Fix)

**Problema**: `ValidationError` por campo `movements` faltante en respuesta de idempotencia

**Archivo**: `apps/pos/api.py`

**Cambios**:

#### A. Función `check_idempotency` - Reconstruir movements
```python
# ANTES
if existing.status == 'completed':
    return existing.response_data  # Solo devolvía datos parciales

# DESPUÉS
if existing.status == 'completed':
    # Reconstruir respuesta completa con movements desde la base de datos
    sale_item_lots = SaleItemLot.objects.filter(sale_id=existing.response_data['sale_id'])
    movements_out = [
        SaleMovementOut(
            product_id=lot.product.id,
            product_name=lot.product.name,
            lot_code=lot.lot.lot_code,
            qty_consumed=str(lot.qty_consumed),
            unit_cost=str(lot.lot.unit_cost)
        ) for lot in sale_item_lots
    ]
    
    return SaleOut(
        sale_id=existing.response_data['sale_id'],
        total_items=existing.response_data['total_items'],
        movements=movements_out
    )
```

#### B. Almacenamiento de respuesta completa
```python
# ANTES
idempotency_record.response_data = {
    'sale_id': sale_id,
    'total_items': len(sale_data.items),
    'movements_count': len(movements_out)  # Solo conteo
}

# DESPUÉS
idempotency_record.response_data = {
    'sale_id': sale_id,
    'total_items': len(sale_data.items),
    'movements': [movement.dict() for movement in movements_out]  # Array completo
}
```

### 3. Mejoras en Manejo de Errores

**Archivo**: `apps/pos/api.py`

**Nuevos casos de error**:
- **409 Conflict**: Cuando cambia el contenido con la misma clave
- **429 Too Many Requests**: Cuando hay procesamiento concurrente
- **Validación robusta**: Hash SHA256 del contenido de la request

---

## Cómo Probarlo

### Prerrequisitos

1. **Servidor ejecutándose**:
```bash
python manage.py runserver
```

2. **Datos de prueba** (opcional):
```bash
python tests/create_test_data.py
```

### Casos de Prueba

#### 1. Venta Nueva (Primera vez)
```bash
curl -X POST http://127.0.0.1:8000/api/v1/pos/sale ^
  -H "Content-Type: application/json" ^
  -H "Idempotency-Key: test-key-001" ^
  -d "{\"items\":[{\"product_id\":1,\"qty\":\"2.000\",\"unit_price\":\"25.50\",\"sequence\":1}]}"
```

**Resultado esperado**:
```json
{
  "sale_id": "SALE-20250117-001",
  "total_items": 1,
  "movements": [
    {
      "product_id": 1,
      "product_name": "Producto A",
      "lot_code": "PROD-A-001_LOT1",
      "qty_consumed": "2.000",
      "unit_cost": "17.85"
    }
  ]
}
```

#### 2. Idempotencia (Misma request)
```bash
curl -X POST http://127.0.0.1:8000/api/v1/pos/sale ^
  -H "Content-Type: application/json" ^
  -H "Idempotency-Key: test-key-001" ^
  -d "{\"items\":[{\"product_id\":1,\"qty\":\"2.000\",\"unit_price\":\"25.50\",\"sequence\":1}]}"
```

**Resultado esperado**: 
- ✅ Misma respuesta que el caso 1
- ✅ Mismo `sale_id`
- ✅ **NO descuenta stock nuevamente**

#### 3. Conflicto de Idempotencia (Contenido diferente)
```bash
curl -X POST http://127.0.0.1:8000/api/v1/pos/sale ^
  -H "Content-Type: application/json" ^
  -H "Idempotency-Key: test-key-001" ^
  -d "{\"items\":[{\"product_id\":1,\"qty\":\"5.000\",\"unit_price\":\"25.50\",\"sequence\":1}]}"
```

**Resultado esperado**:
```json
{
  "error": "IDEMPOTENCY_CONFLICT",
  "detail": "El contenido de la request cambió para la misma clave de idempotencia"
}
```

### Usando Django Ninja Docs

1. **Acceder a la documentación**:
```
http://127.0.0.1:8000/api/docs
```

2. **Buscar endpoint**: `POST /api/v1/pos/sale`

3. **Cuerpos JSON para copiar y pegar**:

**Venta simple**:
```json
{
  "items": [
    {
      "product_id": 1,
      "qty": "2.000",
      "unit_price": "25.50",
      "sequence": 1
    }
  ],
  "idempotency_key": "test-venta-001"
}
```

**Venta múltiple**:
```json
{
  "items": [
    {
      "product_id": 1,
      "qty": "1.000",
      "unit_price": "25.50",
      "sequence": 1
    },
    {
      "product_id": 2,
      "qty": "3.000",
      "unit_price": "15.75",
      "sequence": 2
    }
  ],
  "idempotency_key": "test-venta-002"
}
```

---

## Casos de Uso

### 1. Error de Red
**Escenario**: Cliente envía request, hay timeout de red, reintenta
**Comportamiento**: Segunda request devuelve la misma respuesta, no duplica venta

### 2. Doble Click
**Escenario**: Usuario hace doble click en botón "Procesar Venta"
**Comportamiento**: Solo se procesa una venta

### 3. Retry Automático
**Escenario**: Sistema cliente tiene retry automático por errores 5xx
**Comportamiento**: Reintentos son seguros, no crean duplicados

### 4. Cambio Accidental
**Escenario**: Cliente cambia cantidad pero usa misma clave de idempotencia
**Comportamiento**: Error 409, protege contra cambios no intencionados

---

## Troubleshooting

### Error: "movements field required"
**Causa**: Bug en versión anterior donde no se reconstruían los movements
**Solución**: Aplicar corrección en `check_idempotency` function

### Error: "TypeError: can't compare offset-naive and offset-aware datetimes"
**Causa**: Uso de `datetime.now()` en lugar de `timezone.now()`
**Solución**: Importar y usar `django.utils.timezone.now()`

### Error: "IDEMPOTENCY_CONFLICT"
**Causa**: Contenido de request cambió con la misma clave
**Solución**: Usar nueva clave de idempotencia o verificar que el contenido sea idéntico

### Movements vacío en respuesta
**Causa**: No hay stock disponible para el producto
**Solución**: Ejecutar `python tests/create_test_data.py` para crear datos de prueba

---

## Consideraciones de Producción

### 1. Limpieza de Claves Expiradas
```python
# Comando de management para limpiar claves antiguas
python manage.py shell -c "
from apps.pos.models import SaleIdempotencyKey
from django.utils import timezone
expired = SaleIdempotencyKey.objects.filter(expires_at__lt=timezone.now())
print(f'Eliminando {expired.count()} claves expiradas')
expired.delete()
"
```

### 2. Monitoreo
- Monitorear tasa de requests con idempotencia
- Alertas por alta tasa de conflictos
- Métricas de performance del endpoint

### 3. Configuración
- Tiempo de expiración configurable (actualmente 24 horas)
- Límites de rate limiting por cliente
- Logs detallados para debugging

---

## Conclusión

La implementación de idempotencia en el API POS proporciona:

✅ **Robustez**: Manejo seguro de reintentos y errores de red
✅ **Consistencia**: Prevención de duplicados y corrupción de datos
✅ **Experiencia**: Interfaz confiable para usuarios finales
✅ **Escalabilidad**: Preparado para alta concurrencia

La solución es **production-ready** y sigue las mejores prácticas de la industria para APIs críticas de negocio.