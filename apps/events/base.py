"""
Base classes for Domain Events and Event Handling
Implements the core infrastructure for event-driven architecture
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4
import json
import time


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Base class for all domain events"""
    
    # Event metadata - todos con valores por defecto usando field()
    event_id: UUID = field(default_factory=uuid4)
    event_type: str = field(default="")
    event_version: str = field(default="1.0")
    occurred_at: datetime = field(default_factory=datetime.now)
    
    # Aggregate information - todos con valores por defecto
    aggregate_id: str = field(default="")
    aggregate_type: str = field(default="")
    
    # Event sequence and causation - todos opcionales
    sequence_number: Optional[int] = field(default=None)
    causation_id: Optional[UUID] = field(default=None)  # ID of the command that caused this event
    correlation_id: Optional[UUID] = field(default=None)  # ID to correlate related events
    
    # Metadata - con factory por defecto
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate event after initialization"""
        # Auto-populate event_type with class name if not provided
        if not self.event_type:
            object.__setattr__(self, 'event_type', self.__class__.__name__)
        
        # Allow aggregate_id to be provided via subclass property; ensure it's not empty
        if not getattr(self, 'aggregate_id'):
            raise ValueError("aggregate_id is required")
        
        # Auto-populate aggregate_type with module path if not provided
        if not self.aggregate_type:
            object.__setattr__(self, 'aggregate_type', self.__class__.__module__)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return {
            'event_id': str(self.event_id),
            'event_type': self.event_type,
            'event_version': self.event_version,
            'occurred_at': self.occurred_at.isoformat(),
            'aggregate_id': self.aggregate_id,
            'aggregate_type': self.aggregate_type,
            'sequence_number': self.sequence_number,
            'causation_id': str(self.causation_id) if self.causation_id else None,
            'correlation_id': str(self.correlation_id) if self.correlation_id else None,
            'metadata': self.metadata,
            'data': self._get_event_data()
        }
    
    def _get_event_data(self) -> Dict[str, Any]:
        """Get event-specific data (override in subclasses)"""
        # Get all fields except the base DomainEvent fields
        base_fields = {
            'event_id', 'event_type', 'event_version', 'occurred_at',
            'aggregate_id', 'aggregate_type', 'sequence_number',
            'causation_id', 'correlation_id', 'metadata'
        }
        
        event_data = {}
        for field_name, field_value in self.__dict__.items():
            if field_name not in base_fields:
                if isinstance(field_value, UUID):
                    event_data[field_name] = str(field_value)
                elif isinstance(field_value, datetime):
                    event_data[field_name] = field_value.isoformat()
                else:
                    event_data[field_name] = field_value
        
        return event_data
    
    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict(), default=str)


class EventPriority(Enum):
    """Event processing priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class EventEnvelope:
    """Wrapper for events with routing and processing metadata"""
    
    event: DomainEvent
    priority: EventPriority = EventPriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3
    delay_seconds: float = 0
    
    # Routing information
    routing_key: Optional[str] = None
    target_handlers: Optional[List[str]] = None
    
    # Processing metadata
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_for: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    
    # Tracing
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    
    def is_expired(self, ttl_seconds: int = 3600) -> bool:
        """Check if envelope has expired"""
        if not self.created_at:
            return False
        return (datetime.now() - self.created_at).total_seconds() > ttl_seconds
    
    def should_process_now(self) -> bool:
        """Check if event should be processed now"""
        if self.scheduled_for is None:
            return True
        return datetime.now() >= self.scheduled_for
    
    def increment_retry(self, delay_seconds: float = 0) -> None:
        """Increment retry count and set delay"""
        object.__setattr__(self, 'retry_count', self.retry_count + 1)
        if delay_seconds > 0:
            object.__setattr__(self, 'scheduled_for', 
                             datetime.now().timestamp() + delay_seconds)


@dataclass
class HandlerResult:
    """Result of event handler processing"""
    
    success: bool
    events_to_publish: List[DomainEvent] = field(default_factory=list)
    error_message: Optional[str] = None
    should_retry: bool = False
    processing_time_ms: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def success_with_events(cls, events: List[DomainEvent], 
                          processing_time_ms: float = 0) -> 'HandlerResult':
        """Create successful result with events to publish"""
        return cls(
            success=True,
            events_to_publish=events,
            processing_time_ms=processing_time_ms
        )
    
    @classmethod
    def success_no_events(cls, processing_time_ms: float = 0) -> 'HandlerResult':
        """Create successful result with no events"""
        return cls(
            success=True,
            processing_time_ms=processing_time_ms
        )
    
    @classmethod
    def failure(cls, error_message: str, should_retry: bool = True,
                processing_time_ms: float = 0) -> 'HandlerResult':
        """Create failure result"""
        return cls(
            success=False,
            error_message=error_message,
            should_retry=should_retry,
            processing_time_ms=processing_time_ms
        )


class IEventHandler(ABC):
    """Interface for event handlers"""
    
    @property
    @abstractmethod
    def handler_name(self) -> str:
        """Unique name for this handler"""
        pass
    
    @property
    @abstractmethod
    def handled_events(self) -> List[str]:
        """List of event types this handler can process"""
        pass
    
    @abstractmethod
    async def handle(self, event: DomainEvent) -> HandlerResult:
        """Handle a domain event"""
        pass
    
    def can_handle(self, event_type: str) -> bool:
        """Check if this handler can process the given event type"""
        return event_type in self.handled_events


class RetryStrategy(Enum):
    """Retry strategies for failed event processing"""
    NO_RETRY = "no_retry"
    FIXED_DELAY = "fixed_delay"
    LINEAR_BACKOFF = "linear_backoff"
    EXPONENTIAL_BACKOFF = "exponential_backoff"


@dataclass
class RetryPolicy:
    """Policy for retrying failed event processing"""
    
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    max_attempts: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 300.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    
    @classmethod
    def no_retry(cls) -> 'RetryPolicy':
        """Create a no-retry policy"""
        return cls(
            strategy=RetryStrategy.NO_RETRY,
            max_attempts=1
        )
    
    @classmethod
    def fixed_delay(cls, delay_seconds: float = 5.0, max_attempts: int = 3) -> 'RetryPolicy':
        """Create a fixed delay retry policy"""
        return cls(
            strategy=RetryStrategy.FIXED_DELAY,
            max_attempts=max_attempts,
            initial_delay_seconds=delay_seconds,
            max_delay_seconds=delay_seconds
        )
    
    @classmethod
    def exponential_backoff(cls, initial_delay: float = 1.0, 
                          max_attempts: int = 5) -> 'RetryPolicy':
        """Create an exponential backoff retry policy"""
        return cls(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            max_attempts=max_attempts,
            initial_delay_seconds=initial_delay,
        )
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number"""
        if self.strategy == RetryStrategy.NO_RETRY:
            return 0
        
        if self.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.initial_delay_seconds
        elif self.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.initial_delay_seconds * attempt
        elif self.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.initial_delay_seconds * (self.backoff_multiplier ** (attempt - 1))
        else:
            delay = self.initial_delay_seconds
        
        # Apply max delay limit
        delay = min(delay, self.max_delay_seconds)
        
        # Apply jitter if enabled
        if self.jitter and delay > 0:
            import random
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        return max(0, delay)


# Event Store interfaces
class IEventStore(ABC):
    """Interface for event persistence"""
    
    @abstractmethod
    async def save_event(self, event: DomainEvent) -> None:
        """Save a single event"""
        pass
    
    @abstractmethod
    async def save_events(self, events: List[DomainEvent]) -> None:
        """Save multiple events atomically"""
        pass
    
    @abstractmethod
    async def get_events(self, aggregate_id: str, 
                        from_sequence: Optional[int] = None) -> List[DomainEvent]:
        """Get events for an aggregate"""
        pass
    
    @abstractmethod
    async def get_events_by_type(self, event_type: str, 
                               limit: int = 100) -> List[DomainEvent]:
        """Get events by type"""
        pass


# Event Bus interfaces
class IEventBus(ABC):
    """Interface for event bus"""
    
    @abstractmethod
    async def publish(self, event: DomainEvent, 
                     priority: EventPriority = EventPriority.NORMAL) -> None:
        """Publish a single event"""
        pass
    
    @abstractmethod
    async def publish_batch(self, events: List[DomainEvent],
                          priority: EventPriority = EventPriority.NORMAL) -> None:
        """Publish multiple events"""
        pass
    
    @abstractmethod
    async def subscribe(self, handler: IEventHandler) -> None:
        """Subscribe a handler to events"""
        pass
    
    @abstractmethod
    async def unsubscribe(self, handler: IEventHandler) -> None:
        """Unsubscribe a handler"""
        pass
    
    @abstractmethod
    async def start(self) -> None:
        """Start the event bus"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the event bus"""
        pass


# Metrics and monitoring interfaces
class IEventMetrics(ABC):
    """Interface for event metrics collection"""
    
    @abstractmethod
    def record_event_published(self, event_type: str, processing_time_ms: float) -> None:
        """Record event publication"""
        pass
    
    @abstractmethod
    def record_event_processed(self, event_type: str, handler_name: str, 
                             success: bool, processing_time_ms: float) -> None:
        """Record event processing"""
        pass
    
    @abstractmethod
    def record_handler_error(self, handler_name: str, error_type: str) -> None:
        """Record handler error"""
        pass
    
    @abstractmethod
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        pass