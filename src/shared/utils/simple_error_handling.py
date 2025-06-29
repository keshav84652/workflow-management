"""
Simplified Error Handling Utilities for CPA WorkflowPilot

This replaces the over-engineered circuit breakers and dead letter queue
with simple, practical error handling suitable for the current application scale.
"""

import logging
import functools
import time
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


def safe_execute(func: Callable, 
                 fallback: Any = None,
                 log_errors: bool = True) -> Any:
    """
    Safely execute a function with optional fallback.
    
    Args:
        func: Function to execute
        fallback: Value to return if function fails
        log_errors: Whether to log errors
    
    Returns:
        Function result or fallback value
    """
    try:
        return func()
    except Exception as e:
        if log_errors:
            logger.warning(f"Safe execution failed for {func.__name__}: {e}")
        return fallback


def with_simple_retry(max_attempts: int = 3, delay: float = 1.0):
    """
    Simple retry decorator for functions that may fail temporarily.
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Delay between attempts in seconds
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        logger.error(f"Function {func.__name__} failed after {max_attempts} attempts: {e}")
                        raise e
                    
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {delay}s")
                    time.sleep(delay)
            
            raise last_exception
        return wrapper
    return decorator


def log_and_continue(operation: str):
    """
    Decorator that logs errors but continues execution.
    Useful for non-critical operations that shouldn't break the flow.
    
    Args:
        operation: Description of the operation for logging
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Non-critical operation '{operation}' failed: {e}")
                return None
        return wrapper
    return decorator


class SimpleCache:
    """
    Simple in-memory cache for fallback values.
    Replaces the complex Redis-based fallback system for basic needs.
    """
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        """
        Initialize simple cache.
        
        Args:
            default_ttl: Default time-to-live in seconds
        """
        self._cache = {}
        self._timestamps = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache if not expired"""
        if key not in self._cache:
            return default
        
        # Check if expired
        if time.time() - self._timestamps[key] > self.default_ttl:
            self.remove(key)
            return default
        
        return self._cache[key]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache with optional TTL"""
        self._cache[key] = value
        self._timestamps[key] = time.time()
    
    def remove(self, key: str):
        """Remove value from cache"""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
    
    def clear(self):
        """Clear all cached values"""
        self._cache.clear()
        self._timestamps.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        return len(self._cache)


# Global simple cache instance for fallback values
fallback_cache = SimpleCache()


def with_fallback_cache(cache_key: str, ttl: int = 300):
    """
    Decorator that caches successful results and returns cached values on failure.
    
    Args:
        cache_key: Key to use for caching
        ttl: Time-to-live for cached values in seconds
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                # Cache successful result
                fallback_cache.set(cache_key, result, ttl)
                return result
            except Exception as e:
                logger.warning(f"Function {func.__name__} failed: {e}. Attempting to use cached fallback.")
                cached_result = fallback_cache.get(cache_key)
                if cached_result is not None:
                    logger.info(f"Using cached fallback for {func.__name__}")
                    return cached_result
                else:
                    logger.error(f"No cached fallback available for {func.__name__}")
                    raise e
        return wrapper
    return decorator


def handle_service_unavailable(service_name: str, fallback_action: Optional[Callable] = None):
    """
    Simple service unavailability handler.
    
    Args:
        service_name: Name of the service
        fallback_action: Optional fallback function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Service '{service_name}' unavailable: {e}")
                
                if fallback_action:
                    try:
                        logger.info(f"Executing fallback action for {service_name}")
                        return fallback_action(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"Fallback action for {service_name} also failed: {fallback_error}")
                
                # Re-raise original exception if no fallback or fallback failed
                raise e
        return wrapper
    return decorator