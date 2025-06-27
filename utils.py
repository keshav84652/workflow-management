import secrets
import string
from flask import session, request

def generate_access_code(length=12):
    """Generate a random access code for authentication purposes"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

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

# No more backward compatibility wrappers!
# All code should use service instances directly for clean architecture