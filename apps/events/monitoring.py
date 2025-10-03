"""
Monitoring and Metrics Infrastructure for Event-Driven Architecture
Provides comprehensive monitoring, metrics collection, and observability
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from .base import DomainEvent, IEventMetrics


logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"           # Monotonically increasing
    GAUGE = "gauge"              # Current value
    HISTOGRAM = "histogram"      # Distribution of values
    TIMER = "timer"              # Duration measurements


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """Single metric measurement"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class Alert:
    """System alert"""
    alert_id: str
    name: str
    description: str
    severity: AlertSeverity
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class IMetricsCollector(ABC):
    """Interface for metrics collection"""
    
    @abstractmethod
    def increment_counter(self, name: str, value: float = 1.0, tags: Dict[str, str] = None):
        """Increment a counter metric"""
        pass
    
    @abstractmethod
    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Set a gauge metric"""
        pass
    
    @abstractmethod
    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a histogram value"""
        pass
    
    @abstractmethod
    def start_timer(self, name: str, tags: Dict[str, str] = None) -> 'Timer':
        """Start a timer"""
        pass
    
    @abstractmethod
    def get_metrics(self) -> List[MetricPoint]:
        """Get all collected metrics"""
        pass


class Timer:
    """Timer context manager for measuring durations"""
    
    def __init__(self, collector: IMetricsCollector, name: str, tags: Dict[str, str] = None):
        self.collector = collector
        self.name = name
        self.tags = tags or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.collector.record_histogram(
                f"{self.name}.duration_seconds",
                duration,
                self.tags
            )


class InMemoryMetricsCollector(IMetricsCollector):
    """In-memory metrics collector"""
    
    def __init__(self, max_points: int = 10000):
        self.max_points = max_points
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._metrics_history: deque = deque(maxlen=max_points)
        self._lock = asyncio.Lock()
    
    def increment_counter(self, name: str, value: float = 1.0, tags: Dict[str, str] = None):
        """Increment a counter metric"""
        key = self._make_key(name, tags)
        self._counters[key] += value
        
        self._record_metric(MetricPoint(
            name=name,
            value=self._counters[key],
            timestamp=datetime.now(),
            tags=tags or {},
            metric_type=MetricType.COUNTER
        ))
    
    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Set a gauge metric"""
        key = self._make_key(name, tags)
        self._gauges[key] = value
        
        self._record_metric(MetricPoint(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
            metric_type=MetricType.GAUGE
        ))
    
    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a histogram value"""
        key = self._make_key(name, tags)
        self._histograms[key].append(value)
        
        self._record_metric(MetricPoint(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
            metric_type=MetricType.HISTOGRAM
        ))
    
    def start_timer(self, name: str, tags: Dict[str, str] = None) -> Timer:
        """Start a timer"""
        return Timer(self, name, tags)
    
    def get_metrics(self) -> List[MetricPoint]:
        """Get all collected metrics"""
        return list(self._metrics_history)
    
    def get_counter_value(self, name: str, tags: Dict[str, str] = None) -> float:
        """Get current counter value"""
        key = self._make_key(name, tags)
        return self._counters.get(key, 0.0)
    
    def get_gauge_value(self, name: str, tags: Dict[str, str] = None) -> Optional[float]:
        """Get current gauge value"""
        key = self._make_key(name, tags)
        return self._gauges.get(key)
    
    def get_histogram_stats(self, name: str, tags: Dict[str, str] = None) -> Dict[str, float]:
        """Get histogram statistics"""
        key = self._make_key(name, tags)
        values = list(self._histograms.get(key, []))
        
        if not values:
            return {}
        
        values.sort()
        count = len(values)
        
        return {
            'count': count,
            'min': values[0],
            'max': values[-1],
            'mean': sum(values) / count,
            'p50': values[int(count * 0.5)],
            'p90': values[int(count * 0.9)],
            'p95': values[int(count * 0.95)],
            'p99': values[int(count * 0.99)]
        }
    
    def _make_key(self, name: str, tags: Dict[str, str] = None) -> str:
        """Create key from name and tags"""
        if not tags:
            return name
        
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"
    
    def _record_metric(self, metric: MetricPoint):
        """Record metric in history"""
        self._metrics_history.append(metric)


class EventMetrics(IEventMetrics):
    """Event-specific metrics implementation"""
    
    def __init__(self, collector: IMetricsCollector):
        self.collector = collector
    
    def record_event_published(self, event_type: str, processing_time_ms: float = 0):
        """Record event publication"""
        self.collector.increment_counter(
            "events.published.total",
            tags={"event_type": event_type}
        )
        
        if processing_time_ms > 0:
            self.collector.record_histogram(
                "events.publish.duration_ms",
                processing_time_ms,
                tags={"event_type": event_type}
            )
    
    def record_event_processed(self, event_type: str, handler_name: str, 
                              processing_time_ms: float, success: bool):
        """Record event processing"""
        status = "success" if success else "failure"
        
        self.collector.increment_counter(
            "events.processed.total",
            tags={
                "event_type": event_type,
                "handler": handler_name,
                "status": status
            }
        )
        
        self.collector.record_histogram(
            "events.processing.duration_ms",
            processing_time_ms,
            tags={
                "event_type": event_type,
                "handler": handler_name
            }
        )
    
    def record_handler_error(self, handler_name: str, error_type: str):
        """Record handler error"""
        self.collector.increment_counter(
            "events.handler.errors.total",
            tags={
                "handler": handler_name,
                "error_type": error_type
            }
        )
    
    def record_retry_attempt(self, event_type: str, handler_name: str, attempt: int):
        """Record retry attempt"""
        self.collector.increment_counter(
            "events.retries.total",
            tags={
                "event_type": event_type,
                "handler": handler_name,
                "attempt": str(attempt)
            }
        )
    
    def record_dlq_message(self, event_type: str, handler_name: str):
        """Record dead letter queue message"""
        self.collector.increment_counter(
            "events.dlq.messages.total",
            tags={
                "event_type": event_type,
                "handler": handler_name
            }
        )
    
    def set_active_handlers(self, count: int):
        """Set number of active handlers"""
        self.collector.set_gauge("events.handlers.active", count)
    
    def set_queue_size(self, queue_name: str, size: int):
        """Set queue size"""
        self.collector.set_gauge(
            "events.queue.size",
            size,
            tags={"queue": queue_name}
        )


class HealthChecker:
    """System health monitoring"""
    
    def __init__(self, collector: IMetricsCollector):
        self.collector = collector
        self._checks: Dict[str, callable] = {}
        self._last_check_results: Dict[str, bool] = {}
    
    def register_check(self, name: str, check_func: callable):
        """Register a health check"""
        self._checks[name] = check_func
    
    async def run_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {}
        overall_healthy = True
        
        for name, check_func in self._checks.items():
            try:
                with self.collector.start_timer("health.check.duration", {"check": name}):
                    is_healthy = await check_func()
                
                results[name] = {
                    "healthy": is_healthy,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Record metric
                self.collector.set_gauge(
                    "health.check.status",
                    1.0 if is_healthy else 0.0,
                    tags={"check": name}
                )
                
                # Track status changes
                previous_status = self._last_check_results.get(name)
                if previous_status is not None and previous_status != is_healthy:
                    self.collector.increment_counter(
                        "health.check.status_changes.total",
                        tags={"check": name, "new_status": "healthy" if is_healthy else "unhealthy"}
                    )
                
                self._last_check_results[name] = is_healthy
                
                if not is_healthy:
                    overall_healthy = False
                    
            except Exception as e:
                logger.error(f"Health check {name} failed: {e}")
                results[name] = {
                    "healthy": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                overall_healthy = False
                
                self.collector.increment_counter(
                    "health.check.errors.total",
                    tags={"check": name}
                )
        
        # Overall health status
        self.collector.set_gauge("health.overall.status", 1.0 if overall_healthy else 0.0)
        
        return {
            "overall_healthy": overall_healthy,
            "checks": results,
            "timestamp": datetime.now().isoformat()
        }


class AlertManager:
    """Alert management system"""
    
    def __init__(self, collector: IMetricsCollector):
        self.collector = collector
        self._alerts: Dict[str, Alert] = {}
        self._rules: List[Dict[str, Any]] = []
        self._notification_handlers: List[callable] = []
    
    def add_alert_rule(self, 
                      name: str,
                      condition: callable,
                      severity: AlertSeverity,
                      description: str,
                      tags: Dict[str, str] = None):
        """Add an alert rule"""
        self._rules.append({
            'name': name,
            'condition': condition,
            'severity': severity,
            'description': description,
            'tags': tags or {}
        })
    
    def add_notification_handler(self, handler: callable):
        """Add notification handler"""
        self._notification_handlers.append(handler)
    
    async def evaluate_rules(self, metrics: List[MetricPoint]):
        """Evaluate alert rules against current metrics"""
        for rule in self._rules:
            try:
                should_alert = await rule['condition'](metrics)
                
                if should_alert:
                    await self._trigger_alert(rule)
                else:
                    await self._resolve_alert(rule['name'])
                    
            except Exception as e:
                logger.error(f"Error evaluating alert rule {rule['name']}: {e}")
    
    async def _trigger_alert(self, rule: Dict[str, Any]):
        """Trigger an alert"""
        alert_id = rule['name']
        
        # Check if alert already exists
        if alert_id in self._alerts and not self._alerts[alert_id].resolved:
            return  # Alert already active
        
        alert = Alert(
            alert_id=alert_id,
            name=rule['name'],
            description=rule['description'],
            severity=rule['severity'],
            timestamp=datetime.now(),
            tags=rule['tags']
        )
        
        self._alerts[alert_id] = alert
        
        # Record metric
        self.collector.increment_counter(
            "alerts.triggered.total",
            tags={
                "alert": alert.name,
                "severity": alert.severity.value
            }
        )
        
        # Send notifications
        for handler in self._notification_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Error sending alert notification: {e}")
        
        logger.warning(f"Alert triggered: {alert.name} - {alert.description}")
    
    async def _resolve_alert(self, alert_id: str):
        """Resolve an alert"""
        if alert_id in self._alerts and not self._alerts[alert_id].resolved:
            alert = self._alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.now()
            
            # Record metric
            self.collector.increment_counter(
                "alerts.resolved.total",
                tags={
                    "alert": alert.name,
                    "severity": alert.severity.value
                }
            )
            
            logger.info(f"Alert resolved: {alert.name}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return [alert for alert in self._alerts.values() if not alert.resolved]
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history"""
        alerts = list(self._alerts.values())
        alerts.sort(key=lambda a: a.timestamp, reverse=True)
        return alerts[:limit]


class MonitoringDashboard:
    """Simple monitoring dashboard data provider"""
    
    def __init__(self, 
                 collector: IMetricsCollector,
                 health_checker: HealthChecker,
                 alert_manager: AlertManager):
        self.collector = collector
        self.health_checker = health_checker
        self.alert_manager = alert_manager
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        # Get health status
        health_status = await self.health_checker.run_checks()
        
        # Get active alerts
        active_alerts = self.alert_manager.get_active_alerts()
        
        # Get key metrics
        event_metrics = self._get_event_metrics()
        system_metrics = self._get_system_metrics()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'health': health_status,
            'alerts': {
                'active_count': len(active_alerts),
                'active_alerts': [
                    {
                        'name': alert.name,
                        'severity': alert.severity.value,
                        'description': alert.description,
                        'timestamp': alert.timestamp.isoformat()
                    }
                    for alert in active_alerts
                ]
            },
            'events': event_metrics,
            'system': system_metrics
        }
    
    def _get_event_metrics(self) -> Dict[str, Any]:
        """Get event-related metrics"""
        return {
            'published_total': self.collector.get_counter_value("events.published.total"),
            'processed_total': self.collector.get_counter_value("events.processed.total"),
            'errors_total': self.collector.get_counter_value("events.handler.errors.total"),
            'retries_total': self.collector.get_counter_value("events.retries.total"),
            'dlq_messages_total': self.collector.get_counter_value("events.dlq.messages.total"),
            'active_handlers': self.collector.get_gauge_value("events.handlers.active"),
            'processing_time_stats': self.collector.get_histogram_stats("events.processing.duration_ms")
        }
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system-related metrics"""
        return {
            'overall_health': self.collector.get_gauge_value("health.overall.status"),
            'health_check_errors': self.collector.get_counter_value("health.check.errors.total"),
            'alerts_triggered': self.collector.get_counter_value("alerts.triggered.total"),
            'alerts_resolved': self.collector.get_counter_value("alerts.resolved.total")
        }


# Example alert conditions
async def high_error_rate_condition(metrics: List[MetricPoint]) -> bool:
    """Alert condition for high error rate"""
    # Get recent error metrics
    recent_errors = [
        m for m in metrics 
        if m.name == "events.handler.errors.total" 
        and m.timestamp > datetime.now() - timedelta(minutes=5)
    ]
    
    if len(recent_errors) > 10:  # More than 10 errors in 5 minutes
        return True
    
    return False


async def queue_size_condition(metrics: List[MetricPoint]) -> bool:
    """Alert condition for large queue size"""
    # Get latest queue size metrics
    queue_metrics = [
        m for m in metrics 
        if m.name == "events.queue.size"
        and m.timestamp > datetime.now() - timedelta(minutes=1)
    ]
    
    for metric in queue_metrics:
        if metric.value > 1000:  # Queue size > 1000
            return True
    
    return False