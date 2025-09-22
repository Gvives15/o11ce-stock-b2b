# Catálogo de Productos y Beneficios

## Descripción

Módulo de catálogo que gestiona productos y beneficios (descuentos y combos) con validaciones robustas y API optimizada.

## Modelos

### Product (Producto)

**Campos principales:**
- `code` (str): Código único del producto
- `name` (str): Nombre del producto
- `price` (Decimal): Precio unitario
- `tax_rate` (Decimal): Tasa de impuesto (0-100%)
- `unit` (str): Unidad de medida (UN/KG/LT)
- `brand` (str, opcional): Marca del producto
- `category` (str, opcional): Categoría del producto
- `is_active` (bool): Estado activo/inactivo
- `created_at`, `updated_at`: Timestamps automáticos

**Validaciones:**
- ✅ Precio debe ser mayor a 0
- ✅ Tasa de impuesto entre 0 y 100%
- ✅ Código único en el sistema
- ✅ Unidades válidas: UN, KG, LT

**Índices optimizados:**
- Índice GIN en `name` para búsqueda de texto (PostgreSQL)
- Índice en `brand` para filtros rápidos
- Índice compuesto en `category` + `is_active`

### Benefit (Beneficio)

**Campos principales:**
- `name` (str): Nombre del beneficio
- `type` (str): Tipo de beneficio (discount/combo)
- `segment` (str): Segmento objetivo (retail/wholesale)
- `value` (Decimal, opcional): Porcentaje de descuento
- `combo_spec` (JSON, opcional): Especificación del combo
- `active_from`, `active_to` (Date): Período de vigencia
- `is_active` (bool): Estado activo/inactivo
- `created_at`, `updated_at`: Timestamps automáticos

**Validaciones:**
- ✅ Beneficios tipo 'discount' requieren `value` (0-100%)
- ✅ Beneficios tipo 'combo' requieren `combo_spec`
- ✅ `active_to` debe ser posterior a `active_from`
- ✅ Segmentos válidos: retail, wholesale

**Ejemplo combo_spec:**
```json
{
  "buy": 3,
  "pay": 2,
  "category": "Lácteos",
  "description": "Llevá 3 productos lácteos y pagá solo 2"
}
```

## API Endpoints

### GET /api/catalog/products

**Descripción:** Lista productos con filtros y paginación.

**Parámetros de consulta:**
- `search` (str): Busca en código, nombre o marca
- `brand` (str): Filtra por marca
- `category` (str): Filtra por categoría
- `is_active` (bool): Filtra por estado activo
- `page` (int): Número de página (default: 1)
- `page_size` (int): Elementos por página (default: 20)

**Ejemplo de uso:**
```bash
GET /api/catalog/products?search=coca&is_active=true
GET /api/catalog/products?category=Bebidas&page=2
```

**Respuesta:**
```json
[
  {
    "id": 1,
    "code": "COCA-355",
    "name": "Coca Cola 355ml",
    "price": "2.50",
    "tax_rate": "21.00",
    "unit": "UN",
    "brand": "Coca Cola",
    "category": "Bebidas",
    "is_active": true,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

### GET /api/catalog/offers

**Descripción:** Lista beneficios activos para la fecha actual.

**Parámetros de consulta:**
- `segment` (str): Filtra por segmento (retail/wholesale)
- `date_filter` (str): Fecha en formato ISO (default: hoy)

**Ejemplo de uso:**
```bash
GET /api/catalog/offers?segment=retail
GET /api/catalog/offers?segment=wholesale&date_filter=2024-06-15
```

**Respuesta:**
```json
[
  {
    "id": 1,
    "name": "Descuento 10% Bebidas",
    "type": "discount",
    "segment": "retail",
    "value": "10.00",
    "combo_spec": null,
    "active_from": "2024-01-01",
    "active_to": "2024-12-31",
    "is_active": true
  }
]
```

## Helpers Utilitarios

### apply_discount(price, value_pct)

Aplica descuento porcentual con redondeo a 2 decimales.

```python
from apps.catalog.utils import apply_discount

# Aplicar 10% de descuento a $100.00
discounted_price = apply_discount(Decimal("100.00"), Decimal("10.00"))
# Resultado: Decimal("90.00")
```

### get_active_benefits(segment, date)

Obtiene beneficios activos con consulta optimizada (sin N+1).

```python
from apps.catalog.utils import get_active_benefits

# Beneficios activos para retail hoy
benefits = get_active_benefits(segment="retail")

# Beneficios para fecha específica
benefits = get_active_benefits(segment="wholesale", filter_date=date(2024, 6, 15))
```

## Comandos Útiles

### Migraciones
```bash
python manage.py makemigrations catalog
python manage.py migrate
```

### Cargar datos de prueba
```bash
python manage.py loaddata apps/catalog/fixtures/catalog_seed.json
```

### Ejecutar tests
```bash
pytest apps/catalog -v
```

### Activar extensión PostgreSQL (automático)
La extensión `pg_trgm` se activa automáticamente con las migraciones.

## Observabilidad

### Logs de acceso
Los endpoints `/products` y `/offers` registran:
- Request ID para trazabilidad
- Parámetros de consulta
- Número de resultados devueltos
- Métricas de uso

**Formato de logs:**
```
INFO API_ACCESS /products - Request ID: abc123, Search: coca, Brand: None, Category: Bebidas
INFO METRIC products_endpoint_hit 1 request_id=abc123
INFO API_RESPONSE /products - Request ID: abc123, Results: 5
```

### Métricas
- `products_endpoint_hit`: Contador de accesos a /products
- `offers_endpoint_hit`: Contador de accesos a /offers

## Limitaciones del MVP

⚠️ **Limitaciones actuales:**

1. **Asignación de beneficios:** Los beneficios no se asignan automáticamente a SKUs específicos. La lógica de aplicación debe implementarse en el módulo de checkout.

2. **Combos informativos:** Los combos son descriptivos. La validación de elegibilidad y cálculo de descuentos debe implementarse en el carrito de compras.

3. **Inventario:** No hay control de stock. Los productos pueden aparecer como disponibles sin validar existencias.

4. **Precios dinámicos:** Los precios son fijos. No hay soporte para precios por volumen o segmento.

5. **Geolocalización:** Los beneficios no consideran ubicación geográfica del cliente.

## Performance

### Objetivos de rendimiento
- ✅ `/products` responde en <300ms con dataset de prueba
- ✅ `/offers` responde en <300ms con dataset de prueba
- ✅ Caché de 90s para productos, 60s para ofertas
- ✅ Índices optimizados para búsquedas frecuentes

### Optimizaciones implementadas
- Índices GIN para búsqueda de texto completo
- Caché en memoria para consultas frecuentes
- Paginación para evitar resultados masivos
- Select related para evitar consultas N+1

## Datos de Prueba

El fixture incluye:
- **20 productos** variados (diferentes unidades, categorías, marcas)
- **5 beneficios** (2 descuentos, 2 combos, 1 inactivo)
- Datos realistas para testing y desarrollo

**Categorías incluidas:** Bebidas, Lácteos, Panadería, Granos, Aceites, Frutas, Verduras, Carnes, Limpieza, Higiene

**Marcas incluidas:** Coca Cola, Pepsi, La Serenísima, Bimbo, Gallo Oro, Natura, Sancor, Villavicencio, Matarazzo, Ledesma, La Virginia, Milkaut, Magistral, Dove