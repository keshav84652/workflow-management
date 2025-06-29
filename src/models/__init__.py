"""
Models package for CPA WorkflowPilot
Organized database models by functional area
"""

from .auth import Firm, User, ActivityLog
from .projects import Project, Template, TemplateTask, WorkType, TaskStatus
from .tasks import Task, TaskComment
from .clients import Client, Contact, ClientContact
from .documents import (
    Attachment, DocumentChecklist, ChecklistItem, ClientDocument,
    DocumentTemplate, DocumentTemplateItem, IncomeWorksheet
)
# Import from new modular locations
from ..modules.auth.models import ClientUser, DemoAccessRequest
from ..modules.document.models import ClientChecklistAccess

# Export all models for backwards compatibility
__all__ = [
    # Auth models
    'Firm', 'User', 'ActivityLog',
    
    # Project models
    'Project', 'Template', 'TemplateTask', 'WorkType', 'TaskStatus',
    
    # Task models
    'Task', 'TaskComment',
    
    # Client models
    'Client', 'Contact', 'ClientContact',
    
    # Document models
    'Attachment', 'DocumentChecklist', 'ChecklistItem', 'ClientDocument',
    'DocumentTemplate', 'DocumentTemplateItem', 'IncomeWorksheet',
    
    # Miscellaneous models
    'ClientUser', 'DemoAccessRequest', 'ClientChecklistAccess'
]