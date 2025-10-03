# Patrones de Manejo de Errores - Event-Driven Architecture

## 🎯 Objetivo
Establecer patrones robustos y consistentes para el manejo de errores, recuperación automática y compensación en la arquitectura event-driven.

---

## 🏗️ Estrategia General de Error Handling

### 1. **Niveles de Error Handling**

#### Nivel 1: Handler Level
- Errores específicos del handler
- Validación de datos de entrada
- Errores de lógica de negocio
- Timeouts de procesamiento

#### Nivel 2: Event Bus Level  
- Errores de serialización/deserialización
- Errores de routing
- Errores de conexión
- Sobrecarga del sistema

#### Nivel 3: System Level
- Errores de infraestructura
- Fallos de base de datos
- Errores de red
- Fallos de servicios externos

### 2. **Clasificación de Errores**

```python
from enum import Enum

class ErrorType(Enum):
    # Errores recuperables (retry automático)
    TRANSIENT = "transient"           # Errores temporales de red, DB, etc.
    TIMEOUT = "timeout"               # Timeouts de procesamiento
    RATE_LIMIT = "rate_limit"         # Límites de tasa excedidos
    RESOURCE_UNAVAILABLE = "resource_unavailable"  # Recursos temporalmente no disponibles
    
    # Errores de negocio (no retry, compensación posible)
    BUSINESS_RULE = "business_rule"   # Violación de reglas de negocio
    VALIDATION = "validation"         # Datos inválidos
    AUTHORIZATION = "authorization"   # Permisos insuficientes
    NOT_FOUND = "not_found"          # Recurso no encontrado
    
    # Errores críticos (no retry, intervención manual)
    SYSTEM = "system"                 # Errores de sistema
    CONFIGURATION = "configuration"  # Errores de configuración
    CORRUPTION = "corruption"        # Datos corruptos
    SECURITY = "security"            # Violaciones de seguridad

class ErrorSeverity(Enum):
    LOW = "low"           # No afecta funcionalidad crítica
    MEDIUM = "medium"     # Afecta funcionalidad no crítica
    HIGH = "high"         # Afecta funcionalidad crítica
    CRITICAL = "critical" # Sistema no funcional
```

---

## 🔄 Patrones de Retry

### 1. **Retry Policies por Tipo de Error**

```python
@dataclass
class ErrorRetryPolicy:
    error_type: ErrorType
    retry_policy: RetryPolicy
    max_attempts: int
    escalation_threshold: int  # Después de cuántos fallos escalar
    
    @classmethod
    def get_policy_for_error(cls, error_type: ErrorType) -> 'ErrorRetryPolicy':
        policies = {
            ErrorType.TRANSIENT: cls(
                error_type=ErrorType.TRANSIENT,
                retry_policy=RetryPolicy(
                    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                    max_attempts=5,
                    initial_delay_seconds=1,
                    max_delay_seconds=60,
                    backoff_multiplier=2.0,
                    jitter=True
                ),
                max_attempts=5,
                escalation_threshold=3
            ),
            ErrorType.TIMEOUT: cls(
                error_type=ErrorType.TIMEOUT,
                retry_policy=RetryPolicy(
                    strategy=RetryStrategy.LINEAR_BACKOFF,
                    max_attempts=3,
                    initial_delay_seconds=2,
                    max_delay_seconds=30,
                    backoff_multiplier=1.5,
                    jitter=False
                ),
                max_attempts=3,
                escalation_threshold=2
            ),
            ErrorType.RATE_LIMIT: cls(
                error_type=ErrorType.RATE_LIMIT,
                retry_policy=RetryPolicy(
                    strategy=RetryStrategy.FIXED_DELAY,
                    max_attempts=10,
                    initial_delay_seconds=60,
                    max_delay_seconds=60,
                    jitter=True
                ),
                max_attempts=10,
                escalation_threshold=5
            ),
            ErrorType.BUSINESS_RULE: cls(
                error_type=ErrorType.BUSINESS_RULE,
                retry_policy=RetryPolicy.no_retry(),
                max_attempts=1,
                escalation_threshold=1
            ),
            ErrorType.VALIDATION: cls(
                error_type=ErrorType.VALIDATION,
                retry_policy=RetryPolicy.no_retry(),
                max_attempts=1,
                escalation_threshold=1
            ),
            ErrorType.SYSTEM: cls(
                error_type=ErrorType.SYSTEM,
                retry_policy=RetryPolicy.no_retry(),
                max_attempts=1,
                escalation_threshold=1
            )
        }
        return policies.get(error_type, policies[ErrorType.TRANSIENT])
```

### 2. **Circuit Breaker Pattern**

```python
from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, Any

class CircuitState(Enum):
    CLOSED = "closed"      # Funcionando normalmente
    OPEN = "open"          # Circuito abierto, rechazando requests
    HALF_OPEN = "half_open" # Probando si el servicio se recuperó

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5          # Fallos antes de abrir
    success_threshold: int = 3          # Éxitos para cerrar desde half-open
    timeout_seconds: int = 60           # Tiempo antes de pasar a half-open
    monitoring_window_seconds: int = 300 # Ventana de monitoreo de fallos

class CircuitBreaker:
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state_changed_at = datetime.now()
    
    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.state_changed_at = datetime.now()
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._close_circuit()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0  # Reset failure count on success
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self._open_circuit()
        elif self.state == CircuitState.HALF_OPEN:
            self._open_circuit()
    
    def _should_attempt_reset(self) -> bool:
        if self.last_failure_time is None:
            return True
        return datetime.now() - self.last_failure_time > timedelta(seconds=self.config.timeout_seconds)
    
    def _open_circuit(self):
        self.state = CircuitState.OPEN
        self.state_changed_at = datetime.now()
        self.success_count = 0
    
    def _close_circuit(self):
        self.state = CircuitState.CLOSED
        self.state_changed_at = datetime.now()
        self.failure_count = 0
        self.success_count = 0
```

---

## 🔧 Compensación y Rollback

### 1. **Compensation Events**

```python
@dataclass(frozen=True)
class CompensationEvent(DomainEvent):
    """Evento base para compensaciones"""
    original_event_id: UUID
    original_event_type: str
    compensation_reason: str
    compensation_data: Dict[str, Any]
    
    def __post_init__(self):
        super().__post_init__()
        # Asegurar que el event_type termine con .compensated
        if not self.event_type.endswith('.compensated'):
            object.__setattr__(self, 'event_type', f"{self.event_type}.compensated")

# Ejemplos específicos de compensación
@dataclass(frozen=True)
class StockAllocationCompensated(CompensationEvent):
    """Compensación de asignación de stock"""
    event_type: str = "stock.allocation.compensated"
    event_version: str = "1.0"
    
    allocation_id: str
    product_id: str
    quantity_to_release: Decimal
    warehouse_id: str
    lots_to_release: List[Dict[str, Any]]

@dataclass(frozen=True)
class SaleCompensated(CompensationEvent):
    """Compensación de venta"""
    event_type: str = "pos.sale.compensated"
    event_version: str = "1.0"
    
    sale_id: str
    refund_amount: Decimal
    items_to_restock: List[Dict[str, Any]]
    payment_to_reverse: Dict[str, Any]
```

### 2. **Saga Pattern para Transacciones Distribuidas**

```python
from abc import ABC, abstractmethod
from enum import Enum

class SagaStepStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATED = "compensated"

@dataclass
class SagaStep:
    step_id: str
    step_name: str
    handler_name: str
    event_to_publish: DomainEvent
    compensation_event: Optional[DomainEvent]
    status: SagaStepStatus = SagaStepStatus.PENDING
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

@dataclass
class SagaContext:
    saga_id: UUID
    saga_type: str
    steps: List[SagaStep]
    current_step_index: int = 0
    status: str = "RUNNING"
    started_at: datetime = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.started_at is None:
            object.__setattr__(self, 'started_at', datetime.now())

class ISagaOrchestrator(ABC):
    """Orquestador de sagas"""
    
    @abstractmethod
    async def start_saga(self, saga_context: SagaContext) -> None:
        """Inicia una saga"""
        pass
    
    @abstractmethod
    async def handle_step_completed(self, saga_id: UUID, step_id: str, result: HandlerResult) -> None:
        """Maneja la finalización de un paso"""
        pass
    
    @abstractmethod
    async def handle_step_failed(self, saga_id: UUID, step_id: str, error: Exception) -> None:
        """Maneja el fallo de un paso"""
        pass
    
    @abstractmethod
    async def compensate_saga(self, saga_id: UUID, failed_step_index: int) -> None:
        """Ejecuta compensación de una saga"""
        pass
```

### 3. **Saga Definitions para Flujos Críticos**

#### Saga: Venta POS Completa
```python
class POSSaleSaga:
    """Saga para venta POS completa"""
    
    @staticmethod
    def create_saga_context(sale_data: Dict[str, Any]) -> SagaContext:
        sale_id = sale_data['sale_id']
        
        steps = [
            SagaStep(
                step_id=f"{sale_id}_validate_customer",
                step_name="Validate Customer",
                handler_name="CustomerValidationHandler",
                event_to_publish=CustomerValidationRequested(**sale_data),
                compensation_event=None  # No compensation needed
            ),
            SagaStep(
                step_id=f"{sale_id}_calculate_price",
                step_name="Calculate Pricing",
                handler_name="PricingCalculationHandler",
                event_to_publish=PricingCalculationRequested(**sale_data),
                compensation_event=None  # No compensation needed
            ),
            SagaStep(
                step_id=f"{sale_id}_allocate_stock",
                step_name="Allocate Stock",
                handler_name="StockAllocationHandler",
                event_to_publish=StockAllocationRequested(**sale_data),
                compensation_event=StockAllocationCompensated(
                    original_event_id=uuid4(),
                    original_event_type="stock.allocation.requested",
                    compensation_reason="Sale saga failed",
                    compensation_data=sale_data,
                    allocation_id=sale_data.get('allocation_id', ''),
                    product_id=sale_data['product_id'],
                    quantity_to_release=sale_data['quantity'],
                    warehouse_id=sale_data['warehouse_id'],
                    lots_to_release=[]
                )
            ),
            SagaStep(
                step_id=f"{sale_id}_record_exit",
                step_name="Record Stock Exit",
                handler_name="StockExitHandler",
                event_to_publish=StockExitRequested(**sale_data),
                compensation_event=StockEntryRequested(
                    # Datos para revertir la salida
                    **sale_data
                )
            ),
            SagaStep(
                step_id=f"{sale_id}_complete_sale",
                step_name="Complete Sale",
                handler_name="SaleCompletionHandler",
                event_to_publish=SaleCompletionRequested(**sale_data),
                compensation_event=SaleCompensated(
                    original_event_id=uuid4(),
                    original_event_type="sale.completion.requested",
                    compensation_reason="Sale saga failed",
                    compensation_data=sale_data,
                    sale_id=sale_id,
                    refund_amount=sale_data.get('total_amount', Decimal('0')),
                    items_to_restock=sale_data.get('items', []),
                    payment_to_reverse=sale_data.get('payment_data', {})
                )
            )
        ]
        
        return SagaContext(
            saga_id=uuid4(),
            saga_type="pos_sale_complete",
            steps=steps
        )
```

---

## 🚨 Dead Letter Queue y Error Escalation

### 1. **Dead Letter Queue Management**

```python
@dataclass
class DeadLetterMessage:
    """Mensaje en dead letter queue"""
    message_id: UUID
    original_event: DomainEvent
    handler_name: str
    error_type: ErrorType
    error_message: str
    retry_count: int
    first_failed_at: datetime
    last_failed_at: datetime
    requires_manual_intervention: bool
    escalation_level: int = 0

class IDeadLetterQueueManager(ABC):
    """Gestor de dead letter queue"""
    
    @abstractmethod
    async def add_to_dlq(self, message: DeadLetterMessage) -> None:
        """Añade un mensaje al DLQ"""
        pass
    
    @abstractmethod
    async def get_dlq_messages(self, limit: int = 100) -> List[DeadLetterMessage]:
        """Obtiene mensajes del DLQ"""
        pass
    
    @abstractmethod
    async def retry_message(self, message_id: UUID) -> bool:
        """Reintenta procesar un mensaje del DLQ"""
        pass
    
    @abstractmethod
    async def mark_as_resolved(self, message_id: UUID, resolution_notes: str) -> None:
        """Marca un mensaje como resuelto manualmente"""
        pass
    
    @abstractmethod
    async def get_dlq_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del DLQ"""
        pass
```

### 2. **Error Escalation**

```python
@dataclass
class EscalationRule:
    """Regla de escalación de errores"""
    error_type: ErrorType
    severity: ErrorSeverity
    escalation_threshold: int
    escalation_channels: List[str]  # ["email", "slack", "pagerduty"]
    escalation_delay_minutes: int
    auto_escalate: bool = True

class IErrorEscalationManager(ABC):
    """Gestor de escalación de errores"""
    
    @abstractmethod
    async def evaluate_escalation(self, error_event: ErrorEvent) -> bool:
        """Evalúa si un error debe ser escalado"""
        pass
    
    @abstractmethod
    async def escalate_error(self, error_event: ErrorEvent, escalation_level: int) -> None:
        """Escala un error"""
        pass
    
    @abstractmethod
    async def get_escalation_history(self, error_id: UUID) -> List[Dict[str, Any]]:
        """Obtiene historial de escalaciones"""
        pass
```

---

## 📊 Error Monitoring y Alerting

### 1. **Error Events**

```python
@dataclass(frozen=True)
class ErrorEvent(DomainEvent):
    """Evento de error base"""
    event_type: str = "system.error.occurred"
    event_version: str = "1.0"
    
    error_id: UUID
    error_type: ErrorType
    error_severity: ErrorSeverity
    error_message: str
    error_details: Dict[str, Any]
    
    # Contexto del error
    handler_name: Optional[str]
    original_event_id: Optional[UUID]
    original_event_type: Optional[str]
    
    # Métricas
    processing_time_ms: float
    retry_count: int = 0
    
    # Stack trace (solo para errores críticos)
    stack_trace: Optional[str] = None

@dataclass(frozen=True)
class HandlerTimeoutEvent(ErrorEvent):
    """Evento de timeout de handler"""
    event_type: str = "system.handler.timeout"
    error_type: ErrorType = ErrorType.TIMEOUT
    
    timeout_seconds: int
    handler_name: str

@dataclass(frozen=True)
class BusinessRuleViolationEvent(ErrorEvent):
    """Evento de violación de regla de negocio"""
    event_type: str = "business.rule.violation"
    error_type: ErrorType = ErrorType.BUSINESS_RULE
    
    rule_name: str
    rule_description: str
    violated_constraints: List[str]
```

### 2. **Error Metrics y Dashboards**

```python
class IErrorMetrics(ABC):
    """Interfaz para métricas de errores"""
    
    @abstractmethod
    def record_error(self, error_event: ErrorEvent) -> None:
        """Registra un error"""
        pass
    
    @abstractmethod
    def record_recovery(self, error_id: UUID, recovery_time_ms: float) -> None:
        """Registra la recuperación de un error"""
        pass
    
    @abstractmethod
    def get_error_rate(self, time_window_minutes: int = 60) -> float:
        """Obtiene tasa de errores"""
        pass
    
    @abstractmethod
    def get_error_breakdown(self) -> Dict[str, int]:
        """Obtiene breakdown de errores por tipo"""
        pass
    
    @abstractmethod
    def get_handler_error_stats(self, handler_name: str) -> Dict[str, Any]:
        """Obtiene estadísticas de errores por handler"""
        pass
```

---

## 🔧 Implementación de Error Handlers

### 1. **Base Error Handler**

```python
class BaseErrorHandler(IEventHandler):
    """Handler base para manejo de errores"""
    
    def __init__(self, 
                 circuit_breaker: CircuitBreaker,
                 dlq_manager: IDeadLetterQueueManager,
                 metrics: IErrorMetrics):
        self.circuit_breaker = circuit_breaker
        self.dlq_manager = dlq_manager
        self.metrics = metrics
    
    async def handle_with_error_management(self, event: DomainEvent) -> HandlerResult:
        """Maneja un evento con gestión completa de errores"""
        start_time = time.time()
        
        if not self.circuit_breaker.can_execute():
            error_msg = f"Circuit breaker open for {self.handler_name}"
            await self._record_circuit_breaker_rejection(event, error_msg)
            return HandlerResult.failure(error_msg, should_retry=False)
        
        try:
            # Procesar el evento
            result = await self.handle(event)
            
            # Registrar éxito
            processing_time = (time.time() - start_time) * 1000
            self.circuit_breaker.record_success()
            
            return HandlerResult.success_with_events(
                result or [],
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self.circuit_breaker.record_failure()
            
            # Clasificar error
            error_type = self._classify_error(e)
            error_event = self._create_error_event(event, e, error_type, processing_time)
            
            # Registrar métricas
            self.metrics.record_error(error_event)
            
            # Determinar si debe reintentarse
            should_retry = self._should_retry(error_type, event)
            
            if not should_retry:
                # Enviar a DLQ si no se puede reintentar
                await self._send_to_dlq(event, e, error_type)
            
            return HandlerResult.failure(
                str(e),
                should_retry=should_retry,
                processing_time_ms=processing_time
            )
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """Clasifica un error según su tipo"""
        if isinstance(error, TimeoutError):
            return ErrorType.TIMEOUT
        elif isinstance(error, ConnectionError):
            return ErrorType.TRANSIENT
        elif isinstance(error, ValidationError):
            return ErrorType.VALIDATION
        elif isinstance(error, PermissionError):
            return ErrorType.AUTHORIZATION
        elif isinstance(error, ValueError):
            return ErrorType.BUSINESS_RULE
        else:
            return ErrorType.SYSTEM
    
    def _should_retry(self, error_type: ErrorType, event: DomainEvent) -> bool:
        """Determina si un error debe reintentarse"""
        retry_policy = ErrorRetryPolicy.get_policy_for_error(error_type)
        current_retry_count = getattr(event, 'retry_count', 0)
        return current_retry_count < retry_policy.max_attempts
    
    async def _send_to_dlq(self, event: DomainEvent, error: Exception, error_type: ErrorType):
        """Envía un evento al Dead Letter Queue"""
        dlq_message = DeadLetterMessage(
            message_id=uuid4(),
            original_event=event,
            handler_name=self.handler_name,
            error_type=error_type,
            error_message=str(error),
            retry_count=getattr(event, 'retry_count', 0),
            first_failed_at=datetime.now(),
            last_failed_at=datetime.now(),
            requires_manual_intervention=error_type in [ErrorType.SYSTEM, ErrorType.CORRUPTION]
        )
        await self.dlq_manager.add_to_dlq(dlq_message)
```

---

## 📋 Patrones por Dominio

### 1. **Stock Domain Error Patterns**

```python
class StockErrorPatterns:
    """Patrones de error específicos del dominio Stock"""
    
    @staticmethod
    def handle_insufficient_stock(product_id: str, requested_qty: Decimal, available_qty: Decimal) -> List[DomainEvent]:
        """Maneja error de stock insuficiente"""
        return [
            InsufficientStockDetected(
                event_id=uuid4(),
                occurred_at=datetime.now(),
                aggregate_id=product_id,
                aggregate_type="Product",
                product_id=product_id,
                requested_quantity=requested_qty,
                available_quantity=available_qty,
                shortage_quantity=requested_qty - available_qty
            )
        ]
    
    @staticmethod
    def handle_expired_lot_allocation(lot_id: str, expiry_date: date) -> List[DomainEvent]:
        """Maneja asignación de lote expirado"""
        return [
            ExpiredLotAllocationAttempted(
                event_id=uuid4(),
                occurred_at=datetime.now(),
                aggregate_id=lot_id,
                aggregate_type="StockLot",
                lot_id=lot_id,
                expiry_date=expiry_date,
                requires_lot_review=True
            )
        ]
```

### 2. **POS Domain Error Patterns**

```python
class POSErrorPatterns:
    """Patrones de error específicos del dominio POS"""
    
    @staticmethod
    def handle_payment_failure(sale_id: str, payment_data: Dict[str, Any], error_reason: str) -> List[DomainEvent]:
        """Maneja fallo de pago"""
        return [
            PaymentFailed(
                event_id=uuid4(),
                occurred_at=datetime.now(),
                aggregate_id=sale_id,
                aggregate_type="Sale",
                sale_id=sale_id,
                payment_method=payment_data.get('method'),
                amount=payment_data.get('amount'),
                failure_reason=error_reason,
                requires_stock_release=True
            )
        ]
    
    @staticmethod
    def handle_pricing_calculation_error(sale_id: str, items: List[Dict], error_details: str) -> List[DomainEvent]:
        """Maneja error en cálculo de precios"""
        return [
            PricingCalculationFailed(
                event_id=uuid4(),
                occurred_at=datetime.now(),
                aggregate_id=sale_id,
                aggregate_type="Sale",
                sale_id=sale_id,
                items=items,
                error_details=error_details,
                fallback_to_manual_pricing=True
            )
        ]
```

---

## 🎯 Checklist de Implementación

### Clasificación y Políticas ✅
- [x] ErrorType y ErrorSeverity enums
- [x] ErrorRetryPolicy por tipo de error
- [x] Circuit Breaker pattern
- [x] Escalation rules

### Compensación y Sagas ✅
- [x] CompensationEvent base class
- [x] SagaOrchestrator interface
- [x] POSSaleSaga example
- [x] Rollback patterns

### Dead Letter Queue ✅
- [x] DeadLetterMessage structure
- [x] IDeadLetterQueueManager interface
- [x] Error escalation management
- [x] Manual intervention workflows

### Monitoring y Métricas ✅
- [x] ErrorEvent hierarchy
- [x] IErrorMetrics interface
- [x] Error classification logic
- [x] Dashboard requirements

### Handler Implementation ✅
- [x] BaseErrorHandler with circuit breaker
- [x] Error classification logic
- [x] Retry decision logic
- [x] DLQ integration

### Domain-Specific Patterns ✅
- [x] StockErrorPatterns
- [x] POSErrorPatterns
- [x] Business rule violation handling
- [x] Recovery event patterns

---

**Patrones de error handling definidos**: ✅  
**Estrategias de compensación establecidas**: ✅  
**Circuit breaker y DLQ implementados**: ✅  
**Listo para Fase 3 - Implementación de infraestructura**: ✅