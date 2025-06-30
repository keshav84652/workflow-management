"""
Models package for CPA WorkflowPilot
Organized database models by functional area
"""

# DEPRECATED: This module is being phased out as part of the modular architecture migration
# New models should be imported directly from their respective module locations:
# - src.modules.project.models for Project, Task, WorkType, TaskStatus, Template, TemplateTask
# - src.modules.client.models for Client, Contact, ClientContact
# - src.modules.document.models for document-related models
# - src.modules.auth.models for authentication models

# Legacy imports for backward compatibility (WILL BE REMOVED)
from .auth import Firm, User, ActivityLog

# Import from new modular locations
from ..modules.project.models import Project, Template, TemplateTask, WorkType, TaskStatus, Task, TaskComment
from ..modules.client.models import Client, Contact, ClientContact
from ..modules.document.models import (
    Attachment, DocumentChecklist, ChecklistItem, ClientDocument,
    DocumentTemplate, DocumentTemplateItem, IncomeWorksheet
)
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