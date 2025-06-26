"""
Consolidated Utilities for CPA WorkflowPilot
Central location for all utility functions to eliminate duplication.
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from flask import session, request


# ===== SESSION MANAGEMENT =====

def get_session_firm_id() -> int:
    """
    Safely get firm_id from session with proper error handling
    Returns firm_id if found, raises descriptive error if session is invalid
    """
    if 'firm_id' not in session:
        # More descriptive error for debugging
        available_keys = list(session.keys())
        raise ValueError(f"No firm_id in session. Available session keys: {available_keys}. "
                        f"User may need to log in again. Request path: {request.path}")
    return session['firm_id']


def get_session_user_id() -> int:
    """
    Safely get user_id from session with proper error handling
    Returns user_id if found, raises descriptive error if session is invalid
    """
    if 'user_id' not in session:
        available_keys = list(session.keys())
        raise ValueError(f"No user_id in session. Available session keys: {available_keys}. "
                        f"User may need to log in again. Request path: {request.path}")
    return session['user_id']


# ===== SECURITY =====

def generate_access_code(length: int = 12) -> str:
    """
    Generate a cryptographically secure random access code
    Uses secrets module for security-critical applications
    
    Args:
        length: Length of the access code (default: 12)
        
    Returns:
        Secure random string of uppercase letters and digits
    """
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


# ===== DATE/TIME UTILITIES =====

def format_currency(amount: float) -> str:
    """Format currency amount to string with dollar sign and commas"""
    return f"${amount:,.2f}"


def format_date(date_obj: datetime) -> str:
    """Format datetime object to readable string"""
    if date_obj is None:
        return ""
    return date_obj.strftime("%Y-%m-%d")


def calculate_business_days(start_date: datetime, end_date: datetime) -> int:
    """Calculate number of business days between two dates"""
    if start_date > end_date:
        return 0
    
    business_days = 0
    current_date = start_date
    
    while current_date <= end_date:
        # Monday = 0, Sunday = 6
        if current_date.weekday() < 5:  # Monday to Friday
            business_days += 1
        current_date += timedelta(days=1)
    
    return business_days


# ===== SERVICE DELEGATION =====
# Modern approach: Direct service calls instead of utility wrappers

def create_activity_log(action: str, user_id: Optional[int] = None, 
                       project_id: Optional[int] = None, 
                       task_id: Optional[int] = None) -> None:
    """
    RECOMMENDED: Use ActivityService.create_activity_log() directly
    This utility is provided for convenience but direct service calls are preferred
    """
    from services.activity_service import ActivityService
    ActivityService.create_activity_log(action, user_id, project_id, task_id)


# ===== BACKWARDS COMPATIBILITY =====
# Re-export commonly used functions for smooth transition

__all__ = [
    # Session management
    'get_session_firm_id',
    'get_session_user_id',
    
    # Security
    'generate_access_code',
    
    # Date/time
    'format_currency', 
    'format_date',
    'calculate_business_days',
    
    # Activity logging (deprecated pattern)
    'create_activity_log',
]