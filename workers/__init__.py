"""
Workers Module for CPA WorkflowPilot
Background task workers for different categories of work.
"""

# Import all worker modules to register tasks
from . import ai_worker
from . import document_worker
from . import notification_worker
from . import system_worker

__all__ = [
    'ai_worker',
    'document_worker', 
    'notification_worker',
    'system_worker'
]
