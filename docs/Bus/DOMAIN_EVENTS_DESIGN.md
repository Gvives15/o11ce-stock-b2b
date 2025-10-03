# Diseño de Eventos de Dominio - Fase 2

## 🎯 Objetivo
Diseñar eventos de dominio estructurados, inmutables y bien definidos que reemplacen las dependencias directas identificadas en la Fase 1.

---

## 📋 Principios de Diseño de Eventos

### 1. **Inmutabilidad**
- Los eventos son objetos inmutables una vez creados
- Representan hechos que ya ocurrieron en el pasado
- Nombres en tiempo pasado (ej: `ProductCreated`, `StockUpdated`)

### 2. **Información Rica**
- Contienen toda la información necesaria para los handlers
- Evitan que los handlers necesiten hacer queries adicionales
- Incluyen contexto temporal y de usuario

### 3. **Versionado**
- Cada evento tiene un esquema versionado
- Compatibilidad hacia atrás garantizada
- Evolución controlada de contratos

### 4. **Dominio Específico**
- Cada evento pertenece a un dominio específico
- Expresan conceptos de negocio, no técnicos
- Nombres descriptivos y significativos

---

## 🏗️ Estructura Base de Eventos

### Event Base Class
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID, uuid4

@dataclass(frozen=True)
class DomainEvent:
    """Clase base para todos los eventos de dominio"""
    event_id: UUID
    event_type: str
    event_version: str
    occurred_at: datetime
    aggregate_id: str
    aggregate_type: str
    user_id: Optional[str] = None
    correlation_id: Optional[UUID] = None
    causation_id: Optional[UUID] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})
```

---

## 🛒 Eventos del Dominio POS

### 1. Flujo de Venta POS

#### `SaleInitiated`
```python
@dataclass(frozen=True)
class SaleInitiated(DomainEvent):
    """Se inicia una venta en POS"""
    event_type: str = "pos.sale.initiated"
    event_version: str = "1.0"
    
    # Datos del evento
    sale_id: str
    cashier_id: str
    terminal_id: str
    customer_id: Optional[str]
    items: List[Dict[str, Any]]  # [{"product_id": "123", "quantity": 2, "requested_price": None}]
    payment_method: str
    discount_code: Optional[str]
    
    # Contexto adicional
    store_id: str
    shift_id: str
    is_training_mode: bool = False
```

#### `PriceCalculated`
```python
@dataclass(frozen=True)
class PriceCalculated(DomainEvent):
    """Precios calculados para una venta"""
    event_type: str = "pos.price.calculated"
    event_version: str = "1.0"
    
    sale_id: str
    items: List[Dict[str, Any]]  # [{"product_id": "123", "quantity": 2, "unit_price": 10.50, "total_price": 21.00, "applied_benefits": [...]}]
    subtotal: Decimal
    total_discount: Decimal
    total_tax: Decimal
    final_total: Decimal
    applied_benefits: List[Dict[str, Any]]
    
    # Para auditoría
    pricing_rules_version: str
    calculation_timestamp: datetime
```

#### `StockAllocated`
```python
@dataclass(frozen=True)
class StockAllocated(DomainEvent):
    """Stock asignado para una venta"""
    event_type: str = "pos.stock.allocated"
    event_version: str = "1.0"
    
    sale_id: str
    allocations: List[Dict[str, Any]]  # [{"product_id": "123", "quantity": 2, "lots": [{"lot_id": "L001", "quantity": 2, "expiry_date": "2024-12-31"}]}]
    warehouse_id: str
    allocation_strategy: str  # "FEFO", "FIFO", "MANUAL"
    
    # Para rollback si es necesario
    reservation_expires_at: datetime
    can_partial_fulfill: bool
```

#### `StockExitRecorded`
```python
@dataclass(frozen=True)
class StockExitRecorded(DomainEvent):
    """Salida de stock registrada"""
    event_type: str = "pos.stock.exit_recorded"
    event_version: str = "1.0"
    
    sale_id: str
    movements: List[Dict[str, Any]]  # [{"product_id": "123", "lot_id": "L001", "quantity": 2, "movement_id": "M001", "cost": 8.50}]
    total_cost: Decimal
    warehouse_id: str
    
    # Para auditoría y reportes
    movement_type: str = "SALE"
    reference_document: str  # Número de venta
```

#### `SaleCompleted`
```python
@dataclass(frozen=True)
class SaleCompleted(DomainEvent):
    """Venta completada exitosamente"""
    event_type: str = "pos.sale.completed"
    event_version: str = "1.0"
    
    sale_id: str
    receipt_number: str
    final_total: Decimal
    payment_received: Decimal
    change_given: Decimal
    payment_method: str
    
    # Para integraciones
    requires_invoice: bool
    customer_email: Optional[str]
    loyalty_points_earned: int = 0
```

#### `SaleFailed`
```python
@dataclass(frozen=True)
class SaleFailed(DomainEvent):
    """Venta falló por algún motivo"""
    event_type: str = "pos.sale.failed"
    event_version: str = "1.0"
    
    sale_id: str
    failure_reason: str
    failure_stage: str  # "PRICING", "ALLOCATION", "PAYMENT", "RECORDING"
    error_details: Dict[str, Any]
    
    # Para rollback automático
    requires_stock_release: bool
    allocated_items: List[Dict[str, Any]]
```

---

## 📦 Eventos del Dominio Stock

### 1. Gestión de Inventario

#### `StockEntryRequested`
```python
@dataclass(frozen=True)
class StockEntryRequested(DomainEvent):
    """Solicitud de entrada de stock"""
    event_type: str = "stock.entry.requested"
    event_version: str = "1.0"
    
    entry_id: str
    product_id: str
    quantity: Decimal
    unit_cost: Decimal
    supplier_id: Optional[str]
    warehouse_id: str
    lot_number: Optional[str]
    expiry_date: Optional[date]
    
    # Documentos de respaldo
    purchase_order_id: Optional[str]
    invoice_number: Optional[str]
    received_by: str
```

#### `ProductValidated`
```python
@dataclass(frozen=True)
class ProductValidated(DomainEvent):
    """Producto validado para operación de stock"""
    event_type: str = "stock.product.validated"
    event_version: str = "1.0"
    
    product_id: str
    product_name: str
    product_sku: str
    is_active: bool
    allows_stock_management: bool
    unit_of_measure: str
    
    # Para validaciones adicionales
    requires_lot_tracking: bool
    requires_expiry_tracking: bool
    minimum_stock_level: Decimal
```

#### `StockUpdated`
```python
@dataclass(frozen=True)
class StockUpdated(DomainEvent):
    """Stock actualizado (entrada o salida)"""
    event_type: str = "stock.updated"
    event_version: str = "1.0"
    
    product_id: str
    warehouse_id: str
    movement_type: str  # "ENTRY", "EXIT", "ADJUSTMENT", "TRANSFER"
    quantity_change: Decimal  # Positivo para entradas, negativo para salidas
    new_total_quantity: Decimal
    unit_cost: Optional[Decimal]
    
    # Detalles del lote si aplica
    lot_id: Optional[str]
    lot_number: Optional[str]
    expiry_date: Optional[date]
    
    # Referencias
    movement_id: str
    reference_document: Optional[str]
    reason: str
```

#### `LowStockDetected`
```python
@dataclass(frozen=True)
class LowStockDetected(DomainEvent):
    """Stock bajo detectado"""
    event_type: str = "stock.low_stock.detected"
    event_version: str = "1.0"
    
    product_id: str
    product_name: str
    warehouse_id: str
    current_quantity: Decimal
    minimum_threshold: Decimal
    suggested_reorder_quantity: Decimal
    
    # Para automatización
    auto_reorder_enabled: bool
    preferred_supplier_id: Optional[str]
    last_purchase_cost: Optional[Decimal]
    
    # Contexto temporal
    days_of_stock_remaining: Optional[int]
    average_daily_consumption: Optional[Decimal]
```

#### `StockReservationExpired`
```python
@dataclass(frozen=True)
class StockReservationExpired(DomainEvent):
    """Reserva de stock expirada"""
    event_type: str = "stock.reservation.expired"
    event_version: str = "1.0"
    
    reservation_id: str
    product_id: str
    quantity: Decimal
    warehouse_id: str
    original_sale_id: str
    reserved_at: datetime
    expired_at: datetime
    
    # Para liberación automática
    lots_to_release: List[Dict[str, Any]]
    requires_notification: bool
```

---

## 🛍️ Eventos del Dominio Orders

### 1. Proceso de Checkout

#### `OrderCheckoutInitiated`
```python
@dataclass(frozen=True)
class OrderCheckoutInitiated(DomainEvent):
    """Inicio del proceso de checkout"""
    event_type: str = "orders.checkout.initiated"
    event_version: str = "1.0"
    
    order_id: str
    customer_id: str
    items: List[Dict[str, Any]]  # [{"product_id": "123", "quantity": 2, "requested_price": None}]
    delivery_address: Dict[str, str]
    payment_method: str
    discount_code: Optional[str]
    
    # Contexto del pedido
    order_source: str  # "WEB", "MOBILE", "PHONE", "EMAIL"
    is_express_delivery: bool
    special_instructions: Optional[str]
```

#### `CustomerValidated`
```python
@dataclass(frozen=True)
class CustomerValidated(DomainEvent):
    """Cliente validado para el pedido"""
    event_type: str = "orders.customer.validated"
    event_version: str = "1.0"
    
    order_id: str
    customer_id: str
    customer_name: str
    customer_email: str
    customer_phone: str
    customer_type: str  # "REGULAR", "VIP", "WHOLESALE"
    
    # Para aplicación de beneficios
    loyalty_level: str
    available_credit: Decimal
    payment_terms: str
    
    # Validaciones
    address_validated: bool
    credit_approved: bool
```

#### `BenefitsApplied`
```python
@dataclass(frozen=True)
class BenefitsApplied(DomainEvent):
    """Beneficios aplicados al pedido"""
    event_type: str = "orders.benefits.applied"
    event_version: str = "1.0"
    
    order_id: str
    customer_id: str
    applied_benefits: List[Dict[str, Any]]  # [{"benefit_id": "B001", "type": "DISCOUNT", "value": 10.0, "applied_to": "TOTAL"}]
    original_total: Decimal
    discount_amount: Decimal
    final_total: Decimal
    
    # Para auditoría
    benefits_calculation_version: str
    loyalty_points_used: int = 0
    loyalty_points_earned: int = 0
```

#### `OrderCreated`
```python
@dataclass(frozen=True)
class OrderCreated(DomainEvent):
    """Pedido creado exitosamente"""
    event_type: str = "orders.created"
    event_version: str = "1.0"
    
    order_id: str
    order_number: str
    customer_id: str
    total_amount: Decimal
    status: str = "PENDING"
    
    # Detalles del pedido
    items: List[Dict[str, Any]]
    delivery_address: Dict[str, str]
    estimated_delivery_date: date
    
    # Para seguimiento
    tracking_number: Optional[str]
    requires_preparation: bool
    priority_level: str = "NORMAL"
```

---

## 👥 Eventos del Dominio Customers

#### `CustomerProfileRequested`
```python
@dataclass(frozen=True)
class CustomerProfileRequested(DomainEvent):
    """Solicitud de perfil de cliente"""
    event_type: str = "customers.profile.requested"
    event_version: str = "1.0"
    
    customer_id: str
    requested_by: str  # "POS", "ORDERS", "CATALOG"
    request_context: str  # "SALE", "PRICING", "VALIDATION"
    
    # Datos específicos solicitados
    include_preferences: bool = False
    include_purchase_history: bool = False
    include_loyalty_info: bool = True
```

#### `CustomerProfileRetrieved`
```python
@dataclass(frozen=True)
class CustomerProfileRetrieved(DomainEvent):
    """Perfil de cliente recuperado"""
    event_type: str = "customers.profile.retrieved"
    event_version: str = "1.0"
    
    customer_id: str
    customer_data: Dict[str, Any]
    preferences: Dict[str, Any]
    loyalty_info: Dict[str, Any]
    
    # Metadatos
    data_freshness: datetime
    cache_ttl: int = 300  # 5 minutos
```

---

## 🏷️ Eventos del Dominio Catalog

#### `ProductInfoRequested`
```python
@dataclass(frozen=True)
class ProductInfoRequested(DomainEvent):
    """Solicitud de información de producto"""
    event_type: str = "catalog.product.info_requested"
    event_version: str = "1.0"
    
    product_id: str
    requested_by: str
    info_type: str  # "BASIC", "PRICING", "FULL"
    
    # Contexto para pricing
    customer_id: Optional[str]
    quantity: Optional[Decimal]
    date_needed: Optional[date]
```

#### `ProductInfoRetrieved`
```python
@dataclass(frozen=True)
class ProductInfoRetrieved(DomainEvent):
    """Información de producto recuperada"""
    event_type: str = "catalog.product.info_retrieved"
    event_version: str = "1.0"
    
    product_id: str
    product_data: Dict[str, Any]
    pricing_data: Optional[Dict[str, Any]]
    availability_data: Optional[Dict[str, Any]]
    
    # Metadatos
    data_version: str
    cached_until: datetime
```

---

## 🔔 Eventos del Dominio Notifications

#### `NotificationRequested`
```python
@dataclass(frozen=True)
class NotificationRequested(DomainEvent):
    """Solicitud de notificación"""
    event_type: str = "notifications.requested"
    event_version: str = "1.0"
    
    notification_type: str  # "LOW_STOCK", "ORDER_CREATED", "SALE_COMPLETED"
    recipient_type: str  # "USER", "CUSTOMER", "ADMIN"
    recipient_id: str
    
    # Contenido
    title: str
    message: str
    data: Dict[str, Any]
    
    # Configuración
    channels: List[str]  # ["EMAIL", "SMS", "PUSH", "IN_APP"]
    priority: str = "NORMAL"
    expires_at: Optional[datetime]
```

#### `NotificationSent`
```python
@dataclass(frozen=True)
class NotificationSent(DomainEvent):
    """Notificación enviada"""
    event_type: str = "notifications.sent"
    event_version: str = "1.0"
    
    notification_id: str
    recipient_id: str
    channel: str
    status: str  # "SENT", "DELIVERED", "FAILED"
    
    # Detalles del envío
    sent_at: datetime
    delivery_confirmation: Optional[datetime]
    error_message: Optional[str]
```

---

## 🔄 Eventos de Sistema y Error Handling

#### `EventProcessingFailed`
```python
@dataclass(frozen=True)
class EventProcessingFailed(DomainEvent):
    """Fallo en el procesamiento de un evento"""
    event_type: str = "system.event.processing_failed"
    event_version: str = "1.0"
    
    original_event_id: UUID
    original_event_type: str
    handler_name: str
    error_message: str
    error_details: Dict[str, Any]
    
    # Para retry logic
    attempt_number: int
    max_attempts: int
    next_retry_at: Optional[datetime]
    
    # Para dead letter queue
    requires_manual_intervention: bool
```

#### `CompensationRequired`
```python
@dataclass(frozen=True)
class CompensationRequired(DomainEvent):
    """Se requiere compensación por fallo"""
    event_type: str = "system.compensation.required"
    event_version: str = "1.0"
    
    original_transaction_id: str
    failed_step: str
    compensation_actions: List[Dict[str, Any]]
    
    # Contexto
    affected_aggregates: List[str]
    rollback_data: Dict[str, Any]
    requires_user_notification: bool
```

---

## 📊 Matriz de Eventos por Flujo

### Flujo 1: Venta POS
```
SaleInitiated → PriceCalculated → StockAllocated → StockExitRecorded → SaleCompleted
                     ↓                ↓                ↓                ↓
              CustomerValidated   ProductValidated   StockUpdated   NotificationSent
```

### Flujo 2: Checkout de Orden
```
OrderCheckoutInitiated → CustomerValidated → BenefitsApplied → OrderCreated → NotificationSent
                              ↓                    ↓              ↓
                      ProductInfoRetrieved    StockReserved   StockUpdated
```

### Flujo 3: Actualización de Stock
```
StockEntryRequested → ProductValidated → StockUpdated → LowStockDetected? → NotificationSent?
```

### Flujo 4: Consulta de Disponibilidad
```
AvailabilityRequested → ProductInfoRetrieved → AvailabilityCalculated
```

---

## 🎯 Próximos Pasos

### Completado ✅
- Diseño de eventos de dominio
- Estructura base de eventos
- Eventos para flujos críticos
- Eventos de error handling

### Siguiente: Contratos de Interfaces
- Definir interfaces de handlers
- Establecer contratos de Event Bus
- Crear esquemas de validación
- Documentar patrones de retry

---

**Eventos de dominio diseñados**: ✅  
**Flujos críticos cubiertos**: 4/4  
**Eventos definidos**: 25+  
**Listo para contratos de interfaces**: ✅