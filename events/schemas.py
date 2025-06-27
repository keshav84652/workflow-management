"""
Event Schemas for CPA WorkflowPilot
Event definitions for core business events.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List

class ClientCreatedEvent:
    """Event fired when a new client is created"""
    def __init__(self, client_id: int, firm_id: int, name: str, is_active: bool):
        self.client_id = client_id
        self.firm_id = firm_id
        self.name = name
        self.is_active = is_active

        # Event metadata
        import uuid
        from datetime import datetime
        self.event_id = str(uuid.uuid4())
        self.event_type = self.__class__.__name__
        self.timestamp = datetime.utcnow()
        self.version = "1.0"
        self.source_system = "workflow-management"

    def get_payload(self) -> Dict[str, Any]:
        return {
            'client_id': self.client_id,
            'firm_id': self.firm_id,
            'name': self.name,
            'is_active': self.is_active
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'version': self.version,
            'firm_id': self.firm_id,
            'source_system': self.source_system,
            'payload': self.get_payload()
        }


class ClientUpdatedEvent:
    """Event fired when a client is updated"""
    def __init__(self, client_id: int, firm_id: int, name: str, is_active: bool):
        self.client_id = client_id
        self.firm_id = firm_id
        self.name = name
        self.is_active = is_active

        # Event metadata
        import uuid
        from datetime import datetime
        self.event_id = str(uuid.uuid4())
        self.event_type = self.__class__.__name__
        self.timestamp = datetime.utcnow()
        self.version = "1.0"
        self.source_system = "workflow-management"

    def get_payload(self) -> Dict[str, Any]:
        return {
            'client_id': self.client_id,
            'firm_id': self.firm_id,
            'name': self.name,
            'is_active': self.is_active
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'version': self.version,
            'firm_id': self.firm_id,
            'source_system': self.source_system,
            'payload': self.get_payload()
        }


class TaskCreatedEvent:
    """Event fired when a new task is created"""
    
    def __init__(self, task_id: int, task_title: str, priority: str = "Medium", 
                 project_id: Optional[int] = None, assigned_to: Optional[int] = None, 
                 due_date: Optional[datetime] = None, firm_id: Optional[int] = None, 
                 user_id: Optional[int] = None):
        self.task_id = task_id
        self.task_title = task_title
        self.priority = priority
        self.project_id = project_id
        self.assigned_to = assigned_to
        self.due_date = due_date
        self.firm_id = firm_id
        self.user_id = user_id
        
        # Event metadata
        import uuid
        self.event_id = str(uuid.uuid4())
        self.event_type = self.__class__.__name__
        self.timestamp = datetime.utcnow()
        self.version = "1.0"
        self.source_system = "workflow-management"
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'task_title': self.task_title,
            'project_id': self.project_id,
            'assigned_to': self.assigned_to,
            'priority': self.priority,
            'due_date': self.due_date.isoformat() if self.due_date else None
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary format for serialization"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'version': self.version,
            'firm_id': self.firm_id,
            'user_id': self.user_id,
            'source_system': self.source_system,
            'payload': self.get_payload()
        }


class TaskUpdatedEvent:
    """Event fired when a task is updated"""
    
    def __init__(self, task_id: int, task_title: str, changes: Dict[str, Any],
                 priority: str = "Medium", project_id: Optional[int] = None, 
                 assigned_to: Optional[int] = None, due_date: Optional[datetime] = None,
                 firm_id: Optional[int] = None, user_id: Optional[int] = None):
        self.task_id = task_id
        self.task_title = task_title
        self.changes = changes
        self.priority = priority
        self.project_id = project_id
        self.assigned_to = assigned_to
        self.due_date = due_date
        self.firm_id = firm_id
        self.user_id = user_id
        
        # Event metadata
        import uuid
        self.event_id = str(uuid.uuid4())
        self.event_type = self.__class__.__name__
        self.timestamp = datetime.utcnow()
        self.version = "1.0"
        self.source_system = "workflow-management"
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'task_title': self.task_title,
            'changes': self.changes,
            'project_id': self.project_id,
            'assigned_to': self.assigned_to,
            'priority': self.priority,
            'due_date': self.due_date.isoformat() if self.due_date else None
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'version': self.version,
            'firm_id': self.firm_id,
            'user_id': self.user_id,
            'source_system': self.source_system,
            'payload': self.get_payload()
        }


class TaskStatusChangedEvent:
    """Event fired when a task status changes"""
    
    def __init__(self, task_id: int, task_title: str, old_status: str, new_status: str,
                 priority: str = "Medium", project_id: Optional[int] = None, 
                 assigned_to: Optional[int] = None, firm_id: Optional[int] = None, 
                 user_id: Optional[int] = None):
        self.task_id = task_id
        self.task_title = task_title
        self.old_status = old_status
        self.new_status = new_status
        self.priority = priority
        self.project_id = project_id
        self.assigned_to = assigned_to
        self.firm_id = firm_id
        self.user_id = user_id
        
        # Event metadata
        import uuid
        self.event_id = str(uuid.uuid4())
        self.event_type = self.__class__.__name__
        self.timestamp = datetime.utcnow()
        self.version = "1.0"
        self.source_system = "workflow-management"
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'task_title': self.task_title,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'project_id': self.project_id,
            'assigned_to': self.assigned_to,
            'priority': self.priority
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'version': self.version,
            'firm_id': self.firm_id,
            'user_id': self.user_id,
            'source_system': self.source_system,
            'payload': self.get_payload()
        }


class DocumentAnalysisStartedEvent:
    """Event fired when AI document analysis is started"""
    
    def __init__(self, document_id: int, document_name: str, file_type: str,
                 checklist_id: Optional[int] = None, analysis_service: str = "unknown",
                 firm_id: Optional[int] = None, user_id: Optional[int] = None):
        self.document_id = document_id
        self.document_name = document_name
        self.file_type = file_type
        self.checklist_id = checklist_id
        self.analysis_service = analysis_service
        self.firm_id = firm_id
        self.user_id = user_id
        
        # Event metadata
        import uuid
        self.event_id = str(uuid.uuid4())
        self.event_type = self.__class__.__name__
        self.timestamp = datetime.utcnow()
        self.version = "1.0"
        self.source_system = "workflow-management"
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'document_id': self.document_id,
            'document_name': self.document_name,
            'file_type': self.file_type,
            'checklist_id': self.checklist_id,
            'analysis_service': self.analysis_service
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'version': self.version,
            'firm_id': self.firm_id,
            'user_id': self.user_id,
            'source_system': self.source_system,
            'payload': self.get_payload()
        }


class DocumentAnalysisCompletedEvent:
    """Event fired when AI document analysis is completed"""
    
    def __init__(self, document_id: int, document_name: str, analysis_results: Dict[str, Any],
                 confidence_score: float, document_type: str, processing_time_ms: Optional[float] = None,
                 firm_id: Optional[int] = None, user_id: Optional[int] = None):
        self.document_id = document_id
        self.document_name = document_name
        self.analysis_results = analysis_results
        self.confidence_score = confidence_score
        self.document_type = document_type
        self.processing_time_ms = processing_time_ms
        self.firm_id = firm_id
        self.user_id = user_id
        
        # Event metadata
        import uuid
        self.event_id = str(uuid.uuid4())
        self.event_type = self.__class__.__name__
        self.timestamp = datetime.utcnow()
        self.version = "1.0"
        self.source_system = "workflow-management"
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'document_id': self.document_id,
            'document_name': self.document_name,
            'analysis_results': self.analysis_results,
            'confidence_score': self.confidence_score,
            'document_type': self.document_type,
            'processing_time_ms': self.processing_time_ms
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'version': self.version,
            'firm_id': self.firm_id,
            'user_id': self.user_id,
            'source_system': self.source_system,
            'payload': self.get_payload()
        }


class DocumentAnalysisFailedEvent:
    """Event fired when AI document analysis fails"""
    
    def __init__(self, document_id: int, document_name: str, error_message: str, 
                 error_type: str, retry_count: int = 0, firm_id: Optional[int] = None, 
                 user_id: Optional[int] = None):
        self.document_id = document_id
        self.document_name = document_name
        self.error_message = error_message
        self.error_type = error_type
        self.retry_count = retry_count
        self.firm_id = firm_id
        self.user_id = user_id
        
        # Event metadata
        import uuid
        self.event_id = str(uuid.uuid4())
        self.event_type = self.__class__.__name__
        self.timestamp = datetime.utcnow()
        self.version = "1.0"
        self.source_system = "workflow-management"
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'document_id': self.document_id,
            'document_name': self.document_name,
            'error_message': self.error_message,
            'error_type': self.error_type,
            'retry_count': self.retry_count
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'version': self.version,
            'firm_id': self.firm_id,
            'user_id': self.user_id,
            'source_system': self.source_system,
            'payload': self.get_payload()
        }


class TaskDeletedEvent:
    """Event fired when a task is deleted"""
    
    def __init__(self, task_id: int, task_title: str, priority: str = "Medium", 
                 project_id: Optional[int] = None, assigned_to: Optional[int] = None, 
                 firm_id: Optional[int] = None, user_id: Optional[int] = None):
        self.task_id = task_id
        self.task_title = task_title
        self.priority = priority
        self.project_id = project_id
        self.assigned_to = assigned_to
        self.firm_id = firm_id
        self.user_id = user_id
        
        # Event metadata
        import uuid
        self.event_id = str(uuid.uuid4())
        self.event_type = self.__class__.__name__
        self.timestamp = datetime.utcnow()
        self.version = "1.0"
        self.source_system = "workflow-management"
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'task_title': self.task_title,
            'project_id': self.project_id,
            'assigned_to': self.assigned_to,
            'priority': self.priority
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'version': self.version,
            'firm_id': self.firm_id,
            'user_id': self.user_id,
            'source_system': self.source_system,
            'payload': self.get_payload()
        }


class ErrorEvent:
    """Event fired when system errors occur"""
    
    def __init__(self, error_type: str, error_message: str, stack_trace: Optional[str] = None, 
                 context: Optional[Dict[str, Any]] = None, firm_id: Optional[int] = None, 
                 user_id: Optional[int] = None):
        self.error_type = error_type
        self.error_message = error_message
        self.stack_trace = stack_trace
        self.context = context or {}
        self.firm_id = firm_id
        self.user_id = user_id
        
        # Event metadata
        import uuid
        self.event_id = str(uuid.uuid4())
        self.event_type = self.__class__.__name__
        self.timestamp = datetime.utcnow()
        self.version = "1.0"
        self.source_system = "workflow-management"
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'error_type': self.error_type,
            'error_message': self.error_message,
            'stack_trace': self.stack_trace,
            'context': self.context
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'version': self.version,
            'firm_id': self.firm_id,
            'user_id': self.user_id,
            'source_system': self.source_system,
            'payload': self.get_payload()
        }
class DocumentCreatedEvent:
    """Event fired when a new document is created"""
    def __init__(self, document_id: int, firm_id: int, name: str, status: str):
        self.document_id = document_id
        self.firm_id = firm_id
        self.name = name
        self.status = status

        # Event metadata
        import uuid
        from datetime import datetime
        self.event_id = str(uuid.uuid4())
        self.event_type = self.__class__.__name__
        self.timestamp = datetime.utcnow()
        self.version = "1.0"
        self.source_system = "workflow-management"

    def get_payload(self) -> dict:
        return {
            'document_id': self.document_id,
            'firm_id': self.firm_id,
            'name': self.name,
            'status': self.status
        }

    def to_dict(self) -> dict:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'version': self.version,
            'firm_id': self.firm_id,
            'source_system': self.source_system,
            'payload': self.get_payload()
        }


class DocumentUpdatedEvent:
    """Event fired when a document is updated"""
    def __init__(self, document_id: int, firm_id: int, name: str, status: str):
        self.document_id = document_id
        self.firm_id = firm_id
        self.name = name
        self.status = status

        # Event metadata
        import uuid
        from datetime import datetime
        self.event_id = str(uuid.uuid4())
        self.event_type = self.__class__.__name__
        self.timestamp = datetime.utcnow()
        self.version = "1.0"
        self.source_system = "workflow-management"

    def get_payload(self) -> dict:
        return {
            'document_id': self.document_id,
            'firm_id': self.firm_id,
            'name': self.name,
            'status': self.status
        }

    def to_dict(self) -> dict:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'version': self.version,
            'firm_id': self.firm_id,
            'source_system': self.source_system,
            'payload': self.get_payload()
        }
