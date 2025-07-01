"""
Redis Connection Management for CPA WorkflowPilot
Provides centralized Redis connection and configuration management.
"""

import redis
import logging
from typing import Optional
from functools import wraps
import json

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis connection manager with connection pooling and error handling"""
    
    def __init__(self, config=None):
        """
        Initialize Redis client with configuration
        
        Args:
            config: Flask app config object or dict with Redis settings
        """
        self.config = config or {}
        self._client = None
        self._pool = None
        
        # Redis configuration with defaults
        self.redis_config = {
            'host': self.config.get('REDIS_HOST', 'localhost'),
            'port': self.config.get('REDIS_PORT', 6379),
            'db': self.config.get('REDIS_DB', 0),
            'password': self.config.get('REDIS_PASSWORD'),
            'decode_responses': True,
            'max_connections': self.config.get('REDIS_MAX_CONNECTIONS', 10),
            'retry_on_timeout': True,
            'socket_timeout': self.config.get('REDIS_SOCKET_TIMEOUT', 5),
            'socket_connect_timeout': self.config.get('REDIS_CONNECT_TIMEOUT', 5),
        }
        
        # Initialize connection pool
        self._init_connection_pool()
    
    def _init_connection_pool(self):
        """Initialize Redis connection pool"""
        try:
            self._pool = redis.ConnectionPool(**self.redis_config)
            self._client = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            self._client.ping()
            logger.info("Redis connection pool initialized successfully")
            
        except redis.ConnectionError as e:
            logger.warning(f"Redis connection failed: {e}. Running in fallback mode.")
            self._client = None
            self._pool = None
        except Exception as e:
            logger.error(f"Unexpected error initializing Redis: {e}")
            self._client = None
            self._pool = None
    
    def is_available(self) -> bool:
        """Check if Redis is available"""
        if not self._client:
            return False
        
        try:
            self._client.ping()
            return True
        except Exception:
            return False
    
    def get_client(self) -> Optional[redis.Redis]:
        """Get Redis client instance"""
        if not self.is_available():
            return None
        return self._client
    
    def health_check(self) -> dict:
        """
        Perform Redis health check
        
        Returns:
            dict: Health status information
        """
        if not self._client:
            return {
                'status': 'unavailable',
                'message': 'Redis client not initialized',
                'connected': False
            }
        
        try:
            # Test basic operations
            ping_result = self._client.ping()
            info = self._client.info()
            
            return {
                'status': 'healthy',
                'connected': True,
                'ping': ping_result,
                'redis_version': info.get('redis_version'),
                'used_memory_human': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'total_commands_processed': info.get('total_commands_processed')
            }
        except Exception as e:
            return {
                'status': 'error',
                'connected': False,
                'error': str(e)
            }
    
    def set(self, key: str, value, ex: Optional[int] = None) -> bool:
        """
        Set a key-value pair in Redis
        
        Args:
            key: Redis key
            value: Value to store (will be JSON serialized if not string)
            ex: Expiration time in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_available():
            logger.warning("Redis not available for SET operation")
            return False
        
        try:
            # Serialize value if it's not a string
            if not isinstance(value, str):
                value = json.dumps(value)
            
            result = self._client.set(key, value, ex=ex)
            return result is True
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    def get(self, key: str):
        """
        Get a value from Redis
        
        Args:
            key: Redis key
            
        Returns:
            Stored value (JSON parsed if applicable) or None
        """
        if not self.is_available():
            return None
        
        try:
            value = self._client.get(key)
            if value is None:
                return None
            
            # Try to parse as JSON, fall back to string
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from Redis
        
        Args:
            key: Redis key to delete
            
        Returns:
            bool: True if key was deleted, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            result = self._client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis
        
        Args:
            key: Redis key to check
            
        Returns:
            bool: True if key exists, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            return self._client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    def publish(self, channel: str, message) -> bool:
        """
        Publish a message to a Redis channel
        
        Args:
            channel: Redis channel name
            message: Message to publish (will be JSON serialized)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_available():
            logger.warning(f"Redis not available for publishing to channel {channel}")
            return False
        
        try:
            # Serialize message if it's not a string
            if not isinstance(message, str):
                message = json.dumps(message)
            
            result = self._client.publish(channel, message)
            return result >= 0
        except Exception as e:
            logger.error(f"Redis PUBLISH error for channel {channel}: {e}")
            return False
    
    def close(self):
        """Close Redis connection pool"""
        if self._pool:
            self._pool.disconnect()
            logger.info("Redis connection pool closed")


def with_redis(fallback_return=None):
    """
    Decorator to handle Redis operations with fallback
    
    Args:
        fallback_return: Value to return if Redis is not available
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not hasattr(self, 'redis_client') or not self.redis_client.is_available():
                logger.warning(f"Redis not available for {func.__name__}, using fallback")
                return fallback_return
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


# Global Redis client instance (initialized by Flask app)
redis_client: Optional[RedisClient] = None


def init_redis(app):
    """
    Initialize Redis client with Flask app configuration
    
    Args:
        app: Flask application instance
    """
    global redis_client
    
    redis_client = RedisClient(app.config)
    
    # Store in app context for easy access
    app.redis_client = redis_client
    
    # Add teardown handler
    @app.teardown_appcontext
    def close_redis(error):
        if redis_client:
            redis_client.close()
    
    logger.info("Redis client initialized for Flask app")
    
    return redis_client
