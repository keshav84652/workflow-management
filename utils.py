import secrets
import string

def generate_access_code(length=12):
    """Generate a random access code for authentication purposes"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

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

def process_recurring_tasks():
    """
    DEPRECATED: Use TaskService.process_recurring_tasks() directly
    This wrapper is provided for backward compatibility only
    """
    from services.task_service import TaskService
    return TaskService.process_recurring_tasks()