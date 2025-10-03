"""
Event System Utilities - Common utilities, decorators, and helpers
Provides convenient functions and decorators for working with the event system
"""

import asyncio
import functools
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union
from uuid import UUID, uuid4

from .base import DomainEvent, IEventHandler, HandlerResult
from .manager import get_event_system


logger = logging.getLogger(__name__)

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


# Event creation utilities

def create_event_id() -> UUID:
    """Create a new event ID"""
    return uuid4()


def create_correlation_id() -> str:
    """Create a new correlation ID"""
    return str(uuid4())


def get_current_timestamp() -> datetime:
    """Get current UTC timestamp"""
    return datetime.now(timezone.utc)


def create_event_metadata(
    correlation_id: Optional[str] = None,
    causation_id: Optional[UUID] = None,
    user_id: Optional[str] = None,
    source: Optional[str] = None,
    **additional_metadata
) -> Dict[str, Any]:
    """Create standard event metadata"""
    metadata = {
        'correlation_id': correlation_id or create_correlation_id(),
        'timestamp': get_current_timestamp(),
        **additional_metadata
    }
    
    if causation_id:
        metadata['causation_id'] = causation_id
    if user_id:
        metadata['user_id'] = user_id
    if source:
        metadata['source'] = source
    
    return metadata


# Event handler decorators

def event_handler(
    event_type: str,
    handler_name: Optional[str] = None,
    auto_register: bool = True,
    retry_count: int = 3,
    timeout_seconds: float = 30.0
):
    """
    Decorator to mark a function as an event handler
    
    Args:
        event_type: The type of event this handler processes
        handler_name: Optional name for the handler (defaults to function name)
        auto_register: Whether to automatically register the handler
        retry_count: Number of retries on failure
        timeout_seconds: Handler timeout in seconds
    """
    def decorator(func: F) -> F:
        # Store handler metadata
        func._event_handler_metadata = {
            'event_type': event_type,
            'handler_name': handler_name or func.__name__,
            'auto_register': auto_register,
            'retry_count': retry_count,
            'timeout_seconds': timeout_seconds
        }
        
        # Create wrapper for async functions
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    result = await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=timeout_seconds
                    )
                    return HandlerResult.success(result)
                except asyncio.TimeoutError:
                    logger.error(f"Handler {func.__name__} timed out after {timeout_seconds}s")
                    return HandlerResult.failure(f"Handler timed out after {timeout_seconds}s")
                except Exception as e:
                    logger.error(f"Handler {func.__name__} failed: {e}")
                    return HandlerResult.failure(str(e))
            
            return async_wrapper
        else:
            # Create wrapper for sync functions
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    result = func(*args, **kwargs)
                    return HandlerResult.success(result)
                except Exception as e:
                    logger.error(f"Handler {func.__name__} failed: {e}")
                    return HandlerResult.failure(str(e))
            
            return sync_wrapper
    
    return decorator


def saga_handler(
    saga_name: str,
    step_name: str,
    compensation_event_type: Optional[str] = None
):
    """
    Decorator for saga step handlers
    
    Args:
        saga_name: Name of the saga
        step_name: Name of this step in the saga
        compensation_event_type: Event type to publish for compensation
    """
    def decorator(func: F) -> F:
        func._saga_handler_metadata = {
            'saga_name': saga_name,
            'step_name': step_name,
            'compensation_event_type': compensation_event_type
        }
        return func
    
    return decorator


def compensating_handler(original_event_type: str):
    """
    Decorator for compensation handlers
    
    Args:
        original_event_type: The event type this handler compensates for
    """
    def decorator(func: F) -> F:
        func._compensating_handler_metadata = {
            'original_event_type': original_event_type
        }
        return func
    
    return decorator


# Event publishing utilities

async def publish_event(event: DomainEvent) -> None:
    """Publish an event using the global event system"""
    event_system = get_event_system()
    await event_system.publish_event(event)


async def publish_events(events: List[DomainEvent]) -> None:
    """Publish multiple events"""
    event_system = get_event_system()
    for event in events:
        await event_system.publish_event(event)


async def publish_domain_event(
    event_type: str,
    aggregate_id: str,
    data: Dict[str, Any],
    version: int = 1,
    correlation_id: Optional[str] = None,
    causation_id: Optional[UUID] = None,
    **metadata
) -> DomainEvent:
    """
    Create and publish a domain event
    
    Args:
        event_type: Type of the event
        aggregate_id: ID of the aggregate that generated the event
        data: Event data
        version: Event version
        correlation_id: Correlation ID for tracing
        causation_id: ID of the event that caused this event
        **metadata: Additional metadata
    
    Returns:
        The created and published event
    """
    event_metadata = create_event_metadata(
        correlation_id=correlation_id,
        causation_id=causation_id,
        **metadata
    )
    
    event = DomainEvent(
        event_id=create_event_id(),
        event_type=event_type,
        aggregate_id=aggregate_id,
        data=data,
        version=version,
        metadata=event_metadata
    )
    
    await publish_event(event)
    return event


# Handler registration utilities

class EventHandlerRegistry:
    """Registry for automatically registering event handlers"""
    
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._registered = False
    
    def register_handler(self, event_type: str, handler: Callable):
        """Register a handler for an event type"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def register_handlers_from_module(self, module):
        """Register all handlers from a module"""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if hasattr(attr, '_event_handler_metadata'):
                metadata = attr._event_handler_metadata
                if metadata['auto_register']:
                    self.register_handler(metadata['event_type'], attr)
    
    def register_handlers_from_class(self, cls: Type):
        """Register all handlers from a class"""
        for attr_name in dir(cls):
            if not attr_name.startswith('_'):
                attr = getattr(cls, attr_name)
                if hasattr(attr, '_event_handler_metadata'):
                    metadata = attr._event_handler_metadata
                    if metadata['auto_register']:
                        self.register_handler(metadata['event_type'], attr)
    
    async def register_all_handlers(self):
        """Register all collected handlers with the event system"""
        if self._registered:
            return
        
        event_system = get_event_system()
        
        for event_type, handlers in self._handlers.items():
            for handler in handlers:
                metadata = getattr(handler, '_event_handler_metadata', {})
                handler_name = metadata.get('handler_name', handler.__name__)
                
                # Create handler wrapper
                class HandlerWrapper(IEventHandler):
                    def __init__(self, func):
                        self.func = func
                    
                    async def handle(self, event: DomainEvent) -> HandlerResult:
                        if asyncio.iscoroutinefunction(self.func):
                            return await self.func(event)
                        else:
                            return self.func(event)
                
                await event_system.register_handler(
                    event_type,
                    HandlerWrapper(handler),
                    handler_name
                )
        
        self._registered = True
        logger.info(f"Registered {sum(len(handlers) for handlers in self._handlers.values())} event handlers")


# Global registry instance
_global_registry = EventHandlerRegistry()


def get_handler_registry() -> EventHandlerRegistry:
    """Get the global handler registry"""
    return _global_registry


def register_module_handlers(module):
    """Register all handlers from a module"""
    _global_registry.register_handlers_from_module(module)


def register_class_handlers(cls: Type):
    """Register all handlers from a class"""
    _global_registry.register_handlers_from_class(cls)


async def register_all_handlers():
    """Register all collected handlers"""
    await _global_registry.register_all_handlers()


# Event filtering and querying utilities

class EventFilter:
    """Utility for filtering events"""
    
    def __init__(self):
        self.filters = []
    
    def by_type(self, event_type: str):
        """Filter by event type"""
        self.filters.append(lambda e: e.event_type == event_type)
        return self
    
    def by_aggregate_id(self, aggregate_id: str):
        """Filter by aggregate ID"""
        self.filters.append(lambda e: e.aggregate_id == aggregate_id)
        return self
    
    def by_correlation_id(self, correlation_id: str):
        """Filter by correlation ID"""
        self.filters.append(lambda e: e.metadata.get('correlation_id') == correlation_id)
        return self
    
    def by_date_range(self, start_date: datetime, end_date: datetime):
        """Filter by date range"""
        self.filters.append(lambda e: start_date <= e.timestamp <= end_date)
        return self
    
    def by_user_id(self, user_id: str):
        """Filter by user ID"""
        self.filters.append(lambda e: e.metadata.get('user_id') == user_id)
        return self
    
    def custom_filter(self, filter_func: Callable[[DomainEvent], bool]):
        """Add custom filter function"""
        self.filters.append(filter_func)
        return self
    
    def apply(self, events: List[DomainEvent]) -> List[DomainEvent]:
        """Apply all filters to a list of events"""
        filtered_events = events
        for filter_func in self.filters:
            filtered_events = [e for e in filtered_events if filter_func(e)]
        return filtered_events


# Event validation utilities

def validate_event_data(event: DomainEvent, schema: Dict[str, Any]) -> List[str]:
    """
    Validate event data against a schema
    
    Args:
        event: The event to validate
        schema: Simple schema definition
    
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Check required fields
    required_fields = schema.get('required', [])
    for field in required_fields:
        if field not in event.data:
            errors.append(f"Missing required field: {field}")
    
    # Check field types
    field_types = schema.get('types', {})
    for field, expected_type in field_types.items():
        if field in event.data:
            actual_value = event.data[field]
            if not isinstance(actual_value, expected_type):
                errors.append(f"Field {field} should be {expected_type.__name__}, got {type(actual_value).__name__}")
    
    return errors


# Performance and debugging utilities

class EventTracer:
    """Utility for tracing event flows"""
    
    def __init__(self):
        self.traces: Dict[str, List[Dict[str, Any]]] = {}
    
    def start_trace(self, correlation_id: str, description: str = ""):
        """Start tracing events for a correlation ID"""
        self.traces[correlation_id] = [{
            'timestamp': get_current_timestamp(),
            'action': 'trace_started',
            'description': description
        }]
    
    def add_event(self, correlation_id: str, event: DomainEvent, action: str = "event_published"):
        """Add an event to the trace"""
        if correlation_id not in self.traces:
            self.traces[correlation_id] = []
        
        self.traces[correlation_id].append({
            'timestamp': get_current_timestamp(),
            'action': action,
            'event_type': event.event_type,
            'event_id': str(event.event_id),
            'aggregate_id': event.aggregate_id
        })
    
    def add_handler_execution(self, correlation_id: str, handler_name: str, result: HandlerResult):
        """Add handler execution to the trace"""
        if correlation_id not in self.traces:
            self.traces[correlation_id] = []
        
        self.traces[correlation_id].append({
            'timestamp': get_current_timestamp(),
            'action': 'handler_executed',
            'handler_name': handler_name,
            'success': result.success,
            'error': result.error_message if not result.success else None
        })
    
    def get_trace(self, correlation_id: str) -> List[Dict[str, Any]]:
        """Get the trace for a correlation ID"""
        return self.traces.get(correlation_id, [])
    
    def get_all_traces(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all traces"""
        return self.traces.copy()
    
    def clear_trace(self, correlation_id: str):
        """Clear a specific trace"""
        if correlation_id in self.traces:
            del self.traces[correlation_id]
    
    def clear_all_traces(self):
        """Clear all traces"""
        self.traces.clear()


# Global tracer instance
_global_tracer = EventTracer()


def get_event_tracer() -> EventTracer:
    """Get the global event tracer"""
    return _global_tracer


def start_event_trace(correlation_id: str, description: str = ""):
    """Start tracing events for a correlation ID"""
    _global_tracer.start_trace(correlation_id, description)


def trace_event(correlation_id: str, event: DomainEvent, action: str = "event_published"):
    """Add an event to the trace"""
    _global_tracer.add_event(correlation_id, event, action)


# Context utilities

class EventContext:
    """Context for event processing"""
    
    def __init__(self, correlation_id: str, user_id: Optional[str] = None, source: Optional[str] = None):
        self.correlation_id = correlation_id
        self.user_id = user_id
        self.source = source
        self.metadata = {}
    
    def add_metadata(self, key: str, value: Any):
        """Add metadata to the context"""
        self.metadata[key] = value
    
    def create_event_metadata(self, **additional_metadata) -> Dict[str, Any]:
        """Create event metadata from this context"""
        metadata = {
            'correlation_id': self.correlation_id,
            'timestamp': get_current_timestamp(),
            **self.metadata,
            **additional_metadata
        }
        
        if self.user_id:
            metadata['user_id'] = self.user_id
        if self.source:
            metadata['source'] = self.source
        
        return metadata


# Context variable for current event context
import contextvars
current_event_context: contextvars.ContextVar[Optional[EventContext]] = contextvars.ContextVar('current_event_context', default=None)


def get_current_context() -> Optional[EventContext]:
    """Get the current event context"""
    return current_event_context.get()


def set_current_context(context: EventContext):
    """Set the current event context"""
    current_event_context.set(context)


def create_context(correlation_id: Optional[str] = None, user_id: Optional[str] = None, source: Optional[str] = None) -> EventContext:
    """Create a new event context"""
    return EventContext(
        correlation_id=correlation_id or create_correlation_id(),
        user_id=user_id,
        source=source
    )


async def with_context(context: EventContext, coro):
    """Execute a coroutine with a specific event context"""
    token = current_event_context.set(context)
    try:
        return await coro
    finally:
        current_event_context.reset(token)