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

# Wrapper functions for backward compatibility
# These functions now delegate to the appropriate services

def create_activity_log(action, user_id, project_id=None, task_id=None, details=None):
    """
    DEPRECATED: Use ActivityService.create_activity_log() directly
    This wrapper is provided for backward compatibility only
    """
    from services.activity_service import ActivityService
    ActivityService.create_activity_log(action, user_id, project_id, task_id, details)

def calculate_task_due_date(project_start_date, template_task):
    """
    DEPRECATED: Use TaskService.calculate_task_due_date() directly
    This wrapper is provided for backward compatibility only
    """
    from services.task_service import TaskService
    return TaskService.calculate_task_due_date(project_start_date, template_task)

def find_or_create_client(client_name, firm_id):
    """
    DEPRECATED: Use ClientService.find_or_create_client() directly
    This wrapper is provided for backward compatibility only
    """
    from services.client_service import ClientService
    return ClientService.find_or_create_client(client_name, firm_id)

def calculate_next_due_date(recurrence_rule, base_date=None):
    """
    DEPRECATED: Use TaskService.calculate_next_due_date() directly
    This wrapper is provided for backward compatibility only
    """
    from services.task_service import TaskService
    return TaskService.calculate_next_due_date(recurrence_rule, base_date)

def process_recurring_tasks():
    """
    DEPRECATED: Use TaskService.process_recurring_tasks() directly
    This wrapper is provided for backward compatibility only
    """
    from services.task_service import TaskService
    return TaskService.process_recurring_tasks()