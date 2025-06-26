"""
Error Handling Utilities for CPA WorkflowPilot
Provides circuit breakers, retry logic, and error recovery mechanisms.
"""

import time
import logging
import functools
from typing import Any, Callable, Dict, Optional, Union
from datetime import datetime, timedelta
from enum import Enum


logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker implementation for external service calls.
    Prevents cascading failures by temporarily blocking calls to failing services.
    """
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: tuple = (Exception,)):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exceptions that count as failures
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker entering HALF_OPEN state for {func.__name__}")
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN for {func.__name__}. "
                    f"Next attempt in {self._time_until_reset():.1f}s"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _time_until_reset(self) -> float:
        """Calculate seconds until next reset attempt."""
        if self.last_failure_time is None:
            return 0
        elapsed = time.time() - self.last_failure_time
        return max(0, self.recovery_timeout - elapsed)
    
    def _on_success(self):
        """Handle successful function call."""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info("Circuit breaker reset to CLOSED state")
    
    def _on_failure(self):
        """Handle failed function call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")
    
    def __call__(self, func: Callable) -> Callable:
        """Make CircuitBreaker usable as a decorator."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class RetryConfig:
    """Configuration for retry logic."""
    
    def __init__(self,
                 max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0,
                 jitter: bool = True):
        """
        Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Initial delay between retries (seconds)
            max_delay: Maximum delay between retries (seconds)
            exponential_base: Base for exponential backoff
            jitter: Add random jitter to prevent thundering herd
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


def with_retry(config: RetryConfig = None, 
               exceptions: tuple = (Exception,)):
    """
    Decorator for adding retry logic with exponential backoff.
    
    Args:
        config: Retry configuration
        exceptions: Exceptions that should trigger retry
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts - 1:
                        # Last attempt failed, re-raise
                        logger.error(f"Function {func.__name__} failed after {config.max_attempts} attempts: {e}")
                        raise e
                    
                    # Calculate delay for next attempt
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    
                    if config.jitter:
                        import random
                        delay *= (0.5 + random.random() * 0.5)  # 50-100% of calculated delay
                    
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                                 f"Retrying in {delay:.2f}s")
                    time.sleep(delay)
            
            # Should never reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator


class ErrorContext:
    """
    Preserves error context across retries and provides debugging information.
    """
    
    def __init__(self, operation: str, **metadata):
        """
        Initialize error context.
        
        Args:
            operation: Description of the operation being performed
            **metadata: Additional context information
        """
        self.operation = operation
        self.metadata = metadata
        self.attempts = []
        self.start_time = time.time()
    
    def add_attempt(self, exception: Exception, attempt_number: int):
        """Record a failed attempt."""
        self.attempts.append({
            'attempt': attempt_number,
            'exception': str(exception),
            'exception_type': type(exception).__name__,
            'timestamp': datetime.now().isoformat(),
            'elapsed_time': time.time() - self.start_time
        })
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of error context for logging."""
        return {
            'operation': self.operation,
            'metadata': self.metadata,
            'total_attempts': len(self.attempts),
            'total_duration': time.time() - self.start_time,
            'attempts': self.attempts
        }


def with_error_context(operation: str, **metadata):
    """
    Decorator to add error context preservation.
    
    Args:
        operation: Description of the operation
        **metadata: Additional context metadata
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            context = ErrorContext(operation, **metadata)
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                context.add_attempt(e, 1)
                
                # Attach context to exception for debugging
                if not hasattr(e, 'error_context'):
                    e.error_context = context.get_context_summary()
                
                logger.error(f"Operation failed: {operation}", extra={
                    'error_context': context.get_context_summary(),
                    'exception': str(e)
                })
                raise e
        
        return wrapper
    return decorator


class GracefulDegradation:
    """
    Provides fallback mechanisms when services are unavailable.
    """
    
    @staticmethod
    def fallback_cache(cache_key: str, fallback_value: Any = None) -> Any:
        """
        Provide cached value as fallback.
        
        Args:
            cache_key: Key to look up in fallback cache
            fallback_value: Default value if no cache entry exists
        """
        # In a real implementation, this would use a persistent cache
        # For now, we'll use a simple in-memory fallback
        from core.redis_client import redis_client
        
        try:
            if redis_client and redis_client.is_available():
                cached = redis_client.get_client().get(f"fallback:{cache_key}")
                if cached:
                    import json
                    return json.loads(cached)
        except Exception as e:
            logger.warning(f"Failed to retrieve fallback cache for {cache_key}: {e}")
        
        return fallback_value
    
    @staticmethod
    def handle_service_failure(service_name: str, error: Exception, fallback_action: Callable = None) -> Any:
        """
        Handle service failure with appropriate fallback.
        
        Args:
            service_name: Name of the failing service
            error: The exception that occurred
            fallback_action: Optional fallback function to execute
        """
        logger.warning(f"Service {service_name} failed: {error}")
        
        if fallback_action:
            try:
                return fallback_action()
            except Exception as fallback_error:
                logger.error(f"Fallback action for {service_name} also failed: {fallback_error}")
        
        return None
    
    @staticmethod
    def store_fallback_cache(cache_key: str, value: Any, ttl: int = 3600):
        """
        Store value in fallback cache.
        
        Args:
            cache_key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        from core.redis_client import redis_client
        
        try:
            if redis_client and redis_client.is_available():
                import json
                redis_client.get_client().setex(
                    f"fallback:{cache_key}",
                    ttl,
                    json.dumps(value)
                )
        except Exception as e:
            logger.warning(f"Failed to store fallback cache for {cache_key}: {e}")


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


# Circuit breakers for common services
redis_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=30,
    expected_exception=(ConnectionError, TimeoutError, Exception)
)

ai_services_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=120,
    expected_exception=(ConnectionError, TimeoutError, Exception)
)

database_circuit_breaker = CircuitBreaker(
    failure_threshold=2,
    recovery_timeout=60,
    expected_exception=(Exception,)
)


# Predefined retry configurations
REDIS_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=0.5,
    max_delay=5.0
)

AI_SERVICES_RETRY_CONFIG = RetryConfig(
    max_attempts=2,
    base_delay=2.0,
    max_delay=30.0
)

DATABASE_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=10.0
)
