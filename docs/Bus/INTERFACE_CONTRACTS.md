# Contratos de Interfaces - Event-Driven Architecture

## 🎯 Objetivo
Definir contratos claros y bien estructurados para la comunicación entre dominios a través del Event Bus, garantizando desacoplamiento y mantenibilidad.

---

## 🏗️ Arquitectura de Interfaces

### 1. **Event Bus Interface**
Contrato principal para la publicación y suscripción de eventos.

```python
from abc import ABC, abstractmethod
from typing import List, Callable, Optional, Dict, Any
from uuid import UUID

class IEventBus(ABC):
    """Interfaz principal del Event Bus"""
    
    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """Publica un evento en el bus"""
        pass
    
    @abstractmethod
    async def publish_batch(self, events: List[DomainEvent]) -> None:
        """Publica múltiples eventos en una transacción"""
        pass
    
    @abstractmethod
    def subscribe(self, event_type: str, handler: 'IEventHandler') -> None:
        """Suscribe un handler a un tipo de evento"""
        pass
    
    @abstractmethod
    def unsubscribe(self, event_type: str, handler: 'IEventHandler') -> None:
        """Desuscribe un handler de un tipo de evento"""
        pass
    
    @abstractmethod
    async def start(self) -> None:
        """Inicia el Event Bus"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Detiene el Event Bus gracefully"""
        pass
    
    @abstractmethod
    def get_health_status(self) -> Dict[str, Any]:
        """Retorna el estado de salud del Event Bus"""
        pass
```

### 2. **Event Handler Interface**
Contrato base para todos los manejadores de eventos.

```python
from abc import ABC, abstractmethod
from typing import Optional

class IEventHandler(ABC):
    """Interfaz base para todos los handlers de eventos"""
    
    @property
    @abstractmethod
    def handler_name(self) -> str:
        """Nombre único del handler"""
        pass
    
    @property
    @abstractmethod
    def supported_events(self) -> List[str]:
        """Lista de tipos de eventos que maneja"""
        pass
    
    @abstractmethod
    async def handle(self, event: DomainEvent) -> Optional[List[DomainEvent]]:
        """
        Maneja un evento y opcionalmente retorna nuevos eventos
        
        Returns:
            None si no hay eventos adicionales
            List[DomainEvent] si se generan nuevos eventos
        """
        pass
    
    @abstractmethod
    async def can_handle(self, event: DomainEvent) -> bool:
        """Verifica si el handler puede procesar el evento"""
        pass
    
    @abstractmethod
    async def on_error(self, event: DomainEvent, error: Exception) -> None:
        """Maneja errores durante el procesamiento"""
        pass
    
    @property
    def retry_policy(self) -> 'RetryPolicy':
        """Política de reintentos para este handler"""
        return RetryPolicy.default()
    
    @property
    def timeout_seconds(self) -> int:
        """Timeout en segundos para el procesamiento"""
        return 30
```

### 3. **Retry Policy Interface**
Configuración de políticas de reintentos.

```python
from dataclasses import dataclass
from typing import Optional
from enum import Enum

class RetryStrategy(Enum):
    NONE = "none"
    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"

@dataclass
class RetryPolicy:
    strategy: RetryStrategy
    max_attempts: int
    initial_delay_seconds: int
    max_delay_seconds: Optional[int] = None
    backoff_multiplier: float = 2.0
    jitter: bool = True
    
    @classmethod
    def default(cls) -> 'RetryPolicy':
        return cls(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            max_attempts=3,
            initial_delay_seconds=1,
            max_delay_seconds=60,
            backoff_multiplier=2.0,
            jitter=True
        )
    
    @classmethod
    def no_retry(cls) -> 'RetryPolicy':
        return cls(
            strategy=RetryStrategy.NONE,
            max_attempts=1,
            initial_delay_seconds=0
        )
    
    @classmethod
    def aggressive_retry(cls) -> 'RetryPolicy':
        return cls(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            max_attempts=5,
            initial_delay_seconds=1,
            max_delay_seconds=300,
            backoff_multiplier=2.0,
            jitter=True
        )
```

---

## 🔧 Interfaces Específicas por Dominio

### 1. **Stock Domain Interfaces**

#### Stock Service Interface
```python
class IStockService(ABC):
    """Interfaz para servicios de stock"""
    
    @abstractmethod
    async def validate_product(self, product_id: str) -> Dict[str, Any]:
        """Valida que un producto existe y permite gestión de stock"""
        pass
    
    @abstractmethod
    async def check_availability(self, product_id: str, quantity: Decimal, warehouse_id: str) -> Dict[str, Any]:
        """Verifica disponibilidad de stock"""
        pass
    
    @abstractmethod
    async def allocate_stock(self, product_id: str, quantity: Decimal, warehouse_id: str, strategy: str = "FEFO") -> Dict[str, Any]:
        """Asigna stock para una operación"""
        pass
    
    @abstractmethod
    async def record_movement(self, movement_data: Dict[str, Any]) -> str:
        """Registra un movimiento de stock"""
        pass
    
    @abstractmethod
    async def release_allocation(self, allocation_id: str) -> None:
        """Libera una asignación de stock"""
        pass
```

#### Stock Event Handlers
```python
class IStockEventHandler(IEventHandler):
    """Handler base para eventos de stock"""
    
    @abstractmethod
    async def handle_stock_entry_requested(self, event: StockEntryRequested) -> Optional[List[DomainEvent]]:
        pass
    
    @abstractmethod
    async def handle_stock_allocation_requested(self, event: StockAllocationRequested) -> Optional[List[DomainEvent]]:
        pass
    
    @abstractmethod
    async def handle_stock_exit_requested(self, event: StockExitRequested) -> Optional[List[DomainEvent]]:
        pass
```

### 2. **Catalog Domain Interfaces**

#### Catalog Service Interface
```python
class ICatalogService(ABC):
    """Interfaz para servicios de catálogo"""
    
    @abstractmethod
    async def get_product_info(self, product_id: str, info_type: str = "BASIC") -> Dict[str, Any]:
        """Obtiene información de un producto"""
        pass
    
    @abstractmethod
    async def calculate_pricing(self, items: List[Dict], customer_id: Optional[str] = None) -> Dict[str, Any]:
        """Calcula precios para una lista de items"""
        pass
    
    @abstractmethod
    async def apply_benefits(self, items: List[Dict], customer_id: str) -> Dict[str, Any]:
        """Aplica beneficios a una lista de items"""
        pass
    
    @abstractmethod
    async def validate_products(self, product_ids: List[str]) -> Dict[str, bool]:
        """Valida que los productos existen y están activos"""
        pass
```

#### Catalog Event Handlers
```python
class ICatalogEventHandler(IEventHandler):
    """Handler base para eventos de catálogo"""
    
    @abstractmethod
    async def handle_product_info_requested(self, event: ProductInfoRequested) -> Optional[List[DomainEvent]]:
        pass
    
    @abstractmethod
    async def handle_pricing_calculation_requested(self, event: PricingCalculationRequested) -> Optional[List[DomainEvent]]:
        pass
    
    @abstractmethod
    async def handle_benefits_application_requested(self, event: BenefitsApplicationRequested) -> Optional[List[DomainEvent]]:
        pass
```

### 3. **Customer Domain Interfaces**

#### Customer Service Interface
```python
class ICustomerService(ABC):
    """Interfaz para servicios de clientes"""
    
    @abstractmethod
    async def get_customer_profile(self, customer_id: str, include_preferences: bool = False) -> Dict[str, Any]:
        """Obtiene el perfil de un cliente"""
        pass
    
    @abstractmethod
    async def validate_customer(self, customer_id: str) -> Dict[str, Any]:
        """Valida que un cliente existe y está activo"""
        pass
    
    @abstractmethod
    async def get_loyalty_info(self, customer_id: str) -> Dict[str, Any]:
        """Obtiene información de lealtad del cliente"""
        pass
    
    @abstractmethod
    async def update_loyalty_points(self, customer_id: str, points_change: int, reason: str) -> None:
        """Actualiza puntos de lealtad"""
        pass
```

### 4. **Notification Domain Interfaces**

#### Notification Service Interface
```python
class INotificationService(ABC):
    """Interfaz para servicios de notificaciones"""
    
    @abstractmethod
    async def send_notification(self, notification_data: Dict[str, Any]) -> str:
        """Envía una notificación"""
        pass
    
    @abstractmethod
    async def send_batch_notifications(self, notifications: List[Dict[str, Any]]) -> List[str]:
        """Envía múltiples notificaciones"""
        pass
    
    @abstractmethod
    async def get_notification_status(self, notification_id: str) -> Dict[str, Any]:
        """Obtiene el estado de una notificación"""
        pass
    
    @abstractmethod
    async def cancel_notification(self, notification_id: str) -> bool:
        """Cancela una notificación pendiente"""
        pass
```

---

## 🔄 Patrones de Comunicación

### 1. **Request-Response Pattern**
Para operaciones síncronas que requieren respuesta inmediata.

```python
class IRequestResponseHandler(IEventHandler):
    """Handler para patrones request-response"""
    
    @abstractmethod
    async def handle_request(self, request_event: DomainEvent) -> DomainEvent:
        """Maneja una solicitud y retorna una respuesta"""
        pass
    
    @property
    @abstractmethod
    def response_timeout_seconds(self) -> int:
        """Timeout para la respuesta"""
        pass
```

### 2. **Fire-and-Forget Pattern**
Para operaciones asíncronas que no requieren respuesta.

```python
class IFireAndForgetHandler(IEventHandler):
    """Handler para patrones fire-and-forget"""
    
    @abstractmethod
    async def handle_async(self, event: DomainEvent) -> None:
        """Maneja un evento de forma asíncrona"""
        pass
    
    @property
    def is_critical(self) -> bool:
        """Indica si el procesamiento es crítico"""
        return False
```

### 3. **Saga Pattern**
Para transacciones distribuidas complejas.

```python
class ISagaHandler(IEventHandler):
    """Handler para patrones saga"""
    
    @abstractmethod
    async def handle_saga_step(self, event: DomainEvent, saga_context: Dict[str, Any]) -> Optional[List[DomainEvent]]:
        """Maneja un paso de la saga"""
        pass
    
    @abstractmethod
    async def compensate(self, event: DomainEvent, saga_context: Dict[str, Any]) -> Optional[List[DomainEvent]]:
        """Ejecuta compensación en caso de fallo"""
        pass
    
    @property
    @abstractmethod
    def saga_name(self) -> str:
        """Nombre de la saga"""
        pass
```

---

## 📋 Event Schema Validation

### Schema Interface
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class IEventSchema(ABC):
    """Interfaz para validación de esquemas de eventos"""
    
    @abstractmethod
    def validate(self, event_data: Dict[str, Any]) -> bool:
        """Valida que los datos del evento cumplan el esquema"""
        pass
    
    @abstractmethod
    def get_validation_errors(self, event_data: Dict[str, Any]) -> List[str]:
        """Retorna lista de errores de validación"""
        pass
    
    @property
    @abstractmethod
    def schema_version(self) -> str:
        """Versión del esquema"""
        pass
    
    @property
    @abstractmethod
    def event_type(self) -> str:
        """Tipo de evento que valida"""
        pass
```

### Schema Registry Interface
```python
class ISchemaRegistry(ABC):
    """Registro de esquemas de eventos"""
    
    @abstractmethod
    def register_schema(self, event_type: str, version: str, schema: IEventSchema) -> None:
        """Registra un esquema para un tipo de evento"""
        pass
    
    @abstractmethod
    def get_schema(self, event_type: str, version: str) -> Optional[IEventSchema]:
        """Obtiene un esquema específico"""
        pass
    
    @abstractmethod
    def get_latest_schema(self, event_type: str) -> Optional[IEventSchema]:
        """Obtiene la versión más reciente del esquema"""
        pass
    
    @abstractmethod
    def validate_event(self, event: DomainEvent) -> bool:
        """Valida un evento contra su esquema"""
        pass
```

---

## 🔍 Monitoring and Observability Interfaces

### Event Bus Metrics Interface
```python
class IEventBusMetrics(ABC):
    """Interfaz para métricas del Event Bus"""
    
    @abstractmethod
    def record_event_published(self, event_type: str, processing_time_ms: float) -> None:
        """Registra la publicación de un evento"""
        pass
    
    @abstractmethod
    def record_event_processed(self, event_type: str, handler_name: str, processing_time_ms: float, success: bool) -> None:
        """Registra el procesamiento de un evento"""
        pass
    
    @abstractmethod
    def record_handler_error(self, event_type: str, handler_name: str, error_type: str) -> None:
        """Registra un error en un handler"""
        pass
    
    @abstractmethod
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de métricas"""
        pass
```

### Health Check Interface
```python
class IHealthCheck(ABC):
    """Interfaz para health checks"""
    
    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """Verifica el estado de salud del componente"""
        pass
    
    @property
    @abstractmethod
    def component_name(self) -> str:
        """Nombre del componente"""
        pass
    
    @property
    def check_interval_seconds(self) -> int:
        """Intervalo de verificación en segundos"""
        return 30
```

---

## 🎯 Configuration Interfaces

### Event Bus Configuration
```python
@dataclass
class EventBusConfig:
    """Configuración del Event Bus"""
    max_concurrent_handlers: int = 10
    event_queue_size: int = 1000
    handler_timeout_seconds: int = 30
    enable_dead_letter_queue: bool = True
    dead_letter_queue_size: int = 100
    metrics_enabled: bool = True
    health_check_interval_seconds: int = 30
    
    # Configuración de persistencia
    enable_event_store: bool = False
    event_store_connection_string: Optional[str] = None
    
    # Configuración de retry
    default_retry_policy: RetryPolicy = RetryPolicy.default()
    
    # Configuración de logging
    log_level: str = "INFO"
    log_events: bool = True
    log_handler_performance: bool = True
```

### Handler Configuration Interface
```python
class IHandlerConfig(ABC):
    """Interfaz para configuración de handlers"""
    
    @property
    @abstractmethod
    def handler_name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def enabled(self) -> bool:
        pass
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """Prioridad del handler (mayor número = mayor prioridad)"""
        pass
    
    @property
    @abstractmethod
    def max_concurrent_executions(self) -> int:
        pass
    
    @property
    @abstractmethod
    def retry_policy(self) -> RetryPolicy:
        pass
```

---

## 📊 Contratos de Datos

### Event Envelope
```python
@dataclass(frozen=True)
class EventEnvelope:
    """Envelope que contiene un evento y metadatos de transporte"""
    event: DomainEvent
    message_id: UUID
    timestamp: datetime
    source: str
    destination: Optional[str] = None
    correlation_id: Optional[UUID] = None
    causation_id: Optional[UUID] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Metadatos de routing
    routing_key: str = ""
    headers: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.headers is None:
            object.__setattr__(self, 'headers', {})
```

### Handler Result
```python
@dataclass
class HandlerResult:
    """Resultado del procesamiento de un handler"""
    success: bool
    events_generated: List[DomainEvent]
    error_message: Optional[str] = None
    should_retry: bool = False
    processing_time_ms: float = 0.0
    
    @classmethod
    def success_with_events(cls, events: List[DomainEvent], processing_time_ms: float = 0.0) -> 'HandlerResult':
        return cls(
            success=True,
            events_generated=events,
            processing_time_ms=processing_time_ms
        )
    
    @classmethod
    def success_no_events(cls, processing_time_ms: float = 0.0) -> 'HandlerResult':
        return cls(
            success=True,
            events_generated=[],
            processing_time_ms=processing_time_ms
        )
    
    @classmethod
    def failure(cls, error_message: str, should_retry: bool = True, processing_time_ms: float = 0.0) -> 'HandlerResult':
        return cls(
            success=False,
            events_generated=[],
            error_message=error_message,
            should_retry=should_retry,
            processing_time_ms=processing_time_ms
        )
```

---

## 🔒 Security Interfaces

### Event Authorization Interface
```python
class IEventAuthorizer(ABC):
    """Interfaz para autorización de eventos"""
    
    @abstractmethod
    async def can_publish(self, user_id: str, event: DomainEvent) -> bool:
        """Verifica si un usuario puede publicar un evento"""
        pass
    
    @abstractmethod
    async def can_handle(self, handler_name: str, event: DomainEvent) -> bool:
        """Verifica si un handler puede procesar un evento"""
        pass
    
    @abstractmethod
    async def filter_sensitive_data(self, event: DomainEvent, user_id: str) -> DomainEvent:
        """Filtra datos sensibles de un evento según el usuario"""
        pass
```

---

## 📋 Checklist de Implementación

### Interfaces Core ✅
- [x] IEventBus - Contrato principal del bus
- [x] IEventHandler - Handler base
- [x] RetryPolicy - Políticas de reintentos
- [x] IEventSchema - Validación de esquemas

### Interfaces por Dominio ✅
- [x] IStockService & IStockEventHandler
- [x] ICatalogService & ICatalogEventHandler  
- [x] ICustomerService
- [x] INotificationService

### Patrones de Comunicación ✅
- [x] Request-Response Pattern
- [x] Fire-and-Forget Pattern
- [x] Saga Pattern

### Observabilidad ✅
- [x] IEventBusMetrics
- [x] IHealthCheck
- [x] Configuración y logging

### Seguridad ✅
- [x] IEventAuthorizer
- [x] Filtrado de datos sensibles

---

**Contratos de interfaces definidos**: ✅  
**Patrones de comunicación establecidos**: ✅  
**Interfaces de observabilidad creadas**: ✅  
**Listo para implementación de infraestructura**: ✅