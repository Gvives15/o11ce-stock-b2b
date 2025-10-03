"""
Configuration Management for Event-Driven Architecture
Provides centralized configuration for all event system components
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class EventBusType(Enum):
    """Types of event bus implementations"""
    IN_MEMORY = "in_memory"
    REDIS = "redis"
    RABBITMQ = "rabbitmq"
    KAFKA = "kafka"


class EventStoreType(Enum):
    """Types of event store implementations"""
    IN_MEMORY = "in_memory"
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"
    ELASTICSEARCH = "elasticsearch"


class SerializationFormat(Enum):
    """Event serialization formats"""
    JSON = "json"
    AVRO = "avro"
    PROTOBUF = "protobuf"


@dataclass
class RetryPolicyConfig:
    """Configuration for retry policies"""
    max_attempts: int = 3
    initial_delay_ms: int = 1000
    max_delay_ms: int = 30000
    backoff_multiplier: float = 2.0
    jitter: bool = True


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breakers"""
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_seconds: int = 60
    monitoring_window_seconds: int = 300


@dataclass
class EventBusConfig:
    """Configuration for event bus"""
    type: EventBusType = EventBusType.IN_MEMORY
    max_concurrent_handlers: int = 10
    default_timeout_seconds: int = 30
    enable_metrics: bool = True
    enable_tracing: bool = True
    
    # Queue configuration
    max_queue_size: int = 10000
    batch_size: int = 100
    batch_timeout_ms: int = 1000
    
    # Retry configuration
    default_retry_policy: RetryPolicyConfig = field(default_factory=RetryPolicyConfig)
    
    # Circuit breaker configuration
    default_circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    
    # Connection settings (for external buses)
    connection_string: Optional[str] = None
    connection_pool_size: int = 10
    connection_timeout_seconds: int = 30


@dataclass
class EventStoreConfig:
    """Configuration for event store"""
    type: EventStoreType = EventStoreType.IN_MEMORY
    connection_string: Optional[str] = None
    
    # Performance settings
    batch_size: int = 100
    connection_pool_size: int = 5
    query_timeout_seconds: int = 30
    
    # Retention settings
    enable_retention: bool = False
    retention_days: int = 365
    cleanup_interval_hours: int = 24
    
    # Snapshot settings
    enable_snapshots: bool = False
    snapshot_frequency: int = 100  # Every N events
    
    # Indexing
    enable_indexing: bool = True
    index_by_aggregate: bool = True
    index_by_event_type: bool = True
    index_by_timestamp: bool = True


@dataclass
class SerializationConfig:
    """Configuration for event serialization"""
    format: SerializationFormat = SerializationFormat.JSON
    compress: bool = False
    encryption_enabled: bool = False
    encryption_key: Optional[str] = None
    
    # Schema registry (for Avro/Protobuf)
    schema_registry_url: Optional[str] = None
    schema_registry_auth: Optional[Dict[str, str]] = None


@dataclass
class MonitoringConfig:
    """Configuration for monitoring and metrics"""
    enabled: bool = True
    
    # Metrics collection
    metrics_interval_seconds: int = 60
    max_metric_points: int = 10000
    
    # Health checks
    health_check_interval_seconds: int = 30
    health_check_timeout_seconds: int = 10
    
    # Alerting
    enable_alerting: bool = True
    alert_evaluation_interval_seconds: int = 60
    
    # Logging
    log_level: str = "INFO"
    log_events: bool = False  # Log all events (can be verbose)
    log_handler_execution: bool = True
    log_errors: bool = True


@dataclass
class SecurityConfig:
    """Configuration for security features"""
    enable_authentication: bool = False
    enable_authorization: bool = False
    
    # Event encryption
    encrypt_events: bool = False
    encryption_algorithm: str = "AES-256-GCM"
    key_rotation_days: int = 90
    
    # Access control
    require_handler_permissions: bool = False
    default_permissions: List[str] = field(default_factory=list)
    
    # Audit logging
    enable_audit_log: bool = False
    audit_log_events: List[str] = field(default_factory=list)


@dataclass
class PerformanceConfig:
    """Configuration for performance optimization"""
    # Threading and concurrency
    max_worker_threads: int = 10
    thread_pool_size: int = 5
    
    # Batching
    enable_batching: bool = True
    batch_size: int = 100
    batch_timeout_ms: int = 1000
    
    # Caching
    enable_handler_caching: bool = True
    cache_size: int = 1000
    cache_ttl_seconds: int = 300
    
    # Connection pooling
    connection_pool_size: int = 10
    connection_pool_timeout_seconds: int = 30
    
    # Memory management
    max_memory_usage_mb: int = 512
    gc_threshold_mb: int = 256


@dataclass
class EventSystemConfig:
    """Main configuration for the entire event system"""
    # Core components
    event_bus: EventBusConfig = field(default_factory=EventBusConfig)
    event_store: EventStoreConfig = field(default_factory=EventStoreConfig)
    serialization: SerializationConfig = field(default_factory=SerializationConfig)
    
    # Cross-cutting concerns
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    
    # Environment
    environment: str = "development"
    debug: bool = False
    
    # Feature flags
    enable_event_sourcing: bool = True
    enable_projections: bool = True
    enable_sagas: bool = True
    enable_dead_letter_queue: bool = True


def load_config_from_env() -> EventSystemConfig:
        """
        Load configuration from environment variables
        
        Returns:
            EventSystemConfig: Configuration loaded from environment
        """
        config = EventSystemConfig()
        
        # Environment
        config.environment = os.getenv("EVENT_SYSTEM_ENV", "development")
        config.debug = os.getenv("EVENT_SYSTEM_DEBUG", "false").lower() == "true"
        
        # Event Bus Configuration
        event_bus_type = os.getenv("EVENT_BUS_TYPE", "in_memory")
        try:
            config.event_bus.type = EventBusType(event_bus_type)
        except ValueError:
            config.event_bus.type = EventBusType.IN_MEMORY
        
        config.event_bus.connection_string = os.getenv("EVENT_BUS_CONNECTION_STRING", "")
        config.event_bus.default_timeout_seconds = int(os.getenv("EVENT_BUS_TIMEOUT", "30"))
        
        # Event Store Configuration
        event_store_type = os.getenv("EVENT_STORE_TYPE", "in_memory")
        try:
            config.event_store.type = EventStoreType(event_store_type)
        except ValueError:
            config.event_store.type = EventStoreType.IN_MEMORY
        
        config.event_store.connection_string = os.getenv("EVENT_STORE_CONNECTION_STRING", "")
        config.event_store.enable_retention = os.getenv("EVENT_STORE_RETENTION", "false").lower() == "true"
        config.event_store.retention_days = int(os.getenv("EVENT_STORE_RETENTION_DAYS", "90"))
        
        # Monitoring Configuration
        config.monitoring.enabled = os.getenv("EVENT_MONITORING_ENABLED", "true").lower() == "true"
        config.monitoring.log_level = os.getenv("EVENT_LOG_LEVEL", "INFO")
        config.monitoring.metrics_enabled = os.getenv("EVENT_METRICS_ENABLED", "true").lower() == "true"
        
        # Security Configuration
        config.security.enable_authentication = os.getenv("EVENT_AUTH_ENABLED", "false").lower() == "true"
        config.security.encrypt_events = os.getenv("EVENT_ENCRYPTION_ENABLED", "false").lower() == "true"
        config.security.enable_audit_log = os.getenv("EVENT_AUDIT_LOG_ENABLED", "false").lower() == "true"
        
        # Performance Configuration
        config.performance.max_worker_threads = int(os.getenv("EVENT_MAX_WORKERS", "5"))
        config.performance.batch_size = int(os.getenv("EVENT_BATCH_SIZE", "10"))
        config.performance.enable_batching = os.getenv("EVENT_BATCHING_ENABLED", "false").lower() == "true"
        
        return config


def load_config_from_dict(config_dict: dict) -> EventSystemConfig:
    """
    Load configuration from a dictionary
    
    Args:
        config_dict: Dictionary containing configuration values
        
    Returns:
        EventSystemConfig: Configuration loaded from dictionary
    """
    config = EventSystemConfig()
    
    # Event Bus configuration
    if 'event_bus' in config_dict:
        bus_config = config_dict['event_bus']
        config.event_bus.backend = bus_config.get('backend', config.event_bus.backend)
        config.event_bus.max_retries = bus_config.get('max_retries', config.event_bus.max_retries)
        config.event_bus.retry_delay_seconds = bus_config.get('retry_delay_seconds', config.event_bus.retry_delay_seconds)
        config.event_bus.enable_dead_letter_queue = bus_config.get('enable_dead_letter_queue', config.event_bus.enable_dead_letter_queue)
    
    # Event Store configuration
    if 'event_store' in config_dict:
        store_config = config_dict['event_store']
        config.event_store.backend = store_config.get('backend', config.event_store.backend)
        config.event_store.connection_string = store_config.get('connection_string', config.event_store.connection_string)
        config.event_store.table_name = store_config.get('table_name', config.event_store.table_name)
        config.event_store.enable_snapshots = store_config.get('enable_snapshots', config.event_store.enable_snapshots)
        config.event_store.snapshot_frequency = store_config.get('snapshot_frequency', config.event_store.snapshot_frequency)
    
    # Monitoring configuration
    if 'monitoring' in config_dict:
        monitoring_config = config_dict['monitoring']
        config.monitoring.enable_metrics = monitoring_config.get('enable_metrics', config.monitoring.enable_metrics)
        config.monitoring.enable_tracing = monitoring_config.get('enable_tracing', config.monitoring.enable_tracing)
        config.monitoring.enable_logging = monitoring_config.get('enable_logging', config.monitoring.enable_logging)
        config.monitoring.log_level = monitoring_config.get('log_level', config.monitoring.log_level)
        config.monitoring.metrics_backend = monitoring_config.get('metrics_backend', config.monitoring.metrics_backend)
    
    # Security configuration
    if 'security' in config_dict:
        security_config = config_dict['security']
        config.security.enable_encryption = security_config.get('enable_encryption', config.security.enable_encryption)
        config.security.encryption_key = security_config.get('encryption_key', config.security.encryption_key)
        config.security.enable_authentication = security_config.get('enable_authentication', config.security.enable_authentication)
        config.security.enable_authorization = security_config.get('enable_authorization', config.security.enable_authorization)
    
    # Performance configuration
    if 'performance' in config_dict:
        performance_config = config_dict['performance']
        config.performance.batch_size = performance_config.get('batch_size', config.performance.batch_size)
        config.performance.enable_batching = performance_config.get('enable_batching', config.performance.enable_batching)
    
    # Environment and feature flags
    config.environment = config_dict.get('environment', config.environment)
    config.debug = config_dict.get('debug', config.debug)
    config.enable_event_sourcing = config_dict.get('enable_event_sourcing', config.enable_event_sourcing)
    config.enable_projections = config_dict.get('enable_projections', config.enable_projections)
    config.enable_sagas = config_dict.get('enable_sagas', config.enable_sagas)
    config.enable_dead_letter_queue = config_dict.get('enable_dead_letter_queue', config.enable_dead_letter_queue)
    
    return config


@dataclass
class EventSystemConfig:
    """Main configuration for the entire event system"""
    # Core components
    event_bus: EventBusConfig = field(default_factory=EventBusConfig)
    event_store: EventStoreConfig = field(default_factory=EventStoreConfig)
    serialization: SerializationConfig = field(default_factory=SerializationConfig)
    
    # Cross-cutting concerns
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    
    # Environment
    environment: str = "development"
    debug: bool = False
    
    # Feature flags
    enable_event_sourcing: bool = True
    enable_projections: bool = True
    enable_sagas: bool = True
    enable_dead_letter_queue: bool = True

    @classmethod
    def from_environment(cls) -> 'EventSystemConfig':
        """Create configuration from environment variables"""
        config = cls()
        
        # Event Bus configuration
        config.event_bus.type = EventBusType(
            os.getenv('EVENT_BUS_TYPE', 'in_memory')
        )
        config.event_bus.connection_string = os.getenv('EVENT_BUS_CONNECTION_STRING')
        config.event_bus.max_concurrent_handlers = int(
            os.getenv('EVENT_BUS_MAX_HANDLERS', '10')
        )
        
        # Event Store configuration
        config.event_store.type = EventStoreType(
            os.getenv('EVENT_STORE_TYPE', 'in_memory')
        )
        config.event_store.connection_string = os.getenv('EVENT_STORE_CONNECTION_STRING')
        
        # Monitoring configuration
        config.monitoring.enabled = os.getenv('MONITORING_ENABLED', 'true').lower() == 'true'
        config.monitoring.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # Security configuration
        config.security.enable_authentication = (
            os.getenv('SECURITY_AUTH_ENABLED', 'false').lower() == 'true'
        )
        config.security.encrypt_events = (
            os.getenv('SECURITY_ENCRYPT_EVENTS', 'false').lower() == 'true'
        )
        
        # Environment settings
        config.environment = os.getenv('ENVIRONMENT', 'development')
        config.debug = os.getenv('DEBUG', 'false').lower() == 'true'
        
        return config
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventSystemConfig':
        """Create configuration from dictionary"""
        config = cls()
        
        # Event Bus
        if 'event_bus' in data:
            bus_config = data['event_bus']
            config.event_bus.type = EventBusType(bus_config.get('type', 'in_memory'))
            config.event_bus.max_concurrent_handlers = bus_config.get('max_concurrent_handlers', 10)
            config.event_bus.connection_string = bus_config.get('connection_string')
            
            if 'retry_policy' in bus_config:
                retry_config = bus_config['retry_policy']
                config.event_bus.default_retry_policy = RetryPolicyConfig(
                    max_attempts=retry_config.get('max_attempts', 3),
                    initial_delay_ms=retry_config.get('initial_delay_ms', 1000),
                    max_delay_ms=retry_config.get('max_delay_ms', 30000),
                    backoff_multiplier=retry_config.get('backoff_multiplier', 2.0),
                    jitter=retry_config.get('jitter', True)
                )
        
        # Event Store
        if 'event_store' in data:
            store_config = data['event_store']
            config.event_store.type = EventStoreType(store_config.get('type', 'in_memory'))
            config.event_store.connection_string = store_config.get('connection_string')
            config.event_store.batch_size = store_config.get('batch_size', 100)
            config.event_store.enable_retention = store_config.get('enable_retention', False)
            config.event_store.retention_days = store_config.get('retention_days', 365)
        
        # Monitoring
        if 'monitoring' in data:
            mon_config = data['monitoring']
            config.monitoring.enabled = mon_config.get('enabled', True)
            config.monitoring.metrics_interval_seconds = mon_config.get('metrics_interval_seconds', 60)
            config.monitoring.log_level = mon_config.get('log_level', 'INFO')
            config.monitoring.enable_alerting = mon_config.get('enable_alerting', True)
        
        # Security
        if 'security' in data:
            sec_config = data['security']
            config.security.enable_authentication = sec_config.get('enable_authentication', False)
            config.security.encrypt_events = sec_config.get('encrypt_events', False)
            config.security.enable_audit_log = sec_config.get('enable_audit_log', False)
        
        # Performance
        if 'performance' in data:
            perf_config = data['performance']
            config.performance.max_worker_threads = perf_config.get('max_worker_threads', 10)
            config.performance.enable_batching = perf_config.get('enable_batching', True)
            config.performance.batch_size = perf_config.get('batch_size', 100)
        
        # Environment
        config.environment = data.get('environment', 'development')
        config.debug = data.get('debug', False)
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'event_bus': {
                'type': self.event_bus.type.value,
                'max_concurrent_handlers': self.event_bus.max_concurrent_handlers,
                'default_timeout_seconds': self.event_bus.default_timeout_seconds,
                'connection_string': self.event_bus.connection_string,
                'retry_policy': {
                    'max_attempts': self.event_bus.default_retry_policy.max_attempts,
                    'initial_delay_ms': self.event_bus.default_retry_policy.initial_delay_ms,
                    'max_delay_ms': self.event_bus.default_retry_policy.max_delay_ms,
                    'backoff_multiplier': self.event_bus.default_retry_policy.backoff_multiplier,
                    'jitter': self.event_bus.default_retry_policy.jitter
                }
            },
            'event_store': {
                'type': self.event_store.type.value,
                'connection_string': self.event_store.connection_string,
                'batch_size': self.event_store.batch_size,
                'enable_retention': self.event_store.enable_retention,
                'retention_days': self.event_store.retention_days
            },
            'monitoring': {
                'enabled': self.monitoring.enabled,
                'metrics_interval_seconds': self.monitoring.metrics_interval_seconds,
                'log_level': self.monitoring.log_level,
                'enable_alerting': self.monitoring.enable_alerting
            },
            'security': {
                'enable_authentication': self.security.enable_authentication,
                'encrypt_events': self.security.encrypt_events,
                'enable_audit_log': self.security.enable_audit_log
            },
            'performance': {
                'max_worker_threads': self.performance.max_worker_threads,
                'enable_batching': self.performance.enable_batching,
                'batch_size': self.performance.batch_size
            },
            'environment': self.environment,
            'debug': self.debug
        }
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Validate event bus configuration
        if self.event_bus.max_concurrent_handlers <= 0:
            errors.append("Event bus max_concurrent_handlers must be positive")
        
        if self.event_bus.default_timeout_seconds <= 0:
            errors.append("Event bus default_timeout_seconds must be positive")
        
        # Validate retry policy
        retry = self.event_bus.default_retry_policy
        if retry.max_attempts <= 0:
            errors.append("Retry policy max_attempts must be positive")
        
        if retry.initial_delay_ms <= 0:
            errors.append("Retry policy initial_delay_ms must be positive")
        
        if retry.max_delay_ms < retry.initial_delay_ms:
            errors.append("Retry policy max_delay_ms must be >= initial_delay_ms")
        
        # Validate event store configuration
        if self.event_store.batch_size <= 0:
            errors.append("Event store batch_size must be positive")
        
        if self.event_store.enable_retention and self.event_store.retention_days <= 0:
            errors.append("Event store retention_days must be positive when retention is enabled")
        
        # Validate monitoring configuration
        if self.monitoring.metrics_interval_seconds <= 0:
            errors.append("Monitoring metrics_interval_seconds must be positive")
        
        # Validate performance configuration
        if self.performance.max_worker_threads <= 0:
            errors.append("Performance max_worker_threads must be positive")
        
        if self.performance.batch_size <= 0:
            errors.append("Performance batch_size must be positive")
        
        return errors
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() in ['production', 'prod']
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment.lower() in ['development', 'dev', 'local']


# Default configurations for different environments
def get_development_config() -> EventSystemConfig:
    """Get configuration optimized for development"""
    config = EventSystemConfig()
    config.environment = "development"
    config.debug = True
    
    # Use in-memory implementations for simplicity
    config.event_bus.type = EventBusType.IN_MEMORY
    config.event_store.type = EventStoreType.IN_MEMORY
    
    # Enable all monitoring for debugging
    config.monitoring.enabled = True
    config.monitoring.log_events = True
    config.monitoring.log_handler_execution = True
    config.monitoring.log_level = "DEBUG"
    
    # Disable security for easier development
    config.security.enable_authentication = False
    config.security.encrypt_events = False
    
    # Lower performance settings for development
    config.performance.max_worker_threads = 5
    config.performance.batch_size = 10
    
    return config


def get_production_config() -> EventSystemConfig:
    """Get configuration optimized for production"""
    config = EventSystemConfig()
    config.environment = "production"
    config.debug = False
    
    # Use external implementations for scalability
    config.event_bus.type = EventBusType.REDIS
    config.event_store.type = EventStoreType.POSTGRESQL
    
    # Enable monitoring but reduce verbosity
    config.monitoring.enabled = True
    config.monitoring.log_events = False
    config.monitoring.log_level = "INFO"
    config.monitoring.enable_alerting = True
    
    # Enable security features
    config.security.enable_authentication = True
    config.security.encrypt_events = True
    config.security.enable_audit_log = True
    
    # Higher performance settings
    config.performance.max_worker_threads = 20
    config.performance.batch_size = 100
    config.performance.enable_batching = True
    
    # Enable retention and cleanup
    config.event_store.enable_retention = True
    config.event_store.retention_days = 365
    
    return config


def get_test_config() -> EventSystemConfig:
    """Get configuration optimized for testing"""
    config = EventSystemConfig()
    config.environment = "test"
    config.debug = False
    
    # Use in-memory for fast tests
    config.event_bus.type = EventBusType.IN_MEMORY
    config.event_store.type = EventStoreType.IN_MEMORY
    
    # Minimal monitoring for tests
    config.monitoring.enabled = False
    config.monitoring.log_level = "ERROR"
    
    # Disable security for simpler tests
    config.security.enable_authentication = False
    config.security.encrypt_events = False
    
    # Fast processing for tests
    config.performance.max_worker_threads = 2
    config.performance.batch_size = 5
    config.event_bus.default_timeout_seconds = 5
    
    # Disable retention for tests
    config.event_store.enable_retention = False
    
    return config