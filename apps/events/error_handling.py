"""
Error Handling Infrastructure for Event-Driven Architecture
Implements circuit breakers, retry policies, dead letter queues, and error escalation
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
import json

from .base import DomainEvent, HandlerResult, IEventHandler


logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Classification of error types for handling strategies"""
    # Recoverable errors (automatic retry)
    TRANSIENT = "transient"           # Temporary network, DB, etc.
    TIMEOUT = "timeout"               # Processing timeouts
    RATE_LIMIT = "rate_limit"         # Rate limits exceeded
    RESOURCE_UNAVAILABLE = "resource_unavailable"  # Resources temporarily unavailable
    
    # Business errors (no retry, compensation possible)
    BUSINESS_RULE = "business_rule"   # Business rule violations
    VALIDATION = "validation"         # Invalid data
    AUTHORIZATION = "authorization"   # Insufficient permissions
    NOT_FOUND = "not_found"          # Resource not found
    
    # Critical errors (no retry, manual intervention)
    SYSTEM = "system"                 # System errors
    CONFIGURATION = "configuration"  # Configuration errors
    CORRUPTION = "corruption"        # Data corruption
    SECURITY = "security"            # Security violations


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"           # Non-critical functionality affected
    MEDIUM = "medium"     # Non-critical functionality affected
    HIGH = "high"         # Critical functionality affected
    CRITICAL = "critical" # System non-functional


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit open, rejecting requests
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5          # Failures before opening
    success_threshold: int = 3          # Successes to close from half-open
    timeout_seconds: int = 60           # Time before attempting reset
    monitoring_window_seconds: int = 300 # Window for monitoring failures


class CircuitBreaker:
    """Circuit breaker implementation for preventing cascade failures"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state_changed_at = datetime.now()
    
    def can_execute(self) -> bool:
        """Check if execution is allowed"""
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
        """Record successful execution"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._close_circuit()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0  # Reset failure count on success
    
    def record_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self._open_circuit()
        elif self.state == CircuitState.HALF_OPEN:
            self._open_circuit()
    
    def _should_attempt_reset(self) -> bool:
        """Check if should attempt to reset circuit"""
        if self.last_failure_time is None:
            return True
        return datetime.now() - self.last_failure_time > timedelta(
            seconds=self.config.timeout_seconds
        )
    
    def _open_circuit(self):
        """Open the circuit"""
        self.state = CircuitState.OPEN
        self.state_changed_at = datetime.now()
        self.success_count = 0
        logger.warning(f"Circuit breaker {self.name} opened")
    
    def _close_circuit(self):
        """Close the circuit"""
        self.state = CircuitState.CLOSED
        self.state_changed_at = datetime.now()
        self.failure_count = 0
        self.success_count = 0
        logger.info(f"Circuit breaker {self.name} closed")
    
    def get_state_info(self) -> Dict[str, Any]:
        """Get current state information"""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'state_changed_at': self.state_changed_at.isoformat(),
            'time_in_current_state': (datetime.now() - self.state_changed_at).total_seconds()
        }


@dataclass(frozen=True)
class ErrorEvent(DomainEvent):
    """Base event for error reporting"""
    event_type: str = "system.error.occurred"
    event_version: str = "1.0"
    
    error_id: UUID = field(default_factory=uuid4)
    error_type: ErrorType = ErrorType.SYSTEM
    error_severity: ErrorSeverity = ErrorSeverity.MEDIUM
    error_message: str = ""
    error_details: Dict[str, Any] = field(default_factory=dict)
    
    # Context
    handler_name: Optional[str] = None
    original_event_id: Optional[UUID] = None
    original_event_type: Optional[str] = None
    
    # Metrics
    processing_time_ms: float = 0
    retry_count: int = 0
    
    # Stack trace (only for critical errors)
    stack_trace: Optional[str] = None


@dataclass(frozen=True)
class HandlerTimeoutEvent(ErrorEvent):
    """Event for handler timeouts"""
    event_type: str = "system.handler.timeout"
    error_type: ErrorType = ErrorType.TIMEOUT
    
    timeout_seconds: int = 0
    handler_name: str = ""


@dataclass(frozen=True)
class BusinessRuleViolationEvent(ErrorEvent):
    """Event for business rule violations"""
    event_type: str = "business.rule.violation"
    error_type: ErrorType = ErrorType.BUSINESS_RULE
    
    rule_name: str = ""
    rule_description: str = ""
    violated_constraints: List[str] = field(default_factory=list)


@dataclass
class DeadLetterMessage:
    """Message in dead letter queue"""
    message_id: UUID = field(default_factory=uuid4)
    original_event: Optional[DomainEvent] = None
    handler_name: str = ""
    error_type: ErrorType = ErrorType.SYSTEM
    error_message: str = ""
    retry_count: int = 0
    first_failed_at: datetime = field(default_factory=datetime.now)
    last_failed_at: datetime = field(default_factory=datetime.now)
    requires_manual_intervention: bool = False
    escalation_level: int = 0
    resolution_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'message_id': str(self.message_id),
            'original_event': self.original_event.to_dict() if self.original_event else None,
            'handler_name': self.handler_name,
            'error_type': self.error_type.value,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'first_failed_at': self.first_failed_at.isoformat(),
            'last_failed_at': self.last_failed_at.isoformat(),
            'requires_manual_intervention': self.requires_manual_intervention,
            'escalation_level': self.escalation_level,
            'resolution_notes': self.resolution_notes,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


class IDeadLetterQueueManager(ABC):
    """Interface for dead letter queue management"""
    
    @abstractmethod
    async def add_to_dlq(self, message: DeadLetterMessage) -> None:
        """Add message to dead letter queue"""
        pass
    
    @abstractmethod
    async def get_dlq_messages(self, limit: int = 100) -> List[DeadLetterMessage]:
        """Get messages from dead letter queue"""
        pass
    
    @abstractmethod
    async def retry_message(self, message_id: UUID) -> bool:
        """Retry processing a message from DLQ"""
        pass
    
    @abstractmethod
    async def mark_as_resolved(self, message_id: UUID, resolution_notes: str) -> None:
        """Mark message as resolved manually"""
        pass
    
    @abstractmethod
    async def get_dlq_statistics(self) -> Dict[str, Any]:
        """Get DLQ statistics"""
        pass


class InMemoryDeadLetterQueueManager(IDeadLetterQueueManager):
    """In-memory implementation of dead letter queue manager"""
    
    def __init__(self):
        self._messages: Dict[UUID, DeadLetterMessage] = {}
        self._stats = {
            'total_messages': 0,
            'resolved_messages': 0,
            'pending_messages': 0,
            'manual_interventions': 0
        }
    
    async def add_to_dlq(self, message: DeadLetterMessage) -> None:
        """Add message to dead letter queue"""
        self._messages[message.message_id] = message
        self._stats['total_messages'] += 1
        self._stats['pending_messages'] += 1
        
        if message.requires_manual_intervention:
            self._stats['manual_interventions'] += 1
        
        logger.error(f"Added message to DLQ: {message.handler_name} - {message.error_message}")
    
    async def get_dlq_messages(self, limit: int = 100) -> List[DeadLetterMessage]:
        """Get messages from dead letter queue"""
        messages = list(self._messages.values())
        # Sort by last failed time, most recent first
        messages.sort(key=lambda m: m.last_failed_at, reverse=True)
        return messages[:limit]
    
    async def retry_message(self, message_id: UUID) -> bool:
        """Retry processing a message from DLQ"""
        if message_id not in self._messages:
            return False
        
        message = self._messages[message_id]
        if message.resolved_at is not None:
            return False  # Already resolved
        
        # TODO: Re-queue the original event for processing
        logger.info(f"Retrying DLQ message {message_id}")
        return True
    
    async def mark_as_resolved(self, message_id: UUID, resolution_notes: str) -> None:
        """Mark message as resolved manually"""
        if message_id not in self._messages:
            return
        
        message = self._messages[message_id]
        message.resolution_notes = resolution_notes
        message.resolved_at = datetime.now()
        
        self._stats['resolved_messages'] += 1
        self._stats['pending_messages'] -= 1
        
        logger.info(f"Marked DLQ message {message_id} as resolved: {resolution_notes}")
    
    async def get_dlq_statistics(self) -> Dict[str, Any]:
        """Get DLQ statistics"""
        return {
            **self._stats,
            'current_queue_size': len([m for m in self._messages.values() if m.resolved_at is None])
        }


@dataclass
class EscalationRule:
    """Rule for error escalation"""
    error_type: ErrorType
    severity: ErrorSeverity
    escalation_threshold: int
    escalation_channels: List[str]  # ["email", "slack", "pagerduty"]
    escalation_delay_minutes: int
    auto_escalate: bool = True


class IErrorEscalationManager(ABC):
    """Interface for error escalation management"""
    
    @abstractmethod
    async def evaluate_escalation(self, error_event: ErrorEvent) -> bool:
        """Evaluate if error should be escalated"""
        pass
    
    @abstractmethod
    async def escalate_error(self, error_event: ErrorEvent, escalation_level: int) -> None:
        """Escalate an error"""
        pass
    
    @abstractmethod
    async def get_escalation_history(self, error_id: UUID) -> List[Dict[str, Any]]:
        """Get escalation history"""
        pass


class BaseErrorHandler(IEventHandler):
    """Base handler with comprehensive error management"""
    
    def __init__(self, 
                 circuit_breaker: CircuitBreaker,
                 dlq_manager: IDeadLetterQueueManager):
        self.circuit_breaker = circuit_breaker
        self.dlq_manager = dlq_manager
    
    async def handle_with_error_management(self, event: DomainEvent) -> HandlerResult:
        """Handle event with complete error management"""
        start_time = datetime.now()
        
        if not self.circuit_breaker.can_execute():
            error_msg = f"Circuit breaker open for {self.handler_name}"
            await self._record_circuit_breaker_rejection(event, error_msg)
            return HandlerResult.failure(error_msg, should_retry=False)
        
        try:
            # Process the event
            result = await self.handle(event)
            
            # Record success
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self.circuit_breaker.record_success()
            
            return HandlerResult.success_with_events(
                result.events_to_publish if result else [],
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self.circuit_breaker.record_failure()
            
            # Classify error
            error_type = self._classify_error(e)
            
            # Determine if should retry
            should_retry = self._should_retry(error_type, event)
            
            if not should_retry:
                # Send to DLQ
                await self._send_to_dlq(event, e, error_type)
            
            return HandlerResult.failure(
                str(e),
                should_retry=should_retry,
                processing_time_ms=processing_time
            )
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify error by type"""
        if isinstance(error, TimeoutError):
            return ErrorType.TIMEOUT
        elif isinstance(error, ConnectionError):
            return ErrorType.TRANSIENT
        elif isinstance(error, ValueError):
            return ErrorType.VALIDATION
        elif isinstance(error, PermissionError):
            return ErrorType.AUTHORIZATION
        else:
            return ErrorType.SYSTEM
    
    def _should_retry(self, error_type: ErrorType, event: DomainEvent) -> bool:
        """Determine if error should be retried"""
        non_retryable = {
            ErrorType.BUSINESS_RULE,
            ErrorType.VALIDATION,
            ErrorType.AUTHORIZATION,
            ErrorType.NOT_FOUND,
            ErrorType.SYSTEM,
            ErrorType.CONFIGURATION,
            ErrorType.CORRUPTION,
            ErrorType.SECURITY
        }
        
        if error_type in non_retryable:
            return False
        
        # Check retry count
        current_retry_count = getattr(event, 'retry_count', 0)
        return current_retry_count < 3  # Max 3 retries
    
    async def _send_to_dlq(self, event: DomainEvent, error: Exception, error_type: ErrorType):
        """Send event to dead letter queue"""
        dlq_message = DeadLetterMessage(
            message_id=uuid4(),
            original_event=event,
            handler_name=self.handler_name,
            error_type=error_type,
            error_message=str(error),
            retry_count=getattr(event, 'retry_count', 0),
            first_failed_at=datetime.now(),
            last_failed_at=datetime.now(),
            requires_manual_intervention=error_type in {
                ErrorType.SYSTEM, ErrorType.CORRUPTION, ErrorType.SECURITY
            }
        )
        await self.dlq_manager.add_to_dlq(dlq_message)
    
    async def _record_circuit_breaker_rejection(self, event: DomainEvent, error_msg: str):
        """Record circuit breaker rejection"""
        logger.warning(f"Circuit breaker rejection: {error_msg} for event {event.event_type}")


class ErrorMetrics:
    """Simple error metrics collection"""
    
    def __init__(self):
        self._error_counts: Dict[str, int] = {}
        self._handler_errors: Dict[str, Dict[str, int]] = {}
        self._processing_times: List[float] = []
    
    def record_error(self, error_type: str, handler_name: str = None):
        """Record an error occurrence"""
        self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1
        
        if handler_name:
            if handler_name not in self._handler_errors:
                self._handler_errors[handler_name] = {}
            self._handler_errors[handler_name][error_type] = \
                self._handler_errors[handler_name].get(error_type, 0) + 1
    
    def record_processing_time(self, time_ms: float):
        """Record processing time"""
        self._processing_times.append(time_ms)
        # Keep only last 1000 measurements
        if len(self._processing_times) > 1000:
            self._processing_times = self._processing_times[-1000:]
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary"""
        avg_processing_time = (
            sum(self._processing_times) / len(self._processing_times)
            if self._processing_times else 0
        )
        
        return {
            'total_errors': sum(self._error_counts.values()),
            'error_breakdown': self._error_counts.copy(),
            'handler_errors': self._handler_errors.copy(),
            'avg_processing_time_ms': avg_processing_time,
            'total_processed': len(self._processing_times)
        }