"""
Event System Manager - Central orchestrator for the event-driven architecture
Manages lifecycle, configuration, and coordination of all event system components
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Type
from uuid import UUID

from .base import DomainEvent, IEventBus, IEventHandler, IEventStore, IEventMetrics
from .bus import InMemoryEventBus, EventBusManager
from .config import EventSystemConfig, get_development_config
from .error_handling import (
    InMemoryDeadLetterQueueManager, 
    IDeadLetterQueueManager,
    CircuitBreaker,
    CircuitBreakerConfig
)
from .monitoring import (
    InMemoryMetricsCollector,
    EventMetrics,
    HealthChecker,
    AlertManager,
    MonitoringDashboard,
    high_error_rate_condition,
    queue_size_condition,
    AlertSeverity
)
from .store import InMemoryEventStore, ProjectionManager, EventReplayService


logger = logging.getLogger(__name__)


class EventSystemManager:
    """Central manager for the entire event system"""
    
    def __init__(self, config: Optional[EventSystemConfig] = None):
        self.config = config or get_development_config()
        
        # Core components
        self._event_bus: Optional[IEventBus] = None
        self._event_store: Optional[IEventStore] = None
        self._dlq_manager: Optional[IDeadLetterQueueManager] = None
        
        # Monitoring components
        self._metrics_collector: Optional[InMemoryMetricsCollector] = None
        self._event_metrics: Optional[IEventMetrics] = None
        self._health_checker: Optional[HealthChecker] = None
        self._alert_manager: Optional[AlertManager] = None
        self._dashboard: Optional[MonitoringDashboard] = None
        
        # Management components
        self._projection_manager: Optional[ProjectionManager] = None
        self._replay_service: Optional[EventReplayService] = None
        
        # Circuit breakers for handlers
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # System state
        self._is_initialized = False
        self._is_running = False
        self._background_tasks: List[asyncio.Task] = []
    
    async def initialize(self) -> None:
        """Initialize all system components"""
        if self._is_initialized:
            logger.warning("Event system already initialized")
            return
        
        logger.info("Initializing event system...")
        
        # Validate configuration
        config_errors = self.config.validate()
        if config_errors:
            raise ValueError(f"Configuration errors: {', '.join(config_errors)}")
        
        # Initialize core components
        await self._initialize_core_components()
        
        # Initialize monitoring components
        if self.config.monitoring.enabled:
            await self._initialize_monitoring_components()
        
        # Initialize management components
        await self._initialize_management_components()
        
        self._is_initialized = True
        logger.info("Event system initialized successfully")
    
    async def start(self) -> None:
        """Start the event system"""
        if not self._is_initialized:
            await self.initialize()
        
        if self._is_running:
            logger.warning("Event system already running")
            return
        
        logger.info("Starting event system...")
        
        # Start event bus
        if hasattr(self._event_bus, 'start'):
            await self._event_bus.start()
        
        # Start projection manager
        if self._projection_manager:
            await self._projection_manager.start_projections()
        
        # Start monitoring tasks
        if self.config.monitoring.enabled:
            await self._start_monitoring_tasks()
        
        self._is_running = True
        logger.info("Event system started successfully")
    
    async def stop(self) -> None:
        """Stop the event system"""
        if not self._is_running:
            return
        
        logger.info("Stopping event system...")
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()
        
        # Stop projection manager
        if self._projection_manager:
            await self._projection_manager.stop_projections()
        
        # Stop event bus
        if hasattr(self._event_bus, 'stop'):
            await self._event_bus.stop()
        
        self._is_running = False
        logger.info("Event system stopped successfully")
    
    async def _initialize_core_components(self) -> None:
        """Initialize core event system components"""
        # Initialize event store
        self._event_store = InMemoryEventStore()
        logger.debug("Event store initialized")
        
        # Initialize dead letter queue manager
        self._dlq_manager = InMemoryDeadLetterQueueManager()
        logger.debug("Dead letter queue manager initialized")
        
        # Initialize event bus
        self._event_bus = InMemoryEventBus(
            max_concurrent_handlers=self.config.event_bus.max_concurrent_handlers,
            default_timeout_seconds=self.config.event_bus.default_timeout_seconds
        )
        
        # Set global event bus
        EventBusManager.set_instance(self._event_bus)
        logger.debug("Event bus initialized")
    
    async def _initialize_monitoring_components(self) -> None:
        """Initialize monitoring and metrics components"""
        # Initialize metrics collector
        self._metrics_collector = InMemoryMetricsCollector(
            max_points=self.config.monitoring.max_metric_points
        )
        
        # Initialize event metrics
        self._event_metrics = EventMetrics(self._metrics_collector)
        
        # Set metrics on event bus
        if hasattr(self._event_bus, 'set_metrics'):
            self._event_bus.set_metrics(self._event_metrics)
        
        # Initialize health checker
        self._health_checker = HealthChecker(self._metrics_collector)
        await self._register_health_checks()
        
        # Initialize alert manager
        self._alert_manager = AlertManager(self._metrics_collector)
        await self._register_alert_rules()
        
        # Initialize dashboard
        self._dashboard = MonitoringDashboard(
            self._metrics_collector,
            self._health_checker,
            self._alert_manager
        )
        
        logger.debug("Monitoring components initialized")
    
    async def _initialize_management_components(self) -> None:
        """Initialize management components"""
        # Initialize projection manager
        self._projection_manager = ProjectionManager(self._event_store)
        
        # Initialize replay service
        self._replay_service = EventReplayService(self._event_store)
        
        logger.debug("Management components initialized")
    
    async def _register_health_checks(self) -> None:
        """Register system health checks"""
        if not self._health_checker:
            return
        
        # Event bus health check
        async def event_bus_health():
            return self._event_bus is not None and self._is_running
        
        self._health_checker.register_check("event_bus", event_bus_health)
        
        # Event store health check
        async def event_store_health():
            try:
                stats = await self._event_store.get_statistics()
                return stats is not None
            except Exception:
                return False
        
        self._health_checker.register_check("event_store", event_store_health)
        
        # Dead letter queue health check
        async def dlq_health():
            try:
                stats = await self._dlq_manager.get_dlq_statistics()
                # Alert if too many pending messages
                return stats.get('pending_messages', 0) < 100
            except Exception:
                return False
        
        self._health_checker.register_check("dead_letter_queue", dlq_health)
    
    async def _register_alert_rules(self) -> None:
        """Register system alert rules"""
        if not self._alert_manager:
            return
        
        # High error rate alert
        self._alert_manager.add_alert_rule(
            name="high_error_rate",
            condition=high_error_rate_condition,
            severity=AlertSeverity.ERROR,
            description="High error rate detected in event handlers"
        )
        
        # Large queue size alert
        self._alert_manager.add_alert_rule(
            name="large_queue_size",
            condition=queue_size_condition,
            severity=AlertSeverity.WARNING,
            description="Event queue size is too large"
        )
        
        # Add notification handler for alerts
        async def log_alert(alert):
            logger.warning(f"ALERT: {alert.name} - {alert.description}")
        
        self._alert_manager.add_notification_handler(log_alert)
    
    async def _start_monitoring_tasks(self) -> None:
        """Start background monitoring tasks"""
        if not self.config.monitoring.enabled:
            return
        
        # Health check task
        async def health_check_task():
            while self._is_running:
                try:
                    await self._health_checker.run_checks()
                    await asyncio.sleep(self.config.monitoring.health_check_interval_seconds)
                except Exception as e:
                    logger.error(f"Health check task error: {e}")
                    await asyncio.sleep(5)
        
        # Alert evaluation task
        async def alert_evaluation_task():
            while self._is_running:
                try:
                    metrics = self._metrics_collector.get_metrics()
                    await self._alert_manager.evaluate_rules(metrics)
                    await asyncio.sleep(self.config.monitoring.alert_evaluation_interval_seconds)
                except Exception as e:
                    logger.error(f"Alert evaluation task error: {e}")
                    await asyncio.sleep(5)
        
        # Start tasks
        self._background_tasks.append(asyncio.create_task(health_check_task()))
        self._background_tasks.append(asyncio.create_task(alert_evaluation_task()))
        
        logger.debug("Monitoring tasks started")
    
    # Public API methods
    
    def get_event_bus(self) -> IEventBus:
        """Get the event bus instance"""
        if not self._event_bus:
            raise RuntimeError("Event system not initialized")
        return self._event_bus
    
    def get_event_store(self) -> IEventStore:
        """Get the event store instance"""
        if not self._event_store:
            raise RuntimeError("Event system not initialized")
        return self._event_store
    
    def get_dlq_manager(self) -> IDeadLetterQueueManager:
        """Get the dead letter queue manager"""
        if not self._dlq_manager:
            raise RuntimeError("Event system not initialized")
        return self._dlq_manager
    
    def get_metrics_collector(self) -> Optional[InMemoryMetricsCollector]:
        """Get the metrics collector"""
        return self._metrics_collector
    
    def get_dashboard(self) -> Optional[MonitoringDashboard]:
        """Get the monitoring dashboard"""
        return self._dashboard
    
    def get_projection_manager(self) -> Optional[ProjectionManager]:
        """Get the projection manager"""
        return self._projection_manager
    
    def get_replay_service(self) -> Optional[EventReplayService]:
        """Get the event replay service"""
        return self._replay_service
    
    async def publish_event(self, event: DomainEvent) -> None:
        """Publish an event through the system"""
        if not self._is_running:
            raise RuntimeError("Event system not running")
        
        # Store event if event sourcing is enabled
        if self.config.enable_event_sourcing:
            await self._event_store.append_event(event)
        
        # Publish through event bus
        await self._event_bus.publish(event)
    
    async def register_handler(self, 
                              event_type: str, 
                              handler: IEventHandler,
                              handler_name: Optional[str] = None) -> None:
        """Register an event handler"""
        if not self._event_bus:
            raise RuntimeError("Event system not initialized")
        
        # Create circuit breaker for handler
        if handler_name:
            circuit_breaker_config = CircuitBreakerConfig(
                failure_threshold=self.config.event_bus.default_circuit_breaker.failure_threshold,
                success_threshold=self.config.event_bus.default_circuit_breaker.success_threshold,
                timeout_seconds=self.config.event_bus.default_circuit_breaker.timeout_seconds
            )
            self._circuit_breakers[handler_name] = CircuitBreaker(
                handler_name, 
                circuit_breaker_config
            )
        
        await self._event_bus.subscribe(event_type, handler)
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            'initialized': self._is_initialized,
            'running': self._is_running,
            'config': {
                'environment': self.config.environment,
                'debug': self.config.debug,
                'event_bus_type': self.config.event_bus.type.value,
                'event_store_type': self.config.event_store.type.value,
                'monitoring_enabled': self.config.monitoring.enabled
            }
        }
        
        if self._is_initialized:
            # Event store statistics
            if self._event_store:
                status['event_store'] = await self._event_store.get_statistics()
            
            # Dead letter queue statistics
            if self._dlq_manager:
                status['dlq'] = await self._dlq_manager.get_dlq_statistics()
            
            # Circuit breaker status
            status['circuit_breakers'] = {
                name: cb.get_state_info() 
                for name, cb in self._circuit_breakers.items()
            }
            
            # Projection status
            if self._projection_manager:
                status['projections'] = self._projection_manager.get_projection_status()
            
            # Dashboard data (if monitoring enabled)
            if self._dashboard and self.config.monitoring.enabled:
                status['monitoring'] = await self._dashboard.get_dashboard_data()
        
        return status
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get system health status"""
        if not self._health_checker or not self.config.monitoring.enabled:
            return {
                'overall_healthy': self._is_running,
                'monitoring_enabled': False
            }
        
        return await self._health_checker.run_checks()
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        if not self._metrics_collector or not self.config.monitoring.enabled:
            return {'monitoring_enabled': False}
        
        return {
            'monitoring_enabled': True,
            'total_metrics': len(self._metrics_collector.get_metrics()),
            'event_metrics': {
                'published_total': self._metrics_collector.get_counter_value("events.published.total"),
                'processed_total': self._metrics_collector.get_counter_value("events.processed.total"),
                'errors_total': self._metrics_collector.get_counter_value("events.handler.errors.total"),
                'processing_time_stats': self._metrics_collector.get_histogram_stats("events.processing.duration_ms")
            }
        }


# Global instance management
_global_event_system: Optional[EventSystemManager] = None


def get_event_system() -> EventSystemManager:
    """Get the global event system instance"""
    global _global_event_system
    if _global_event_system is None:
        _global_event_system = EventSystemManager()
    return _global_event_system


def set_event_system(event_system: EventSystemManager) -> None:
    """Set the global event system instance"""
    global _global_event_system
    _global_event_system = event_system


async def initialize_event_system(config: Optional[EventSystemConfig] = None) -> EventSystemManager:
    """Initialize and start the global event system"""
    event_system = EventSystemManager(config)
    await event_system.initialize()
    await event_system.start()
    set_event_system(event_system)
    return event_system


async def shutdown_event_system() -> None:
    """Shutdown the global event system"""
    global _global_event_system
    if _global_event_system:
        await _global_event_system.stop()
        _global_event_system = None


# Convenience functions for common operations
async def publish_event(event: DomainEvent) -> None:
    """Publish an event using the global event system"""
    event_system = get_event_system()
    await event_system.publish_event(event)


async def register_handler(event_type: str, 
                          handler: IEventHandler,
                          handler_name: Optional[str] = None) -> None:
    """Register a handler using the global event system"""
    event_system = get_event_system()
    await event_system.register_handler(event_type, handler, handler_name)