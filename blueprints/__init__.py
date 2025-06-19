"""
Blueprint package for CPA WorkflowPilot
Organized route handling by functional area
"""

from .auth import auth_bp
from .admin import admin_bp
from .dashboard import dashboard_bp
from .projects import projects_bp
from .tasks import tasks_bp
from .clients import clients_bp
from .contacts import contacts_bp
from .users import users_bp
from .views import views_bp
from .documents import documents_bp
from .client_portal import client_portal_bp
from .export import export_bp
from .api import api_bp
from .attachments import attachments_bp
from .subtasks import subtasks_bp
from .ai import ai_bp

# List of all blueprints for easy registration
ALL_BLUEPRINTS = [
    auth_bp,
    admin_bp, 
    dashboard_bp,
    projects_bp,
    tasks_bp,
    clients_bp,
    contacts_bp,
    users_bp,
    views_bp,
    documents_bp,
    client_portal_bp,
    export_bp,
    api_bp,
    attachments_bp,
    subtasks_bp,
    ai_bp
]
