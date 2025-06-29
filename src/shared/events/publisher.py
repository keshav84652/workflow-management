"""
Event Publisher for CPA WorkflowPilot
Handles publishing events to Redis channels and message queues.
"""

import logging
import time
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..database.redis_client import redis_client, with_redis
from .base import BaseEvent, EventProcessingResult

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Event publisher for the CPA WorkflowPilot system
    
    Publishes events to Redis channels for real-time processing
    and queues them for background processing.
    """
    
    def __init__(self, redis_client_instance=None):
        """
        Initialize event publisher
        
        Args:
            redis_client_instance: Redis client instance (optional)
        """
        self.redis_client = redis_client_instance or redis_client
        self.default_channel = "workflow_events"
        self.fallback_events = []  # Store events when Redis is unavailable
        
    def publish(self, event: BaseEvent, channel: Optional[str] = None) -> bool:
        """
        Publish event to Redis channel
        
        Args:
            event: Event to publish
            channel: Redis channel name (uses default if not specified)
            
        Returns:
            bool: True if successfully published, False otherwise
        """
        start_time = time.time()
        
        try:
            # Set default context if not provided (only if attributes exist)
            if hasattr(event, 'firm_id') and getattr(event, 'firm_id', None) is None:
                try:
                    from flask import session
                    event.firm_id = session.get('firm_id')
                except (RuntimeError, ImportError):
                    # No Flask application context available
                    pass
            if hasattr(event, 'user_id') and getattr(event, 'user_id', None) is None:
                try:
                    from flask import session
                    event.user_id = session.get('user_id')
                except (RuntimeError, ImportError):
                    # No Flask application context available
                    pass
            
            # Use default channel if not specified
            target_channel = channel or self.default_channel
            
            # Try to publish to Redis
            if self.redis_client and self.redis_client.is_available():
                import json
                event_json = json.dumps(event.to_dict())
                success = self.redis_client.publish(target_channel, event_json)
                
                if success:
                    logger.info(f"Published event {event.event_type} to channel {target_channel}")
                    
                    # Store event metadata for monitoring
                    self._store_event_metadata(event, target_channel, time.time() - start_time)
                    
                    return True
                else:
                    logger.warning(f"Failed to publish event {event.event_type} to Redis")
            
            # Fallback: store event locally for later processing
            self._store_fallback_event(event, target_channel)
            return False
            
        except Exception as e:
            logger.error(f"Error publishing event {event.event_type}: {e}")
            self._store_fallback_event(event, channel)
            return False
    
    def publish_multiple(self, events: List[BaseEvent], channel: Optional[str] = None) -> Dict[str, bool]:
        """
        Publish multiple events in batch
        
        Args:
            events: List of events to publish
            channel: Redis channel name
            
        Returns:
            dict: Results for each event {event_id: success}
        """
        results = {}
        
        for event in events:
            success = self.publish(event, channel)
            results[event.event_id] = success
        
        logger.info(f"Batch published {len(events)} events, {sum(results.values())} successful")
        return results
    
    @with_redis(fallback_return=False)
    def _store_event_metadata(self, event: BaseEvent, channel: str, processing_time: float):
        """Store event metadata for monitoring and analytics"""
        try:
            metadata_key = f"event_metadata:{event.event_id}"
            metadata = {
                'event_type': event.event_type,
                'channel': channel,
                'published_at': datetime.utcnow().isoformat(),
                'processing_time_ms': processing_time * 1000,
                'firm_id': getattr(event, 'firm_id', None),
                'user_id': getattr(event, 'user_id', None)
            }
            
            # Store with 24 hour expiration
            self.redis_client.set(metadata_key, metadata, ex=86400)
            
            # Update event type counters
            counter_key = f"event_counter:{event.event_type}:{datetime.utcnow().strftime('%Y-%m-%d')}"
            client = self.redis_client.get_client()
            if client:
                client.incr(counter_key)
                client.expire(counter_key, 86400 * 7)  # Keep for 7 days
                
        except Exception as e:
            logger.warning(f"Failed to store event metadata: {e}")
    
    def _store_fallback_event(self, event: BaseEvent, channel: Optional[str]):
        """Store event locally when Redis is unavailable"""
        try:
            fallback_entry = {
                'event': event.to_dict(),
                'channel': channel or self.default_channel,
                'stored_at': datetime.utcnow().isoformat(),
                'retry_count': 0
            }
            
            self.fallback_events.append(fallback_entry)
            
            # Limit fallback storage to prevent memory issues
            if len(self.fallback_events) > 1000:
                self.fallback_events = self.fallback_events[-1000:]
            
            logger.warning(f"Stored event {event.event_type} in fallback storage")
            
        except Exception as e:
            logger.error(f"Failed to store fallback event: {e}")
    
    def retry_fallback_events(self) -> int:
        """
        Retry publishing events stored in fallback storage
        
        Returns:
            int: Number of events successfully published
        """
        if not self.fallback_events:
            return 0
        
        if not self.redis_client or not self.redis_client.is_available():
            logger.warning("Redis still unavailable, cannot retry fallback events")
            return 0
        
        successful_count = 0
        remaining_events = []
        
        for entry in self.fallback_events:
            try:
                # Recreate event from stored data
                from .base import event_registry
                event = event_registry.create_event_from_dict(entry['event'])
                
                if event:
                    import json
                    event_json = json.dumps(event.to_dict())
                    success = self.redis_client.publish(entry['channel'], event_json)
                    if success:
                        successful_count += 1
                        logger.info(f"Successfully retried event {event.event_type}")
                    else:
                        # Increment retry count and keep for later
                        entry['retry_count'] += 1
                        if entry['retry_count'] < 5:  # Max 5 retries
                            remaining_events.append(entry)
                else:
                    logger.warning(f"Could not recreate event from fallback data")
                    
            except Exception as e:
                logger.error(f"Error retrying fallback event: {e}")
                # Keep for retry if not too many attempts
                entry['retry_count'] = entry.get('retry_count', 0) + 1
                if entry['retry_count'] < 5:
                    remaining_events.append(entry)
        
        # Update fallback storage
        self.fallback_events = remaining_events
        
        if successful_count > 0:
            logger.info(f"Successfully retried {successful_count} fallback events")
        
        return successful_count
    
    def get_event_stats(self) -> Dict[str, Any]:
        """
        Get event publishing statistics
        
        Returns:
            dict: Statistics about event publishing
        """
        stats = {
            'redis_available': self.redis_client.is_available() if self.redis_client else False,
            'fallback_events_count': len(self.fallback_events),
            'total_event_types': 0,
            'daily_counts': {}
        }
        
        if self.redis_client and self.redis_client.is_available():
            try:
                client = self.redis_client.get_client()
                if client:
                    # Get event type counts for today
                    today = datetime.utcnow().strftime('%Y-%m-%d')
                    pattern = f"event_counter:*:{today}"
                    
                    for key in client.scan_iter(match=pattern):
                        event_type = key.split(':')[1]
                        count = client.get(key)
                        if count:
                            stats['daily_counts'][event_type] = int(count)
                    
                    stats['total_event_types'] = len(stats['daily_counts'])
                    
            except Exception as e:
                logger.warning(f"Failed to get event stats: {e}")
        
        return stats
    
    def health_check(self) -> Dict[str, Any]:
        """
        Health check for event publishing system
        
        Returns:
            dict: Health status information
        """
        status = {
            'component': 'event_publisher',
            'status': 'healthy',
            'checks': {},
            'timestamp': datetime.utcnow().isoformat()
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
        
        # Check fallback storage
        fallback_count = len(self.fallback_events)
        status['checks']['fallback_storage'] = {
            'status': 'healthy' if fallback_count < 100 else 'warning',
            'fallback_events_count': fallback_count,
            'message': f"{fallback_count} events in fallback storage"
        }
        
        if fallback_count >= 500:
            status['status'] = 'warning'
        
        return status


# Global event publisher instance
event_publisher: Optional[EventPublisher] = None


def init_event_publisher(redis_client_instance=None):
    """
    Initialize global event publisher
    
    Args:
        redis_client_instance: Redis client instance (optional)
    """
    global event_publisher
    event_publisher = EventPublisher(redis_client_instance)
    logger.info("Event publisher initialized")
    return event_publisher


def publish_event(event: BaseEvent, channel: Optional[str] = None) -> bool:
    """
    Convenience function to publish an event using the global publisher
    
    Args:
        event: Event to publish
        channel: Redis channel (optional)
        
    Returns:
        bool: True if successful
    """
    if not event_publisher:
        logger.warning("Event publisher not initialized, creating default instance")
        init_event_publisher()
    
    return event_publisher.publish(event, channel)
