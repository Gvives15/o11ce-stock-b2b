"""
Event Bus Centralizado - Punto de entrada principal para el sistema de eventos
Este módulo actúa como la interfaz principal para toda la comunicación event-driven en BFF
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Type
from uuid import UUID

# Importar toda la infraestructura de eventos
from apps.events import (
    # Core components
    DomainEvent,
    IEventHandler,
    IEventBus,
    
    # Event system management
    EventSystemManager,
    get_event_system,
    initialize_event_system,
    shutdown_event_system,
    
    # Configuration
    EventSystemConfig,
    get_development_config,
    get_production_config,
    
    # Utilities
    event_handler,
    publish_event,
    publish_domain_event,
    create_event_id,
    create_correlation_id,
    get_handler_registry,
    register_all_handlers,
    
    # Error handling
    ErrorType,
    CircuitBreaker,
    
    # Monitoring
    EventMetrics,
    HealthChecker
)

logger = logging.getLogger(__name__)

# Global event system instance
_event_system: Optional[EventSystemManager] = None


class EventBus:
    """
    Facade centralizado para el Event Bus
    Proporciona una interfaz simplificada para publicar y manejar eventos
    """
    
    @staticmethod
    async def initialize(config: Optional[EventSystemConfig] = None) -> None:
        """Inicializar el sistema de eventos"""
        global _event_system
        
        if _event_system is not None:
            logger.warning("Event system already initialized")
            return
            
        try:
            _event_system = await initialize_event_system(config)
            logger.info("Event system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize event system: {e}")
            raise
    
    @staticmethod
    async def shutdown() -> None:
        """Cerrar el sistema de eventos"""
        global _event_system
        
        if _event_system is None:
            return
            
        try:
            await shutdown_event_system()
            _event_system = None
            logger.info("Event system shutdown successfully")
        except Exception as e:
            logger.error(f"Failed to shutdown event system: {e}")
            raise
    
    @staticmethod
    async def publish(event: DomainEvent) -> None:
        """Publicar un evento de dominio"""
        if _event_system is None:
            raise RuntimeError("Event system not initialized. Call EventBus.initialize() first")
        
        try:
            await _event_system.publish_event(event)
            logger.debug(f"Published event: {event.event_type} for {event.aggregate_type}:{event.aggregate_id}")
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_type}: {e}")
            raise
    
    @staticmethod
    async def publish_domain_event(
        event_type: str,
        aggregate_id: str,
        aggregate_type: str,
        data: Dict[str, Any],
        correlation_id: Optional[UUID] = None,
        causation_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Publicar un evento de dominio con datos específicos"""
        await publish_domain_event(
            event_type=event_type,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            data=data,
            correlation_id=correlation_id,
            causation_id=causation_id,
            metadata=metadata or {}
        )
    
    @staticmethod
    def register_handler(event_type: str):
        """Decorador para registrar handlers de eventos"""
        return event_handler(event_type)
    
    @staticmethod
    async def register_all_handlers() -> None:
        """Registrar todos los handlers recolectados"""
        await register_all_handlers()
    
    @staticmethod
    def get_system() -> EventSystemManager:
        """Obtener la instancia del sistema de eventos"""
        if _event_system is None:
            raise RuntimeError("Event system not initialized")
        return _event_system
    
    @staticmethod
    def is_initialized() -> bool:
        """Verificar si el sistema está inicializado"""
        return _event_system is not None


# Funciones de conveniencia para uso directo
async def publish_stock_event(
    event_type: str,
    product_id: str,
    data: Dict[str, Any],
    correlation_id: Optional[UUID] = None
) -> None:
    """Publicar evento específico del dominio Stock"""
    await EventBus.publish_domain_event(
        event_type=f"stock.{event_type}",
        aggregate_id=product_id,
        aggregate_type="Product",
        data=data,
        correlation_id=correlation_id
    )


def publish_pos_event(event: DomainEvent) -> str:
    """
    Publicar un evento del dominio POS desde un contexto síncrono.
    Acepta una instancia de DomainEvent y retorna el ID del evento publicado como str.
    """
    # Asegurar inicialización del sistema de eventos
    if not EventBus.is_initialized():
        try:
            asyncio.run(EventBus.initialize(get_development_config()))
        except Exception as e:
            logger.error(f"Failed to initialize event system for POS publish: {e}")
            # Si no se inicializa, el publish más abajo levantará error
    
    # Publicar el evento de manera síncrona
    try:
        asyncio.run(EventBus.publish(event))
        return str(event.event_id)
    except Exception as e:
        logger.error(f"Failed to publish POS event {event.event_type}: {e}")
        raise


async def publish_order_event(
    event_type: str,
    order_id: str,
    data: Dict[str, Any],
    correlation_id: Optional[UUID] = None
) -> None:
    """Publicar evento específico del dominio Orders"""
    await EventBus.publish_domain_event(
        event_type=f"order.{event_type}",
        aggregate_id=order_id,
        aggregate_type="Order",
        data=data,
        correlation_id=correlation_id
    )


# Aliases para compatibilidad
initialize_event_bus = EventBus.initialize
shutdown_event_bus = EventBus.shutdown
publish_event_async = EventBus.publish
register_event_handler = EventBus.register_handler

# Exportar la interfaz pública
__all__ = [
    # Main EventBus class
    'EventBus',
    
    # Core types
    'DomainEvent',
    'IEventHandler',
    'EventSystemConfig',
    
    # Configuration functions
    'get_development_config',
    'get_production_config',
    
    # Domain-specific publishers
    'publish_stock_event',
    'publish_pos_event',
    'publish_order_event',
    
    # Compatibility aliases
    'initialize_event_bus',
    'shutdown_event_bus',
    'publish_event_async',
    'register_event_handler',
    
    # Utilities
    'create_event_id',
    'create_correlation_id',
]