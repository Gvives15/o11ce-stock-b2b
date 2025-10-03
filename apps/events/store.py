"""
Event Store Implementation for Event-Driven Architecture
Provides event persistence, querying, and replay capabilities
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Type
from uuid import UUID, uuid4

from .base import DomainEvent, IEventStore


logger = logging.getLogger(__name__)


@dataclass
class EventRecord:
    """Stored event record with metadata"""
    event_id: UUID
    event_type: str
    event_version: str
    aggregate_id: Optional[UUID]
    aggregate_type: Optional[str]
    event_data: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime
    sequence_number: int
    correlation_id: Optional[UUID] = None
    causation_id: Optional[UUID] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'event_id': str(self.event_id),
            'event_type': self.event_type,
            'event_version': self.event_version,
            'aggregate_id': str(self.aggregate_id) if self.aggregate_id else None,
            'aggregate_type': self.aggregate_type,
            'event_data': self.event_data,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
            'sequence_number': self.sequence_number,
            'correlation_id': str(self.correlation_id) if self.correlation_id else None,
            'causation_id': str(self.causation_id) if self.causation_id else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventRecord':
        """Create from dictionary"""
        return cls(
            event_id=UUID(data['event_id']),
            event_type=data['event_type'],
            event_version=data['event_version'],
            aggregate_id=UUID(data['aggregate_id']) if data.get('aggregate_id') else None,
            aggregate_type=data.get('aggregate_type'),
            event_data=data['event_data'],
            metadata=data['metadata'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            sequence_number=data['sequence_number'],
            correlation_id=UUID(data['correlation_id']) if data.get('correlation_id') else None,
            causation_id=UUID(data['causation_id']) if data.get('causation_id') else None
        )


@dataclass
class EventQuery:
    """Query parameters for event retrieval"""
    aggregate_id: Optional[UUID] = None
    aggregate_type: Optional[str] = None
    event_types: Optional[List[str]] = None
    from_timestamp: Optional[datetime] = None
    to_timestamp: Optional[datetime] = None
    from_sequence: Optional[int] = None
    to_sequence: Optional[int] = None
    correlation_id: Optional[UUID] = None
    limit: int = 100
    offset: int = 0


@dataclass
class EventStream:
    """Stream of events with metadata"""
    events: List[EventRecord]
    total_count: int
    has_more: bool
    next_sequence: Optional[int] = None


class EventStoreError(Exception):
    """Base exception for event store operations"""
    pass


class ConcurrencyError(EventStoreError):
    """Raised when concurrent modification is detected"""
    pass


class EventNotFoundError(EventStoreError):
    """Raised when event is not found"""
    pass


class InMemoryEventStore(IEventStore):
    """In-memory implementation of event store"""
    
    def __init__(self):
        self._events: List[EventRecord] = []
        self._sequence_counter = 0
        self._aggregate_sequences: Dict[str, int] = {}  # aggregate_id -> last_sequence
        self._lock = asyncio.Lock()
    
    async def append_event(self, 
                          event: DomainEvent, 
                          expected_version: Optional[int] = None) -> EventRecord:
        """Append event to store"""
        async with self._lock:
            # Generate sequence number
            self._sequence_counter += 1
            sequence_number = self._sequence_counter
            
            # Check concurrency if expected version provided
            if expected_version is not None and event.aggregate_id:
                aggregate_key = str(event.aggregate_id)
                current_version = self._aggregate_sequences.get(aggregate_key, 0)
                if current_version != expected_version:
                    raise ConcurrencyError(
                        f"Expected version {expected_version}, but current version is {current_version}"
                    )
            
            # Create event record
            event_record = EventRecord(
                event_id=event.event_id,
                event_type=event.event_type,
                event_version=event.event_version,
                aggregate_id=event.aggregate_id,
                aggregate_type=event.aggregate_type,
                event_data=event.to_dict(),
                metadata={
                    'source': event.source,
                    'user_id': str(event.user_id) if event.user_id else None,
                    'tenant_id': str(event.tenant_id) if event.tenant_id else None,
                    'correlation_id': str(event.correlation_id) if event.correlation_id else None,
                    'causation_id': str(event.causation_id) if event.causation_id else None
                },
                timestamp=event.timestamp,
                sequence_number=sequence_number,
                correlation_id=event.correlation_id,
                causation_id=event.causation_id
            )
            
            # Store event
            self._events.append(event_record)
            
            # Update aggregate sequence
            if event.aggregate_id:
                aggregate_key = str(event.aggregate_id)
                self._aggregate_sequences[aggregate_key] = sequence_number
            
            logger.debug(f"Appended event {event.event_type} with sequence {sequence_number}")
            return event_record
    
    async def get_events(self, query: EventQuery) -> EventStream:
        """Get events matching query"""
        async with self._lock:
            filtered_events = self._filter_events(query)
            
            # Apply pagination
            total_count = len(filtered_events)
            start_idx = query.offset
            end_idx = start_idx + query.limit
            
            paginated_events = filtered_events[start_idx:end_idx]
            has_more = end_idx < total_count
            
            next_sequence = None
            if paginated_events:
                next_sequence = paginated_events[-1].sequence_number + 1
            
            return EventStream(
                events=paginated_events,
                total_count=total_count,
                has_more=has_more,
                next_sequence=next_sequence
            )
    
    async def get_events_by_aggregate(self, 
                                    aggregate_id: UUID, 
                                    from_version: int = 0) -> List[EventRecord]:
        """Get all events for specific aggregate"""
        query = EventQuery(
            aggregate_id=aggregate_id,
            from_sequence=from_version,
            limit=10000  # Large limit to get all events
        )
        stream = await self.get_events(query)
        return stream.events
    
    async def get_event_by_id(self, event_id: UUID) -> Optional[EventRecord]:
        """Get specific event by ID"""
        async with self._lock:
            for event in self._events:
                if event.event_id == event_id:
                    return event
            return None
    
    async def get_aggregate_version(self, aggregate_id: UUID) -> int:
        """Get current version of aggregate"""
        async with self._lock:
            aggregate_key = str(aggregate_id)
            return self._aggregate_sequences.get(aggregate_key, 0)
    
    async def get_events_since(self, 
                              since_sequence: int, 
                              limit: int = 100) -> List[EventRecord]:
        """Get events since specific sequence number"""
        query = EventQuery(
            from_sequence=since_sequence + 1,
            limit=limit
        )
        stream = await self.get_events(query)
        return stream.events
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get event store statistics"""
        async with self._lock:
            event_types = {}
            aggregate_types = {}
            
            for event in self._events:
                # Count by event type
                event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
                
                # Count by aggregate type
                if event.aggregate_type:
                    aggregate_types[event.aggregate_type] = \
                        aggregate_types.get(event.aggregate_type, 0) + 1
            
            return {
                'total_events': len(self._events),
                'total_aggregates': len(self._aggregate_sequences),
                'current_sequence': self._sequence_counter,
                'event_types': event_types,
                'aggregate_types': aggregate_types,
                'oldest_event': self._events[0].timestamp.isoformat() if self._events else None,
                'newest_event': self._events[-1].timestamp.isoformat() if self._events else None
            }
    
    def _filter_events(self, query: EventQuery) -> List[EventRecord]:
        """Filter events based on query parameters"""
        filtered = self._events
        
        # Filter by aggregate ID
        if query.aggregate_id:
            filtered = [e for e in filtered if e.aggregate_id == query.aggregate_id]
        
        # Filter by aggregate type
        if query.aggregate_type:
            filtered = [e for e in filtered if e.aggregate_type == query.aggregate_type]
        
        # Filter by event types
        if query.event_types:
            filtered = [e for e in filtered if e.event_type in query.event_types]
        
        # Filter by timestamp range
        if query.from_timestamp:
            filtered = [e for e in filtered if e.timestamp >= query.from_timestamp]
        if query.to_timestamp:
            filtered = [e for e in filtered if e.timestamp <= query.to_timestamp]
        
        # Filter by sequence range
        if query.from_sequence:
            filtered = [e for e in filtered if e.sequence_number >= query.from_sequence]
        if query.to_sequence:
            filtered = [e for e in filtered if e.sequence_number <= query.to_sequence]
        
        # Filter by correlation ID
        if query.correlation_id:
            filtered = [e for e in filtered if e.correlation_id == query.correlation_id]
        
        # Sort by sequence number
        filtered.sort(key=lambda e: e.sequence_number)
        
        return filtered


class EventProjection(ABC):
    """Base class for event projections"""
    
    @property
    @abstractmethod
    def projection_name(self) -> str:
        """Name of the projection"""
        pass
    
    @property
    @abstractmethod
    def handled_events(self) -> List[str]:
        """List of event types this projection handles"""
        pass
    
    @abstractmethod
    async def handle_event(self, event: EventRecord) -> None:
        """Handle an event for projection"""
        pass
    
    @abstractmethod
    async def reset(self) -> None:
        """Reset projection state"""
        pass


@dataclass
class ProjectionCheckpoint:
    """Checkpoint for projection processing"""
    projection_name: str
    last_processed_sequence: int
    last_processed_at: datetime
    total_events_processed: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'projection_name': self.projection_name,
            'last_processed_sequence': self.last_processed_sequence,
            'last_processed_at': self.last_processed_at.isoformat(),
            'total_events_processed': self.total_events_processed
        }


class ProjectionManager:
    """Manages event projections and their checkpoints"""
    
    def __init__(self, event_store: IEventStore):
        self.event_store = event_store
        self.projections: Dict[str, EventProjection] = {}
        self.checkpoints: Dict[str, ProjectionCheckpoint] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
    
    def register_projection(self, projection: EventProjection):
        """Register a projection"""
        self.projections[projection.projection_name] = projection
        
        # Initialize checkpoint if not exists
        if projection.projection_name not in self.checkpoints:
            self.checkpoints[projection.projection_name] = ProjectionCheckpoint(
                projection_name=projection.projection_name,
                last_processed_sequence=0,
                last_processed_at=datetime.now()
            )
    
    async def start_projections(self):
        """Start processing projections"""
        if self._running:
            return
        
        self._running = True
        
        for projection_name in self.projections:
            task = asyncio.create_task(self._process_projection(projection_name))
            self._tasks.append(task)
        
        logger.info(f"Started {len(self.projections)} projections")
    
    async def stop_projections(self):
        """Stop processing projections"""
        self._running = False
        
        for task in self._tasks:
            task.cancel()
        
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        
        logger.info("Stopped all projections")
    
    async def rebuild_projection(self, projection_name: str):
        """Rebuild projection from beginning"""
        if projection_name not in self.projections:
            raise ValueError(f"Projection {projection_name} not found")
        
        projection = self.projections[projection_name]
        
        # Reset projection
        await projection.reset()
        
        # Reset checkpoint
        self.checkpoints[projection_name] = ProjectionCheckpoint(
            projection_name=projection_name,
            last_processed_sequence=0,
            last_processed_at=datetime.now()
        )
        
        # Process all events
        await self._process_projection_batch(projection_name)
        
        logger.info(f"Rebuilt projection {projection_name}")
    
    async def _process_projection(self, projection_name: str):
        """Process events for a specific projection"""
        while self._running:
            try:
                await self._process_projection_batch(projection_name)
                await asyncio.sleep(1)  # Poll every second
            except Exception as e:
                logger.error(f"Error processing projection {projection_name}: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _process_projection_batch(self, projection_name: str):
        """Process a batch of events for projection"""
        projection = self.projections[projection_name]
        checkpoint = self.checkpoints[projection_name]
        
        # Get new events since last checkpoint
        events = await self.event_store.get_events_since(
            checkpoint.last_processed_sequence,
            limit=100
        )
        
        # Filter events for this projection
        relevant_events = [
            event for event in events
            if event.event_type in projection.handled_events
        ]
        
        # Process events
        for event in relevant_events:
            await projection.handle_event(event)
            
            # Update checkpoint
            checkpoint.last_processed_sequence = event.sequence_number
            checkpoint.last_processed_at = datetime.now()
            checkpoint.total_events_processed += 1
        
        if relevant_events:
            logger.debug(f"Processed {len(relevant_events)} events for projection {projection_name}")
    
    def get_projection_status(self) -> Dict[str, Any]:
        """Get status of all projections"""
        status = {}
        
        for name, checkpoint in self.checkpoints.items():
            status[name] = {
                'last_processed_sequence': checkpoint.last_processed_sequence,
                'last_processed_at': checkpoint.last_processed_at.isoformat(),
                'total_events_processed': checkpoint.total_events_processed,
                'is_running': self._running
            }
        
        return status


class EventReplayService:
    """Service for replaying events"""
    
    def __init__(self, event_store: IEventStore):
        self.event_store = event_store
    
    async def replay_events(self, 
                           query: EventQuery,
                           handler_func: callable) -> int:
        """Replay events matching query"""
        processed_count = 0
        offset = 0
        batch_size = 100
        
        while True:
            # Get batch of events
            batch_query = EventQuery(
                aggregate_id=query.aggregate_id,
                aggregate_type=query.aggregate_type,
                event_types=query.event_types,
                from_timestamp=query.from_timestamp,
                to_timestamp=query.to_timestamp,
                from_sequence=query.from_sequence,
                to_sequence=query.to_sequence,
                correlation_id=query.correlation_id,
                limit=batch_size,
                offset=offset
            )
            
            stream = await self.event_store.get_events(batch_query)
            
            if not stream.events:
                break
            
            # Process batch
            for event in stream.events:
                await handler_func(event)
                processed_count += 1
            
            # Check if more events available
            if not stream.has_more:
                break
            
            offset += batch_size
        
        logger.info(f"Replayed {processed_count} events")
        return processed_count
    
    async def replay_aggregate(self, 
                              aggregate_id: UUID,
                              handler_func: callable) -> int:
        """Replay all events for specific aggregate"""
        events = await self.event_store.get_events_by_aggregate(aggregate_id)
        
        for event in events:
            await handler_func(event)
        
        logger.info(f"Replayed {len(events)} events for aggregate {aggregate_id}")
        return len(events)