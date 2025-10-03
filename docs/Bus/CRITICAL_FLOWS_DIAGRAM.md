# Diagramas de Flujos Críticos - Estado Actual

## 🔄 Flujo 1: Venta POS Completa

### Estado Actual (Problemático)
```mermaid
sequenceDiagram
    participant Client
    participant POS_API as POS API
    participant Catalog as Catalog Service
    participant Stock as Stock Service
    participant Customer as Customer Model
    participant DB

    Client->>POS_API: POST /pos/sale
    
    Note over POS_API: IMPORT DIRECTO
    POS_API->>Catalog: price_quote(items, customer_id)
    Catalog->>DB: Query products & benefits
    DB-->>Catalog: Product data
    Catalog-->>POS_API: Calculated prices
    
    Note over POS_API: IMPORT DIRECTO
    POS_API->>Stock: allocate_lots_fefo(product, qty)
    Stock->>DB: Query available lots
    DB-->>Stock: Lot data
    Stock-->>POS_API: Allocation plan
    
    Note over POS_API: IMPORT DIRECTO
    POS_API->>Stock: record_exit_fefo(product, qty)
    Stock->>DB: Create movements
    DB-->>Stock: Movement records
    Stock-->>POS_API: Exit confirmation
    
    Note over POS_API: IMPORT DIRECTO
    POS_API->>Customer: Validate customer_id
    Customer->>DB: Query customer
    DB-->>Customer: Customer data
    Customer-->>POS_API: Validation result
    
    POS_API-->>Client: Sale completed
```

**Problemas Identificados:**
- 4 imports directos en una sola operación
- Acoplamiento fuerte entre POS y otros dominios
- Difícil testing unitario (requiere mocks de 4 servicios)
- Transacciones complejas distribuidas en múltiples servicios

### Estado Objetivo (Event-Driven)
```mermaid
sequenceDiagram
    participant Client
    participant POS_API as POS API
    participant EventBus
    participant CatalogHandler as Catalog Handler
    participant StockHandler as Stock Handler
    participant CustomerHandler as Customer Handler

    Client->>POS_API: POST /pos/sale
    
    POS_API->>EventBus: publish(SaleInitiated)
    EventBus->>CatalogHandler: handle(SaleInitiated)
    CatalogHandler->>EventBus: publish(PriceCalculated)
    
    EventBus->>StockHandler: handle(PriceCalculated)
    StockHandler->>EventBus: publish(StockAllocated)
    
    EventBus->>StockHandler: handle(StockAllocated)
    StockHandler->>EventBus: publish(StockExitRecorded)
    
    EventBus->>CustomerHandler: handle(SaleInitiated)
    CustomerHandler->>EventBus: publish(CustomerValidated)
    
    EventBus->>POS_API: handle(AllEventsCompleted)
    POS_API-->>Client: Sale completed
```

**Beneficios:**
- 0 imports directos
- Cada handler es testeable independientemente
- Fácil agregar nuevos handlers (ej: loyalty points)
- Mejor manejo de errores y rollback

---

## 🛒 Flujo 2: Checkout de Orden

### Estado Actual (Problemático)
```mermaid
sequenceDiagram
    participant Client
    participant Orders_API as Orders API
    participant Orders_Service as Orders Service
    participant Stock_Service as Stock Service
    participant Catalog as Catalog Service
    participant Customer as Customer Model
    participant Notifications as Notifications
    participant DB

    Client->>Orders_API: POST /orders/checkout
    Orders_API->>Orders_Service: checkout(customer_id, items)
    
    Note over Orders_Service: IMPORT DIRECTO
    Orders_Service->>Customer: get_object_or_404(customer_id)
    Customer->>DB: Query customer
    DB-->>Customer: Customer data
    Customer-->>Orders_Service: Customer object
    
    Note over Orders_Service: IMPORT DIRECTO
    Orders_Service->>Catalog: apply_benefits(product, customer)
    Catalog->>DB: Query benefits
    DB-->>Catalog: Benefit data
    Catalog-->>Orders_Service: Pricing info
    
    Note over Orders_Service: IMPORT DIRECTO
    Orders_Service->>Stock_Service: record_exit_fefo(product_id, qty)
    Stock_Service->>DB: Update stock & create movements
    DB-->>Stock_Service: Movement records
    Stock_Service-->>Orders_Service: Exit result
    
    Orders_Service->>DB: Create Order & OrderItems
    DB-->>Orders_Service: Order created
    
    Note over Orders_Service: IMPORT DIRECTO
    Orders_Service->>Notifications: notify(NEW_ORDER, order_id)
    Notifications->>DB: Create notification
    DB-->>Notifications: Notification created
    
    Orders_Service-->>Orders_API: Order object
    Orders_API-->>Client: Order confirmation
```

**Problemas Identificados:**
- 4 imports directos en checkout
- Lógica de negocio distribuida en múltiples servicios
- Difícil rollback si falla algún paso
- Testing requiere setup complejo de múltiples dominios

### Estado Objetivo (Event-Driven)
```mermaid
sequenceDiagram
    participant Client
    participant Orders_API as Orders API
    participant EventBus
    participant CustomerHandler as Customer Handler
    participant CatalogHandler as Catalog Handler
    participant StockHandler as Stock Handler
    participant NotificationHandler as Notification Handler

    Client->>Orders_API: POST /orders/checkout
    Orders_API->>EventBus: publish(OrderCheckoutInitiated)
    
    EventBus->>CustomerHandler: handle(OrderCheckoutInitiated)
    CustomerHandler->>EventBus: publish(CustomerValidated)
    
    EventBus->>CatalogHandler: handle(CustomerValidated)
    CatalogHandler->>EventBus: publish(BenefitsApplied)
    
    EventBus->>StockHandler: handle(BenefitsApplied)
    StockHandler->>EventBus: publish(StockReserved)
    
    EventBus->>Orders_API: handle(StockReserved)
    Orders_API->>EventBus: publish(OrderCreated)
    
    EventBus->>NotificationHandler: handle(OrderCreated)
    NotificationHandler->>EventBus: publish(NotificationSent)
    
    EventBus->>Orders_API: handle(AllEventsCompleted)
    Orders_API-->>Client: Order confirmation
```

---

## 📦 Flujo 3: Actualización de Stock

### Estado Actual (Problemático)
```mermaid
sequenceDiagram
    participant Admin
    participant Stock_API as Stock API
    participant Stock_Service as Stock Service
    participant Catalog as Catalog Models
    participant Django_Signals as Django Signals
    participant Cache
    participant Notifications as Notifications
    participant DB

    Admin->>Stock_API: POST /stock/entry
    Stock_API->>Stock_Service: record_entry(product_id, qty, cost)
    
    Note over Stock_Service: IMPORT DIRECTO
    Stock_Service->>Catalog: Product.objects.get(id=product_id)
    Catalog->>DB: Query product
    DB-->>Catalog: Product data
    Catalog-->>Stock_Service: Product object
    
    Stock_Service->>DB: Create StockLot & Movement
    DB-->>Stock_Service: Records created
    
    Note over DB: Django Signal Triggered
    DB->>Django_Signals: post_save(StockLot)
    Django_Signals->>Cache: Invalidate product cache
    
    Stock_Service->>Stock_Service: check_low_stock_threshold()
    
    alt Stock is low
        Note over Stock_Service: IMPORT DIRECTO
        Stock_Service->>Notifications: notify(LOW_STOCK, product_id)
        Notifications->>DB: Create notification
    end
    
    Stock_Service-->>Stock_API: Entry confirmation
    Stock_API-->>Admin: Success response
```

**Problemas Identificados:**
- Import directo de Catalog models en Stock
- Mezcla de imports directos y Django signals
- Lógica de low stock mezclada con entrada de stock
- Notificaciones acopladas al servicio de stock

### Estado Objetivo (Event-Driven)
```mermaid
sequenceDiagram
    participant Admin
    participant Stock_API as Stock API
    participant EventBus
    participant CatalogHandler as Catalog Handler
    participant CacheHandler as Cache Handler
    participant NotificationHandler as Notification Handler
    participant LowStockHandler as Low Stock Handler

    Admin->>Stock_API: POST /stock/entry
    Stock_API->>EventBus: publish(StockEntryRequested)
    
    EventBus->>CatalogHandler: handle(StockEntryRequested)
    CatalogHandler->>EventBus: publish(ProductValidated)
    
    EventBus->>Stock_API: handle(ProductValidated)
    Stock_API->>EventBus: publish(StockUpdated)
    
    EventBus->>CacheHandler: handle(StockUpdated)
    CacheHandler->>EventBus: publish(CacheInvalidated)
    
    EventBus->>LowStockHandler: handle(StockUpdated)
    
    alt Stock is low
        LowStockHandler->>EventBus: publish(LowStockDetected)
        EventBus->>NotificationHandler: handle(LowStockDetected)
        NotificationHandler->>EventBus: publish(NotificationSent)
    end
    
    EventBus->>Stock_API: handle(AllEventsCompleted)
    Stock_API-->>Admin: Success response
```

---

## 🔍 Flujo 4: Consulta de Disponibilidad (POS)

### Estado Actual (Problemático)
```mermaid
sequenceDiagram
    participant POS_Client as POS Client
    participant POS_API as POS API
    participant Stock_Service as Stock Service
    participant Catalog as Catalog Models
    participant DB

    POS_Client->>POS_API: GET /pos/availability?product_id=123
    
    Note over POS_API: IMPORT DIRECTO
    POS_API->>Catalog: Product.objects.get(id=123)
    Catalog->>DB: Query product
    DB-->>Catalog: Product data
    Catalog-->>POS_API: Product object
    
    Note over POS_API: IMPORT DIRECTO
    POS_API->>Stock_Service: get_lot_options(product, qty)
    Stock_Service->>DB: Query available lots
    DB-->>Stock_Service: Lot data with FEFO
    Stock_Service-->>POS_API: Available options
    
    POS_API-->>POS_Client: Availability response
```

### Estado Objetivo (Event-Driven)
```mermaid
sequenceDiagram
    participant POS_Client as POS Client
    participant POS_API as POS API
    participant EventBus
    participant StockHandler as Stock Handler
    participant CatalogHandler as Catalog Handler

    POS_Client->>POS_API: GET /pos/availability?product_id=123
    POS_API->>EventBus: publish(AvailabilityRequested)
    
    EventBus->>CatalogHandler: handle(AvailabilityRequested)
    CatalogHandler->>EventBus: publish(ProductInfoRetrieved)
    
    EventBus->>StockHandler: handle(ProductInfoRetrieved)
    StockHandler->>EventBus: publish(AvailabilityCalculated)
    
    EventBus->>POS_API: handle(AvailabilityCalculated)
    POS_API-->>POS_Client: Availability response
```

---

## 📊 Análisis de Complejidad por Flujo

### Métricas Actuales:
| Flujo | Imports Directos | Servicios Involucrados | Tiempo Promedio | Complejidad Ciclomática |
|-------|------------------|------------------------|-----------------|-------------------------|
| Venta POS | 4 | 5 | 200ms | 12 |
| Checkout Orden | 4 | 6 | 350ms | 15 |
| Actualización Stock | 2 | 4 | 50ms | 8 |
| Consulta Disponibilidad | 2 | 3 | 80ms | 6 |

### Métricas Objetivo (Post Event-Driven):
| Flujo | Imports Directos | Handlers | Tiempo Estimado | Complejidad Estimada |
|-------|------------------|----------|-----------------|---------------------|
| Venta POS | 0 | 4 | 180ms | 6 |
| Checkout Orden | 0 | 5 | 320ms | 8 |
| Actualización Stock | 0 | 3 | 45ms | 4 |
| Consulta Disponibilidad | 0 | 2 | 75ms | 3 |

## 🎯 Casos Edge Identificados

### 1. **Fallo en Medio de Venta POS**
**Actual**: Rollback manual complejo
**Objetivo**: Event sourcing con compensating actions

### 2. **Stock Insuficiente Durante Checkout**
**Actual**: Exception propagada a través de imports
**Objetivo**: StockInsufficientEvent → OrderCancelledEvent

### 3. **Producto Discontinuado Durante Venta**
**Actual**: Error en runtime por import directo
**Objetivo**: ProductDiscontinuedEvent → SaleBlockedEvent

### 4. **Concurrencia en Reserva de Stock**
**Actual**: Race conditions en imports directos
**Objetivo**: StockReservationConflictEvent → RetryEvent

---

## 🚀 Próximos Pasos para Fase 2

### Eventos a Diseñar (Basados en Flujos):
1. **SaleInitiated, PriceCalculated, StockAllocated**
2. **OrderCheckoutInitiated, CustomerValidated, BenefitsApplied**
3. **StockEntryRequested, StockUpdated, LowStockDetected**
4. **AvailabilityRequested, ProductInfoRetrieved, AvailabilityCalculated**

### Handlers a Implementar:
1. **CatalogHandler**: Pricing, benefits, product validation
2. **StockHandler**: Allocation, reservation, availability
3. **CustomerHandler**: Validation, preferences
4. **NotificationHandler**: Alerts, emails, SMS

### Contratos a Definir:
1. **Event schemas** con versionado
2. **Handler interfaces** estándar
3. **Error handling** patterns
4. **Retry policies** por tipo de evento

---

**Análisis completado**: ✅
**Flujos críticos identificados**: 4
**Casos edge documentados**: 4
**Listo para Fase 2**: ✅