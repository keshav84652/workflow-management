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
    calculate_business_days,
)

# NOTE: Service functions moved to their respective services
# Use service instances directly instead of utility wrappers

# Import health checks
from .health_checks import check_system_health

__all__ = [
    # Session management
    'get_session_firm_id',
    'get_session_user_id',
    
    # Security
    'generate_access_code',
    
    # Date/time utilities
    'calculate_business_days',
    
    # Health monitoring
    'check_system_health'
]
