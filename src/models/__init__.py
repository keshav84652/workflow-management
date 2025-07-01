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

# Import essential models for backwards compatibility
# Using try/except to handle missing modules gracefully

try:
    from ..modules.project.models import Project, Template, TemplateTask, WorkType, TaskStatus, Task, TaskComment
except ImportError as e:
    print(f"Warning: Could not import project models: {e}")
    # Create placeholder classes to prevent import errors
    class Project: pass
    class Template: pass
    class TemplateTask: pass
    class WorkType: pass
    class TaskStatus: pass
    class Task: pass
    class TaskComment: pass

try:
    from ..modules.client.models import Client, Contact, ClientContact
except ImportError as e:
    print(f"Warning: Could not import client models: {e}")
    class Client: pass
    class Contact: pass
    class ClientContact: pass

try:
    from ..modules.document.models import (
        Attachment, DocumentChecklist, ChecklistItem, ClientDocument,
        DocumentTemplate, DocumentTemplateItem, IncomeWorksheet
    )
except ImportError as e:
    print(f"Warning: Could not import document models: {e}")
    class Attachment: pass
    class DocumentChecklist: pass
    class ChecklistItem: pass
    class ClientDocument: pass
    class DocumentTemplate: pass
    class DocumentTemplateItem: pass
    class IncomeWorksheet: pass

try:
    from ..modules.auth.models import ClientUser, DemoAccessRequest
    try:
        from ..modules.document.models import ClientChecklistAccess
    except ImportError:
        class ClientChecklistAccess: pass
except ImportError as e:
    print(f"Warning: Could not import auth models: {e}")
    class ClientUser: pass
    class DemoAccessRequest: pass
    class ClientChecklistAccess: pass

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