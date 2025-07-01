"""
Event Subscriber for CPA WorkflowPilot
Handles subscribing to Redis channels and processing events.
"""

import logging
import asyncio
import time
import json
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
import threading

from src.shared.database.redis_client import redis_client
from src.shared.events.base import BaseEvent, EventHandler, EventProcessingResult, event_registry

logger = logging.getLogger(__name__)


class EventSubscriber:
    """
    Event subscriber for the CPA WorkflowPilot system
    
    Subscribes to Redis channels and processes events through registered handlers.
    """
    
    def __init__(self, redis_client_instance=None):
        """
        Initialize event subscriber
        
        Args:
            redis_client_instance: Redis client instance (optional)
        """
        self.redis_client = redis_client_instance or redis_client
        self.handlers: Dict[str, List[EventHandler]] = {}
        self.middleware: List[Callable] = []
        self.is_running = False
        self.subscriber_thread = None
        self.default_channels = ["workflow_events"]
        
    def add_handler(self, event_type: str, handler: EventHandler):
        """
        Add an event handler for a specific event type
        
        Args:
            event_type: Type of event to handle
            handler: Handler instance
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        
        self.handlers[event_type].append(handler)
        logger.info(f"Added handler {handler.get_handler_name()} for event type {event_type}")
    
    def add_middleware(self, middleware_func: Callable):
        """
        Add middleware function to process events before handlers
        
        Args:
            middleware_func: Function that takes and returns an event
        """
        self.middleware.append(middleware_func)
        logger.info(f"Added middleware: {middleware_func.__name__}")
    
    def subscribe(self, channels: Optional[List[str]] = None):
        """
        Start subscribing to Redis channels
        
        Args:
            channels: List of channel names to subscribe to
        """
        if self.is_running:
            logger.warning("Subscriber is already running")
            return
        
        if not self.redis_client or not self.redis_client.is_available():
            logger.error("Redis client not available, cannot start subscriber")
            return
        
        target_channels = channels or self.default_channels
        
        def subscriber_worker():
            """Worker function to run in separate thread"""
            try:
                client = self.redis_client.get_client()
                if not client:
                    logger.error("Could not get Redis client for subscription")
                    return
                
                pubsub = client.pubsub()
                
                # Subscribe to channels
                for channel in target_channels:
                    pubsub.subscribe(channel)
                    logger.info(f"Subscribed to channel: {channel}")
                
                self.is_running = True
                logger.info("Event subscriber started")
                
                # Listen for messages
                for message in pubsub.listen():
                    if not self.is_running:
                        break
                    
                    if message['type'] == 'message':
                        self._process_message(message)
                
            except Exception as e:
                logger.error(f"Error in subscriber worker: {e}")
            finally:
                self.is_running = False
                if 'pubsub' in locals():
                    pubsub.close()
                logger.info("Event subscriber stopped")
        
        # Start subscriber in separate thread
        self.subscriber_thread = threading.Thread(target=subscriber_worker, daemon=True)
        self.subscriber_thread.start()
    
    def stop(self):
        """Stop the event subscriber"""
        if self.is_running:
            self.is_running = False
            logger.info("Stopping event subscriber...")
            
            if self.subscriber_thread:
                self.subscriber_thread.join(timeout=5.0)
                if self.subscriber_thread.is_alive():
                    logger.warning("Subscriber thread did not stop gracefully")
    
    def _process_message(self, message):
        """
        Process a received Redis message
        
        Args:
            message: Redis message dict
        """
        start_time = time.time()
        
        try:
            # Parse message data
            channel = message['channel']
            data = message['data']
            
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            
            event_data = json.loads(data)
            
            # Create event instance
            event = event_registry.create_event_from_dict(event_data)
            if not event:
                logger.warning(f"Could not create event from message data: {event_data.get('event_type')}")
                return
            
            # Process through middleware
            processed_event = event
            for middleware_func in self.middleware:
                try:
                    processed_event = middleware_func(processed_event)
                except Exception as e:
                    logger.error(f"Error in middleware {middleware_func.__name__}: {e}")
                    continue
            
            # Process through handlers
            result = self._handle_event(processed_event)
            
            # Log processing result
            processing_time = (time.time() - start_time) * 1000
            result.processing_time_ms = processing_time
            
            if result.success:
                logger.info(f"Successfully processed event {event.event_type} in {processing_time:.2f}ms")
            else:
                logger.error(f"Failed to process event {event.event_type}: {result.errors}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def _handle_event(self, event: BaseEvent) -> EventProcessingResult:
        """
        Handle an event through registered handlers
        
        Args:
            event: Event to process
            
        Returns:
            EventProcessingResult: Processing result
        """
        result = EventProcessingResult(
            success=True,
            event_id=event.event_id
        )
        
        event_type = event.event_type
        handlers = self.handlers.get(event_type, [])
        
        if not handlers:
            logger.warning(f"No handlers registered for event type: {event_type}")
            result.success = False
            result.errors.append(f"No handlers for event type: {event_type}")
            return result
        
        # Process through each handler
        for handler in handlers:
            try:
                if handler.can_handle(event):
                    # For now, run handlers synchronously
                    # In future, could make this async
                    handler_success = asyncio.run(handler.handle(event))
                    
                    result.add_handler_result(
                        handler.get_handler_name(),
                        handler_success
                    )
                    
                    if not handler_success:
                        result.success = False
                else:
                    logger.debug(f"Handler {handler.get_handler_name()} cannot handle event {event_type}")
                    
            except Exception as e:
                logger.error(f"Error in handler {handler.get_handler_name()}: {e}")
                result.add_handler_result(
                    handler.get_handler_name(),
                    False,
                    str(e)
                )
                result.success = False
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get subscriber statistics
        
        Returns:
            dict: Subscriber statistics
        """
        return {
            'is_running': self.is_running,
            'redis_available': self.redis_client.is_available() if self.redis_client else False,
            'registered_handlers': {
                event_type: len(handlers) 
                for event_type, handlers in self.handlers.items()
            },
            'middleware_count': len(self.middleware),
            'subscribed_channels': self.default_channels
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Health check for event subscriber
        
        Returns:
            dict: Health status information
        """
        status = {
            'component': 'event_subscriber',
            'status': 'healthy',
            'checks': {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Check if subscriber is running
        status['checks']['subscriber_running'] = {
            'status': 'healthy' if self.is_running else 'warning',
            'is_running': self.is_running,
            'message': 'Subscriber is running' if self.is_running else 'Subscriber is not running'
        }
        
        # Check Redis connection
        if self.redis_client:
            redis_health = self.redis_client.health_check()
            status['checks']['redis'] = redis_health
            
            if redis_health['status'] != 'healthy':
                status['status'] = 'degraded'
        else:
            status['checks']['redis'] = {'status': 'unavailable', 'message': 'No Redis client'}
            status['status'] = 'degraded'
        
        # Check handler registration
        handler_count = sum(len(handlers) for handlers in self.handlers.values())
        status['checks']['handlers'] = {
            'status': 'healthy' if handler_count > 0 else 'warning',
            'total_handlers': handler_count,
            'event_types': len(self.handlers),
            'message': f"{handler_count} handlers registered for {len(self.handlers)} event types"
        }
        
        if not self.is_running and self.redis_client and self.redis_client.is_available():
            status['status'] = 'warning'
        
        return status


# Sample Event Handlers
class LoggingHandler(EventHandler):
    """Simple handler that logs all events"""
    
    def can_handle(self, event: BaseEvent) -> bool:
        return True  # Handle all events
    
    async def handle(self, event: BaseEvent) -> bool:
        try:
            logger.info(f"Event logged: {event.event_type} from firm {event.firm_id}")
            return True
        except Exception as e:
            logger.error(f"Error in logging handler: {e}")
            return False


class NotificationHandler(EventHandler):
    """Handler for notification events"""
    
    def can_handle(self, event: BaseEvent) -> bool:
        return event.event_type == 'NotificationEvent'
    
    async def handle(self, event: BaseEvent) -> bool:
        try:
            # In a real implementation, this would send notifications
            # via email, SMS, push notifications, etc.
            payload = event.get_payload()
            logger.info(f"Would send notification: {payload.get('title')} to user {payload.get('recipient_user_id')}")
            return True
        except Exception as e:
            logger.error(f"Error in notification handler: {e}")
            return False


class TaskStatusHandler(EventHandler):
    """Handler for task status change events"""
    
    def can_handle(self, event: BaseEvent) -> bool:
        return event.event_type in ['TaskStatusChangedEvent', 'TaskCompletedEvent']
    
    async def handle(self, event: BaseEvent) -> bool:
        try:
            payload = event.get_payload()
            
            if event.event_type == 'TaskCompletedEvent':
                # Handle task completion logic
                logger.info(f"Task completed: {payload.get('task_title')}")
                
                # Could trigger project completion check here
                # Could send completion notifications
                # Could update analytics
                
            elif event.event_type == 'TaskStatusChangedEvent':
                # Handle status change logic
                logger.info(f"Task status changed: {payload.get('task_title')} from {payload.get('old_status')} to {payload.get('new_status')}")
            
            return True
        except Exception as e:
            logger.error(f"Error in task status handler: {e}")
            return False


# Global event subscriber instance
event_subscriber: Optional[EventSubscriber] = None


def init_event_subscriber(redis_client_instance=None):
    """
    Initialize global event subscriber with default handlers
    
    Args:
        redis_client_instance: Redis client instance (optional)
    """
    global event_subscriber
    
    event_subscriber = EventSubscriber(redis_client_instance)
    
    # Register default handlers
    event_subscriber.add_handler('*', LoggingHandler())  # Log all events
    event_subscriber.add_handler('NotificationEvent', NotificationHandler())
    event_subscriber.add_handler('TaskStatusChangedEvent', TaskStatusHandler())
    event_subscriber.add_handler('TaskCompletedEvent', TaskStatusHandler())
    
    logger.info("Event subscriber initialized with default handlers")
    return event_subscriber


def start_event_processing(channels: Optional[List[str]] = None):
    """
    Start event processing (convenience function)
    
    Args:
        channels: List of channels to subscribe to
    """
    if not event_subscriber:
        logger.warning("Event subscriber not initialized, creating default instance")
        init_event_subscriber()
    
    event_subscriber.subscribe(channels)


def stop_event_processing():
    """Stop event processing (convenience function)"""
    if event_subscriber:
        event_subscriber.stop()
