"""
Utility Package for CPA WorkflowPilot
Common utility functions and helpers.

UPDATED: Now uses consolidated utilities to eliminate duplication.
"""

# Import from consolidated utilities (eliminates duplication)
from .consolidated import (
    get_session_firm_id,
    get_session_user_id,
    generate_access_code,
    format_currency,
    format_date,
    calculate_business_days,
    create_activity_log  # Backwards compatibility
)

# Import remaining core utilities that aren't duplicated
from .core import (
    process_recurring_tasks,
    calculate_next_due_date,
    calculate_task_due_date,
    find_or_create_client
)

# Import health checks
from .health_checks import check_system_health

__all__ = [
    # Session management (consolidated)
    'get_session_firm_id',
    'get_session_user_id',
    
    # Security (consolidated)
    'generate_access_code',
    
    # Date/time utilities (consolidated)
    'format_currency',
    'format_date', 
    'calculate_business_days',
    
    # Legacy/compatibility (consolidated)
    'create_activity_log',
    
    # Core utilities (not duplicated)
    'process_recurring_tasks',
    'calculate_next_due_date',
    'calculate_task_due_date',
    'find_or_create_client',
    
    # Health monitoring
    'check_system_health'
]
