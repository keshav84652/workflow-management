"""
Dead Letter Queue System
Handles failed messages and provides retry mechanisms.
"""

import logging
import json
from datetime import datetime, timedelta
from collections import deque
from typing import List, Any, Dict, Optional, Callable

from ..database.redis_client import redis_client
from .error_handling import (
    redis_circuit_breaker, REDIS_RETRY_CONFIG, with_retry,
    with_error_context, safe_execute
)

logger = logging.getLogger(__name__)

class DeadLetterQueue:
    """
    Dead Letter Queue system for handling failed messages with Redis persistence.
    """
    def __init__(self, 
                 queue_name: str = 'dlq:default',
                 max_retries: int = 5, 
                 max_storage: int = 1000,
                 retry_delay_minutes: int = 30,
                 redis_client_instance=None):
        """
        Initialize the Dead Letter Queue
        
        Args:
            queue_name (str): Name of the queue in Redis
            max_retries (int): Maximum number of retry attempts per message
            max_storage (int): Maximum number of messages to store in the queue
            retry_delay_minutes (int): Minutes to wait before retrying failed messages
            redis_client_instance: Redis client instance (optional)
        """
        self.queue_name = queue_name
        self.max_retries = max_retries
        self.max_storage = max_storage
        self.retry_delay_minutes = retry_delay_minutes
        self.redis_client = redis_client_instance or redis_client
        
        # In-memory fallback for when Redis is unavailable
        self.fallback_queue = deque()
        
        # Registry for retry handlers
        self.retry_handlers: Dict[str, Callable] = {}
        
    def add_to_queue(self, message: Dict[str, Any], error_details: str = None):
        """
        Add a failed message to the queue with Redis persistence
        
        Args:
            message (Dict[str, Any]): Message data to store
            error_details (str): Details about the error that caused the failure
        """
        message_entry = {
            'id': f"{self.queue_name}:{datetime.utcnow().timestamp()}",
            'message': message,
            'retry_count': 0,
            'first_failed_at': datetime.utcnow().isoformat(),
            'last_retry_at': None,
            'error_details': error_details or "Unknown error",
            'next_retry_at': (datetime.utcnow() + timedelta(minutes=self.retry_delay_minutes)).isoformat()
        }
        
        try:
            # Store in Redis with priority queue using sorted sets
            self._store_message_redis(message_entry)
        except Exception as e:
            logger.warning(f"Failed to store message in Redis: {e}. Using fallback storage.")
            self._store_message_fallback(message_entry)
        
        logger.info(f"Added message to Dead Letter Queue: {message_entry['id']}")

    def retry_messages(self) -> int:
        """
        Retry messages stored in the queue
        
        Returns:
            int: Number of messages successfully retried
        """
        success_count = 0
        remaining_messages = deque()
        
        while self.queue:
            entry = self.queue.popleft()
            try:
                # Implement actual retry logic here
                # For example, republish to a message queue or a similar mechanism
                if self._retry_logic(entry['message']):
                    success_count += 1
                    logger.info(f"Successfully retried message: {entry['message']}")
                else:
                    raise Exception("Retry logic failed")
            except Exception as e:
                entry['retry_count'] += 1
                logger.error(f"Failed to retry message: {entry['message']}, error: {e}")
                if entry['retry_count'] < self.max_retries:
                    remaining_messages.append(entry)
        
        self.queue = remaining_messages
        logger.info(f"Retried {success_count} messages successfully")
        return success_count

    def _store_message_redis(self, message_entry: Dict[str, Any]):
        """Store message in Redis using sorted sets for priority queuing"""
        if not redis_circuit_breaker.is_operational():
            raise Exception("Redis circuit breaker is open")
        
        @with_retry(**REDIS_RETRY_CONFIG)
        def _store():
            with redis_client.pipeline() as pipe:
                pipe.multi()
                # Use timestamp as score for FIFO ordering
                next_retry_timestamp = datetime.fromisoformat(message_entry['next_retry_at']).timestamp()
                pipe.zadd(f"{self.queue_name}:retry_queue", {message_entry['id']: next_retry_timestamp})
                pipe.hset(f"{self.queue_name}:messages", message_entry['id'], json.dumps(message_entry))
                pipe.execute()
        
        _store()
    
    def _store_message_fallback(self, message_entry: Dict[str, Any]):
        """Store message in fallback memory storage"""
        if len(self.fallback_queue) >= self.max_storage:
            logger.warning("Fallback Dead Letter Queue is full. Removing oldest message.")
            self.fallback_queue.popleft()
        self.fallback_queue.append(message_entry)
    
    def register_retry_handler(self, message_type: str, handler: Callable):
        """Register a retry handler for specific message types"""
        self.retry_handlers[message_type] = handler
        logger.info(f"Registered retry handler for message type: {message_type}")
    
    @with_error_context("Dead Letter Queue Retry")
    def retry_ready_messages(self) -> Dict[str, int]:
        """
        Retry messages that are ready for retry based on their next_retry_at timestamp
        
        Returns:
            Dict containing retry statistics
        """
        stats = {
            'processed': 0,
            'succeeded': 0,
            'failed': 0,
            'discarded': 0
        }
        
        current_time = datetime.utcnow().timestamp()
        
        try:
            # Process Redis messages first
            stats.update(self._retry_redis_messages(current_time))
        except Exception as e:
            logger.error(f"Failed to retry Redis messages: {e}")
        
        # Process fallback messages
        stats.update(self._retry_fallback_messages())
        
        logger.info(f"DLQ retry completed: {stats}")
        return stats
    
    def _retry_redis_messages(self, current_time: float) -> Dict[str, int]:
        """Retry messages stored in Redis"""
        stats = {'processed': 0, 'succeeded': 0, 'failed': 0, 'discarded': 0}
        
        if not redis_circuit_breaker.is_operational():
            logger.warning("Redis circuit breaker open, skipping Redis message retry")
            return stats
        
        @with_retry(**REDIS_RETRY_CONFIG)
        def _get_ready_messages():
            # Get messages ready for retry (score <= current_time)
            return redis_client.zrangebyscore(
                f"{self.queue_name}:retry_queue", 
                min=0, 
                max=current_time, 
                withscores=True
            )
        
        try:
            ready_messages = _get_ready_messages()
            
            for message_id, _ in ready_messages:
                message_id = message_id.decode('utf-8') if isinstance(message_id, bytes) else message_id
                stats['processed'] += 1
                
                if self._process_message_retry(message_id):
                    stats['succeeded'] += 1
                    self._remove_message_from_redis(message_id)
                else:
                    stats['failed'] += 1
                    # Update retry count and next retry time
                    self._update_message_retry_info(message_id)
        
        except Exception as e:
            logger.error(f"Error processing Redis DLQ messages: {e}")
            redis_circuit_breaker.record_failure()
            raise
        
        return stats
    
    def _retry_fallback_messages(self) -> Dict[str, int]:
        """Retry messages stored in fallback memory storage"""
        stats = {'processed': 0, 'succeeded': 0, 'failed': 0, 'discarded': 0}
        remaining_messages = deque()
        
        while self.fallback_queue:
            entry = self.fallback_queue.popleft()
            stats['processed'] += 1
            
            # Check if message is ready for retry
            next_retry = datetime.fromisoformat(entry['next_retry_at'])
            if datetime.utcnow() < next_retry:
                remaining_messages.append(entry)
                continue
            
            if self._execute_retry_handler(entry):
                stats['succeeded'] += 1
            else:
                entry['retry_count'] += 1
                if entry['retry_count'] < self.max_retries:
                    # Schedule for next retry
                    entry['last_retry_at'] = datetime.utcnow().isoformat()
                    entry['next_retry_at'] = (
                        datetime.utcnow() + 
                        timedelta(minutes=self.retry_delay_minutes * (2 ** entry['retry_count']))
                    ).isoformat()
                    remaining_messages.append(entry)
                    stats['failed'] += 1
                else:
                    logger.warning(f"Discarding message after {self.max_retries} retries: {entry['id']}")
                    stats['discarded'] += 1
        
        self.fallback_queue = remaining_messages
        return stats
    
    def _process_message_retry(self, message_id: str) -> bool:
        """Process a single message retry from Redis storage"""
        try:
            message_data = redis_client.hget(f"{self.queue_name}:messages", message_id)
            if not message_data:
                logger.warning(f"Message {message_id} not found in Redis storage")
                return False
            
            entry = json.loads(message_data)
            return self._execute_retry_handler(entry)
        
        except Exception as e:
            logger.error(f"Failed to process message {message_id}: {e}")
            return False
    
    def _execute_retry_handler(self, entry: Dict[str, Any]) -> bool:
        """Execute the appropriate retry handler for a message"""
        message = entry['message']
        message_type = message.get('type', 'default')
        
        handler = self.retry_handlers.get(message_type, self._default_retry_logic)
        
        try:
            return safe_execute(handler, message, default=False)
        except Exception as e:
            logger.error(f"Retry handler failed for message {entry['id']}: {e}")
            return False
    
    def _remove_message_from_redis(self, message_id: str):
        """Remove successfully retried message from Redis"""
        try:
            with redis_client.pipeline() as pipe:
                pipe.multi()
                pipe.zrem(f"{self.queue_name}:retry_queue", message_id)
                pipe.hdel(f"{self.queue_name}:messages", message_id)
                pipe.execute()
        except Exception as e:
            logger.error(f"Failed to remove message {message_id} from Redis: {e}")
    
    def _update_message_retry_info(self, message_id: str):
        """Update retry information for a failed message"""
        try:
            message_data = redis_client.hget(f"{self.queue_name}:messages", message_id)
            if message_data:
                entry = json.loads(message_data)
                entry['retry_count'] += 1
                
                if entry['retry_count'] >= self.max_retries:
                    # Remove from retry queue if max retries reached
                    self._remove_message_from_redis(message_id)
                    logger.warning(f"Message {message_id} exceeded max retries and was discarded")
                else:
                    # Update retry timestamp with exponential backoff
                    entry['last_retry_at'] = datetime.utcnow().isoformat()
                    entry['next_retry_at'] = (
                        datetime.utcnow() + 
                        timedelta(minutes=self.retry_delay_minutes * (2 ** entry['retry_count']))
                    ).isoformat()
                    
                    # Update stored message and retry queue
                    with redis_client.pipeline() as pipe:
                        pipe.multi()
                        pipe.hset(f"{self.queue_name}:messages", message_id, json.dumps(entry))
                        next_retry_timestamp = datetime.fromisoformat(entry['next_retry_at']).timestamp()
                        pipe.zadd(f"{self.queue_name}:retry_queue", {message_id: next_retry_timestamp})
                        pipe.execute()
        
        except Exception as e:
            logger.error(f"Failed to update retry info for message {message_id}: {e}")
    
    def _default_retry_logic(self, message: Dict[str, Any]) -> bool:
        """
        Default retry logic - override this or register specific handlers
        
        Args:
            message (Dict[str, Any]): Message data
            
        Returns:
            bool: True if retry was successful, False otherwise
        """
        # Default implementation - just log and return success
        # In practice, this would republish to the original queue/topic
        logger.info(f"Default retry for message: {message}")
        return True
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the dead letter queue"""
        stats = {
            'fallback_queue_size': len(self.fallback_queue),
            'redis_queue_size': 0,
            'total_handlers': len(self.retry_handlers),
            'queue_name': self.queue_name,
            'max_retries': self.max_retries,
            'retry_delay_minutes': self.retry_delay_minutes
        }
        
        try:
            if redis_circuit_breaker.is_operational():
                stats['redis_queue_size'] = redis_client.zcard(f"{self.queue_name}:retry_queue")
        except Exception as e:
            logger.warning(f"Failed to get Redis queue size: {e}")
        
        return stats
    
    def clear_queue(self, force: bool = False) -> Dict[str, int]:
        """Clear all messages from the queue"""
        if not force:
            raise ValueError("clear_queue requires force=True to prevent accidental data loss")
        
        cleared = {'redis': 0, 'fallback': 0}
        
        # Clear fallback queue
        cleared['fallback'] = len(self.fallback_queue)
        self.fallback_queue.clear()
        
        # Clear Redis queues
        try:
            if redis_circuit_breaker.is_operational():
                with redis_client.pipeline() as pipe:
                    pipe.multi()
                    cleared['redis'] = redis_client.zcard(f"{self.queue_name}:retry_queue")
                    pipe.delete(f"{self.queue_name}:retry_queue")
                    pipe.delete(f"{self.queue_name}:messages")
                    pipe.execute()
        except Exception as e:
            logger.error(f"Failed to clear Redis queues: {e}")
        
        logger.info(f"Cleared DLQ: {cleared}")
        return cleared

