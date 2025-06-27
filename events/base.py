"""
Base Event Classes for CPA WorkflowPilot Event-Driven Architecture
Provides the foundation for event publishing and handling.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, Type
from dataclasses import dataclass, field
import uuid
import json


@dataclass
class BaseEvent(ABC):
    """
    Base class for all domain events
    
    All events in the system should inherit from this class.
    """
    # Context information (put optional fields with defaults last)
    firm_id: Optional[int] = None
    user_id: Optional[int] = None
    
    # Event metadata (all have defaults)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = field(init=False)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0"
    source_system: str = "workflow-management"
    
    # Event payload (to be defined by subclasses)
    @abstractmethod
    def get_payload(self) -> Dict[str, Any]:
        """Return the event payload data"""
        pass
    
    def __post_init__(self):
        """Set event_type after initialization"""
        if not hasattr(self, 'event_type') or not self.event_type:
            self.event_type = self.__class__.__name__
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert event to dictionary format for serialization
        
        Returns:
            dict: Complete event data including metadata and payload
        """
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'version': self.version,
            'firm_id': self.firm_id,
            'user_id': self.user_id,
            'source_system': self.source_system,
            'payload': self.get_payload()
        }
    
    def to_json(self) -> str:
        """
        Convert event to JSON string
        
        Returns:
            str: JSON representation of the event
        """
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseEvent':
        """
        Create event instance from dictionary
        
        Args:
            data: Event data dictionary
            
        Returns:
            BaseEvent: Event instance
        """
        # Extract metadata
        event_id = data.get('event_id')
        timestamp_str = data.get('timestamp')
        timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.utcnow()
        version = data.get('version', '1.0')
        firm_id = data.get('firm_id')
        user_id = data.get('user_id')
        source_system = data.get('source_system', 'workflow-management')
        
        # Extract payload
        payload = data.get('payload', {})
        
        # Create instance (subclasses should override this method)
        instance = cls(**payload)
        instance.event_id = event_id or str(uuid.uuid4())
        instance.timestamp = timestamp
        instance.version = version
        instance.firm_id = firm_id
        instance.user_id = user_id
        instance.source_system = source_system
        
        return instance


class EventHandler(ABC):
    """
    Base class for event handlers
    
    Event handlers process specific types of events and execute business logic.
    """
    
    @abstractmethod
    def can_handle(self, event: BaseEvent) -> bool:
        """
        Check if this handler can process the given event
        
        Args:
            event: Event to check
            
        Returns:
            bool: True if handler can process the event
        """
        pass
    
    @abstractmethod
    async def handle(self, event: BaseEvent) -> bool:
        """
        Process the event
        
        Args:
            event: Event to process
            
        Returns:
            bool: True if successfully processed, False otherwise
        """
        pass
    
    def get_handler_name(self) -> str:
        """Get handler name for logging"""
        return self.__class__.__name__


class EventMiddleware(ABC):
    """
    Base class for event middleware
    
    Middleware can intercept events before they reach handlers for
    logging, validation, transformation, etc.
    """
    
    @abstractmethod
    def process_event(self, event: BaseEvent) -> BaseEvent:
        """
        Process event before it reaches handlers
        
        Args:
            event: Original event
            
        Returns:
            BaseEvent: Processed event (can be modified)
        """
        pass


@dataclass
class EventProcessingResult:
    """Result of event processing operation"""
    success: bool
    event_id: str
    processed_at: datetime = field(default_factory=datetime.utcnow)
    handler_results: Dict[str, bool] = field(default_factory=dict)
    errors: list = field(default_factory=list)
    processing_time_ms: Optional[float] = None
    
    def add_handler_result(self, handler_name: str, success: bool, error: Optional[str] = None):
        """Add result from a specific handler"""
        self.handler_results[handler_name] = success
        if error:
            self.errors.append(f"{handler_name}: {error}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage"""
        return {
            'success': self.success,
            'event_id': self.event_id,
            'processed_at': self.processed_at.isoformat(),
            'handler_results': self.handler_results,
            'errors': self.errors,
            'processing_time_ms': self.processing_time_ms
        }


class EventRegistry:
    """
    Registry for event types and their corresponding schemas
    
    Provides event type validation and schema management.
    """
    
    def __init__(self):
        self._event_types: Dict[str, Type[BaseEvent]] = {}
        self._handlers: Dict[str, list] = {}
    
    def register_event_type(self, event_class: Type[BaseEvent]):
        """
        Register an event type
        
        Args:
            event_class: Event class to register
        """
        event_type = event_class.__name__
        self._event_types[event_type] = event_class

    def clear_handlers(self, event_type: str):
        """
        Clear all handlers for a specific event type

        Args:
            event_type: Type of event to clear handlers for
        """
        if event_type in self._handlers:
            del self._handlers[event_type]
    
    def register_handler(self, event_type: str, handler: EventHandler):
        """
        Register an event handler for a specific event type
        
        Args:
            event_type: Type of event to handle
            handler: Handler instance
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def get_event_class(self, event_type: str) -> Optional[Type[BaseEvent]]:
        """Get event class by type name"""
        return self._event_types.get(event_type)
    
    def get_handlers(self, event_type: str) -> list:
        """Get handlers for specific event type"""
        return self._handlers.get(event_type, [])
    
    def get_registered_types(self) -> list:
        """Get list of all registered event types"""
        return list(self._event_types.keys())
    
    def create_event_from_dict(self, data: Dict[str, Any]) -> Optional[BaseEvent]:
        """
        Create event instance from dictionary data
        
        Args:
            data: Event data dictionary
            
        Returns:
            BaseEvent instance or None if type not registered
        """
        event_type = data.get('event_type')
        if not event_type:
            return None
        
        event_class = self.get_event_class(event_type)
        if not event_class:
            return None
        
        return event_class.from_dict(data)


# Global event registry instance
event_registry = EventRegistry()


def register_event(event_class: Type[BaseEvent]):
    """
    Decorator to register event types
    
    Usage:
        @register_event
        class MyEvent(BaseEvent):
            ...
    """
    event_registry.register_event_type(event_class)
    return event_class


def register_handler(event_type: str):
    """
    Decorator to register event handlers
    
    Usage:
        @register_handler('TaskCreated')
        class TaskCreatedHandler(EventHandler):
            ...
    """
    def decorator(handler_class):
        handler_instance = handler_class()
        event_registry.register_handler(event_type, handler_instance)
        return handler_class
    return decorator
