"""
Utility Package for CPA WorkflowPilot
Common utility functions and helpers.

UPDATED: Now uses consolidated utilities to eliminate duplication.
"""

# Import from consolidated utilities (clean architecture)
from .consolidated import (
    get_session_firm_id,
    get_session_user_id,
    generate_access_code,
)

# NOTE: Service functions moved to their respective services
# Use service instances directly instead of utility wrappers

# Import health checks
from .health_checks import check_system_health

# Import simplified error handling (replaces complex circuit breakers)
from .simple_error_handling import (
    safe_execute,
    with_simple_retry,
    log_and_continue,
    with_fallback_cache,
    handle_service_unavailable
)

__all__ = [
    # Session management
    'get_session_firm_id',
    'get_session_user_id',
    
    # Security
    'generate_access_code',
    
    # Health monitoring
    'check_system_health',
    
    # Simplified error handling
    'safe_execute',
    'with_simple_retry', 
    'log_and_continue',
    'with_fallback_cache',
    'handle_service_unavailable'
]
