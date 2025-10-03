"""
Event Bus Implementation
Central component for event-driven communication with retry, circuit breaker, and monitoring
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from uuid import uuid4
import json

from .base import (
    DomainEvent, EventEnvelope, EventPriority, HandlerResult,
    IEventBus, IEventHandler, IEventMetrics, RetryPolicy
)
from .error_handling import CircuitBreaker, CircuitBreakerConfig, ErrorType


logger = logging.getLogger(__name__)


class InMemoryEventBus(IEventBus):
    """
    In-memory implementation of Event Bus
    Suitable for development and testing, can be extended for production
    """
    
    def __init__(self, 
                 metrics: Optional[IEventMetrics] = None,
                 max_queue_size: int = 10000,
                 processing_batch_size: int = 100,
                 processing_interval_seconds: float = 0.1):
        
        self.metrics = metrics
        self.max_queue_size = max_queue_size
        self.processing_batch_size = processing_batch_size
        self.processing_interval_seconds = processing_interval_seconds
        
        # Handler management
        self._handlers: Dict[str, List[IEventHandler]] = defaultdict(list)
        self._handler_circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Event queues by priority
        self._event_queues: Dict[EventPriority, asyncio.Queue] = {
            EventPriority.CRITICAL: asyncio.Queue(maxsize=max_queue_size),
            EventPriority.HIGH: asyncio.Queue(maxsize=max_queue_size),
            EventPriority.NORMAL: asyncio.Queue(maxsize=max_queue_size),
            EventPriority.LOW: asyncio.Queue(maxsize=max_queue_size)
        }
        
        # Retry queue for failed events
        self._retry_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        
        # Processing control
        self._running = False
        self._processing_tasks: List[asyncio.Task] = []
        
        # Statistics
        self._stats = {
            'events_published': 0,
            'events_processed': 0,
            'events_failed': 0,
            'handlers_registered': 0,
            'circuit_breakers_open': 0
        }
    
    async def publish(self, event: DomainEvent, 
                     priority: EventPriority = EventPriority.NORMAL) -> None:
        """Publish a single event"""
        if not self._running:
            raise RuntimeError("Event bus is not running")
        
        envelope = EventEnvelope(
            event=event,
            priority=priority,
            trace_id=str(uuid4())
        )
        
        try:
            # Add to appropriate priority queue
            await self._event_queues[priority].put(envelope)
            self._stats['events_published'] += 1
            
            if self.metrics:
                self.metrics.record_event_published(
                    event.event_type, 
                    0  # Publishing time is negligible for in-memory
                )
            
            logger.debug(f"Published event {event.event_type} with ID {event.event_id}")
            
        except asyncio.QueueFull:
            logger.error(f"Event queue full for priority {priority.value}")
            raise RuntimeError(f"Event queue full for priority {priority.value}")
    
    async def publish_batch(self, events: List[DomainEvent],
                          priority: EventPriority = EventPriority.NORMAL) -> None:
        """Publish multiple events"""
        for event in events:
            await self.publish(event, priority)
    
    async def subscribe(self, handler: IEventHandler) -> None:
        """Subscribe a handler to events"""
        for event_type in handler.handled_events:
            self._handlers[event_type].append(handler)
            
            # Create circuit breaker for handler
            if handler.handler_name not in self._handler_circuit_breakers:
                config = CircuitBreakerConfig(
                    failure_threshold=5,
                    success_threshold=3,
                    timeout_seconds=60
                )
                self._handler_circuit_breakers[handler.handler_name] = CircuitBreaker(
                    handler.handler_name, config
                )
        
        self._stats['handlers_registered'] += 1
        logger.info(f"Subscribed handler {handler.handler_name} to events: {handler.handled_events}")
    
    async def unsubscribe(self, handler: IEventHandler) -> None:
        """Unsubscribe a handler"""
        for event_type in handler.handled_events:
            if handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)
        
        # Remove circuit breaker
        if handler.handler_name in self._handler_circuit_breakers:
            del self._handler_circuit_breakers[handler.handler_name]
        
        self._stats['handlers_registered'] -= 1
        logger.info(f"Unsubscribed handler {handler.handler_name}")
    
    async def start(self) -> None:
        """Start the event bus"""
        if self._running:
            return
        
        self._running = True
        
        # Start processing tasks for each priority level
        for priority in EventPriority:
            task = asyncio.create_task(
                self._process_events_for_priority(priority),
                name=f"event_processor_{priority.value}"
            )
            self._processing_tasks.append(task)
        
        # Start retry processor
        retry_task = asyncio.create_task(
            self._process_retry_queue(),
            name="retry_processor"
        )
        self._processing_tasks.append(retry_task)
        
        logger.info("Event bus started")
    
    async def stop(self) -> None:
        """Stop the event bus"""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel all processing tasks
        for task in self._processing_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._processing_tasks:
            await asyncio.gather(*self._processing_tasks, return_exceptions=True)
        
        self._processing_tasks.clear()
        logger.info("Event bus stopped")
    
    async def _process_events_for_priority(self, priority: EventPriority) -> None:
        """Process events for a specific priority level"""
        queue = self._event_queues[priority]
        
        while self._running:
            try:
                # Get batch of events
                envelopes = []
                
                # Get first event (blocking)
                try:
                    envelope = await asyncio.wait_for(
                        queue.get(), 
                        timeout=self.processing_interval_seconds
                    )
                    envelopes.append(envelope)
                except asyncio.TimeoutError:
                    continue
                
                # Get additional events (non-blocking) up to batch size
                while len(envelopes) < self.processing_batch_size:
                    try:
                        envelope = queue.get_nowait()
                        envelopes.append(envelope)
                    except asyncio.QueueEmpty:
                        break
                
                # Process batch
                await self._process_event_batch(envelopes)
                
            except Exception as e:
                logger.error(f"Error in event processor for {priority.value}: {e}")
                await asyncio.sleep(1)  # Brief pause on error
    
    async def _process_event_batch(self, envelopes: List[EventEnvelope]) -> None:
        """Process a batch of event envelopes"""
        for envelope in envelopes:
            if not envelope.should_process_now():
                # Re-queue for later processing
                await self._retry_queue.put(envelope)
                continue
            
            await self._process_single_event(envelope)
    
    async def _process_single_event(self, envelope: EventEnvelope) -> None:
        """Process a single event envelope"""
        event = envelope.event
        handlers = self._handlers.get(event.event_type, [])
        
        if not handlers:
            logger.warning(f"No handlers found for event type: {event.event_type}")
            return
        
        # Process with each handler
        for handler in handlers:
            await self._process_with_handler(envelope, handler)
    
    async def _process_with_handler(self, envelope: EventEnvelope, 
                                  handler: IEventHandler) -> None:
        """Process event with a specific handler"""
        event = envelope.event
        circuit_breaker = self._handler_circuit_breakers.get(handler.handler_name)
        
        # Check circuit breaker
        if circuit_breaker and not circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker open for handler {handler.handler_name}")
            self._stats['circuit_breakers_open'] += 1
            return
        
        start_time = datetime.now()
        
        try:
            # Process event
            result = await handler.handle(event)
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if result.success:
                # Record success
                if circuit_breaker:
                    circuit_breaker.record_success()
                
                self._stats['events_processed'] += 1
                
                # Publish any resulting events
                if result.events_to_publish:
                    for new_event in result.events_to_publish:
                        await self.publish(new_event, envelope.priority)
                
                if self.metrics:
                    self.metrics.record_event_processed(
                        event.event_type,
                        handler.handler_name,
                        True,
                        processing_time
                    )
                
                logger.debug(f"Handler {handler.handler_name} processed {event.event_type} successfully")
                
            else:
                # Handle failure
                await self._handle_processing_failure(envelope, handler, result)
                
        except Exception as e:
            # Handle unexpected exception
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if circuit_breaker:
                circuit_breaker.record_failure()
            
            self._stats['events_failed'] += 1
            
            if self.metrics:
                self.metrics.record_event_processed(
                    event.event_type,
                    handler.handler_name,
                    False,
                    processing_time
                )
                self.metrics.record_handler_error(handler.handler_name, type(e).__name__)
            
            logger.error(f"Handler {handler.handler_name} failed processing {event.event_type}: {e}")
            
            # Create failure result for retry logic
            failure_result = HandlerResult.failure(str(e), should_retry=True)
            await self._handle_processing_failure(envelope, handler, failure_result)
    
    async def _handle_processing_failure(self, envelope: EventEnvelope,
                                       handler: IEventHandler, 
                                       result: HandlerResult) -> None:
        """Handle processing failure with retry logic"""
        if not result.should_retry or envelope.retry_count >= envelope.max_retries:
            logger.error(f"Max retries exceeded for event {envelope.event.event_type} "
                        f"with handler {handler.handler_name}")
            # TODO: Send to dead letter queue
            return
        
        # Calculate retry delay
        retry_policy = RetryPolicy.exponential_backoff()
        delay = retry_policy.calculate_delay(envelope.retry_count + 1)
        
        # Update envelope for retry
        envelope.increment_retry(delay)
        
        # Add to retry queue
        await self._retry_queue.put(envelope)
        
        logger.info(f"Scheduled retry for event {envelope.event.event_type} "
                   f"in {delay:.2f} seconds (attempt {envelope.retry_count})")
    
    async def _process_retry_queue(self) -> None:
        """Process the retry queue"""
        while self._running:
            try:
                # Check for events ready to retry
                envelope = await asyncio.wait_for(
                    self._retry_queue.get(),
                    timeout=1.0
                )
                
                if envelope.should_process_now():
                    # Re-queue to appropriate priority queue
                    await self._event_queues[envelope.priority].put(envelope)
                else:
                    # Put back in retry queue
                    await self._retry_queue.put(envelope)
                    await asyncio.sleep(0.1)  # Brief pause
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in retry processor: {e}")
                await asyncio.sleep(1)
    
    def get_statistics(self) -> Dict[str, any]:
        """Get event bus statistics"""
        queue_sizes = {
            f"queue_{priority.value}": queue.qsize() 
            for priority, queue in self._event_queues.items()
        }
        
        return {
            **self._stats,
            **queue_sizes,
            'retry_queue_size': self._retry_queue.qsize(),
            'running': self._running,
            'active_handlers': len(self._handlers)
        }


class EventBusManager:
    """
    Manager for event bus lifecycle and configuration
    Singleton pattern for application-wide event bus access
    """
    
    _instance: Optional['EventBusManager'] = None
    _event_bus: Optional[IEventBus] = None
    
    def __new__(cls) -> 'EventBusManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'EventBusManager':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def initialize(self, event_bus: IEventBus) -> None:
        """Initialize with event bus implementation"""
        self._event_bus = event_bus
    
    def get_event_bus(self) -> IEventBus:
        """Get the current event bus instance"""
        if self._event_bus is None:
            # Default to in-memory implementation
            self._event_bus = InMemoryEventBus()
        return self._event_bus
    
    async def start(self) -> None:
        """Start the event bus"""
        event_bus = self.get_event_bus()
        await event_bus.start()
    
    async def stop(self) -> None:
        """Stop the event bus"""
        if self._event_bus:
            await self._event_bus.stop()


# Convenience functions for global access
def get_event_bus() -> IEventBus:
    """Get the global event bus instance"""
    return EventBusManager.get_instance().get_event_bus()


async def publish_event(event: DomainEvent, 
                       priority: EventPriority = EventPriority.NORMAL) -> None:
    """Publish an event using the global event bus"""
    event_bus = get_event_bus()
    await event_bus.publish(event, priority)


async def publish_events(events: List[DomainEvent],
                        priority: EventPriority = EventPriority.NORMAL) -> None:
    """Publish multiple events using the global event bus"""
    event_bus = get_event_bus()
    await event_bus.publish_batch(events, priority)