"""
Session helper functions for CPA WorkflowPilot
Functions to safely access Flask session data.
"""

from flask import session, request


def get_session_firm_id():
    """
    Safely get firm_id from session with proper error handling
    Returns None if not found, raises descriptive error if session is invalid
    """
    if 'firm_id' not in session:
        # More descriptive error for debugging
        available_keys = list(session.keys())
        raise ValueError(f"No firm_id in session. Available session keys: {available_keys}. "
                        f"User may need to log in again. Request path: {request.path}")
    return session['firm_id']


def get_session_user_id():
    """
    Safely get user_id from session with proper error handling
    Returns None if not found, raises descriptive error if session is invalid
    """
    if 'user_id' not in session:
        available_keys = list(session.keys())
        raise ValueError(f"No user_id in session. Available session keys: {available_keys}. "
                        f"User may need to log in again. Request path: {request.path}")
    return session['user_id']