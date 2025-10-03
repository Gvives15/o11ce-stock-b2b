"""
Event-driven architecture infrastructure for BFF application

This package provides a complete event-driven architecture implementation including:
- Domain events and event bus
- Event store and projections
- Error handling and monitoring
- Configuration and management
- Utilities and decorators

Usage:
    from apps.events import initialize_event_system, publish_event, event_handler
    
    # Initialize the system
    await initialize_event_system()
    
    # Define event handlers
    @event_handler('user.created')
    async def handle_user_created(event):
        # Handle the event
        pass
    
    # Publish events
    await publish_event(UserCreatedEvent(...))
"""

# Core components
from .base import (
    DomainEvent,
    EventEnvelope,
    HandlerResult,
    IEventHandler,
    IEventBus,
    IEventStore,
    IEventMetrics,
    RetryPolicy
)

from .bus import (
    InMemoryEventBus,
    EventBusManager
)

from .store import (
    InMemoryEventStore,
    EventRecord,
    EventQuery,
    EventStream,
    EventProjection,
    ProjectionManager,
    EventReplayService
)

from .error_handling import (
    ErrorType,
    ErrorSeverity,
    CircuitBreaker,
    CircuitBreakerConfig,
    ErrorEvent,
    DeadLetterMessage,
    InMemoryDeadLetterQueueManager,
    BaseErrorHandler,
    ErrorMetrics
)

from .monitoring import (
    MetricType,
    AlertSeverity,
    MetricPoint,
    Alert,
    InMemoryMetricsCollector,
    EventMetrics,
    HealthChecker,
    AlertManager,
    MonitoringDashboard
)

from .config import (
    EventSystemConfig,
    get_development_config,
    get_production_config,
    get_test_config,  # Cambiar de get_testing_config a get_test_config
    load_config_from_env,
    load_config_from_dict
)

from .manager import (
    EventSystemManager,
    get_event_system,
    set_event_system,
    initialize_event_system,
    shutdown_event_system
)

from .utils import (
    # Event creation utilities
    create_event_id,
    create_correlation_id,
    get_current_timestamp,
    create_event_metadata,
    
    # Decorators
    event_handler,
    saga_handler,
    compensating_handler,
    
    # Publishing utilities
    publish_event,
    publish_events,
    publish_domain_event,
    
    # Handler registration
    EventHandlerRegistry,
    get_handler_registry,
    register_module_handlers,
    register_class_handlers,
    register_all_handlers,
    
    # Filtering and validation
    EventFilter,
    validate_event_data,
    
    # Tracing and debugging
    EventTracer,
    get_event_tracer,
    start_event_trace,
    trace_event,
    
    # Context management
    EventContext,
    get_current_context,
    set_current_context,
    create_context,
    with_context
)

# Version information
__version__ = "1.0.0"
__author__ = "BFF Development Team"

# Public API
__all__ = [
    # Core components
    'DomainEvent',
    'EventEnvelope', 
    'HandlerResult',
    'IEventHandler',
    'IEventBus',
    'IEventStore',
    'IEventMetrics',
    'RetryPolicy',
    
    # Event bus
    'InMemoryEventBus',
    'EventBusManager',
    
    # Event store
    'InMemoryEventStore',
    'EventRecord',
    'EventQuery',
    'EventStream',
    'EventProjection',
    'ProjectionManager',
    'EventReplayService',
    
    # Error handling
    'ErrorType',
    'ErrorSeverity',
    'CircuitBreaker',
    'CircuitBreakerConfig',
    'ErrorEvent',
    'DeadLetterMessage',
    'InMemoryDeadLetterQueueManager',
    'BaseErrorHandler',
    'ErrorMetrics',
    
    # Monitoring
    'MetricType',
    'AlertSeverity',
    'MetricPoint',
    'Alert',
    'InMemoryMetricsCollector',
    'EventMetrics',
    'HealthChecker',
    'AlertManager',
    'MonitoringDashboard',
    
    # Configuration
    'EventSystemConfig',
    'get_development_config',
    'get_production_config',
    'get_test_config',
    'load_config_from_env',
    'load_config_from_dict',
    
    # Management
    'EventSystemManager',
    'get_event_system',
    'set_event_system',
    'initialize_event_system',
    'shutdown_event_system',
    
    # Utilities
    'create_event_id',
    'create_correlation_id',
    'get_current_timestamp',
    'create_event_metadata',
    'event_handler',
    'saga_handler',
    'compensating_handler',
    'publish_event',
    'publish_events',
    'publish_domain_event',
    'EventHandlerRegistry',
    'get_handler_registry',
    'register_module_handlers',
    'register_class_handlers',
    'register_all_handlers',
    'EventFilter',
    'validate_event_data',
    'EventTracer',
    'get_event_tracer',
    'start_event_trace',
    'trace_event',
    'EventContext',
    'get_current_context',
    'set_current_context',
    'create_context',
    'with_context'
]