"""
Event Schemas for CPA WorkflowPilot
Event definitions for core business events.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid


class BaseEvent(ABC):
    """Abstract base class for all events"""
    
    def __init__(self, event_type: str, firm_id: Optional[int] = None):
        self.event_id = str(uuid.uuid4())
        self.event_type = event_type
        self.timestamp = datetime.utcnow()
        self.version = "1.0"
        self.source_system = "workflow-management"
        self.firm_id = firm_id
    
    @abstractmethod
    def get_payload(self) -> Dict[str, Any]:
        """Return the event payload data"""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary format for serialization"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'version': self.version,
            'firm_id': self.firm_id,
            'source_system': self.source_system,
            'payload': self.get_payload()
        }
    
    def to_json(self) -> str:
        """Convert event to JSON string for Redis publishing"""
        import json
        return json.dumps(self.to_dict())

class ClientCreatedEvent(BaseEvent):
    """Event fired when a new client is created"""
    def __init__(self, client_id: int, firm_id: int, name: str, is_active: bool):
        super().__init__(event_type=self.__class__.__name__, firm_id=firm_id)
        self.client_id = client_id
        self.name = name
        self.is_active = is_active

    def get_payload(self) -> Dict[str, Any]:
        return {
            'client_id': self.client_id,
            'firm_id': self.firm_id,
            'name': self.name,
            'is_active': self.is_active
        }



class ClientUpdatedEvent(BaseEvent):
    """Event fired when a client is updated"""
    def __init__(self, client_id: int, firm_id: int, name: str, is_active: bool):
        super().__init__(event_type=self.__class__.__name__, firm_id=firm_id)
        self.client_id = client_id
        self.name = name
        self.is_active = is_active

    def get_payload(self) -> Dict[str, Any]:
        return {
            'client_id': self.client_id,
            'firm_id': self.firm_id,
            'name': self.name,
            'is_active': self.is_active
        }



class TaskCreatedEvent(BaseEvent):
    """Event fired when a new task is created"""
    
    def __init__(self, task_id: int, task_title: str, priority: str = "Medium", 
                 project_id: Optional[int] = None, assignee_id: Optional[int] = None, 
                 due_date: Optional[datetime] = None, firm_id: Optional[int] = None, 
                 user_id: Optional[int] = None):
        super().__init__(event_type=self.__class__.__name__, firm_id=firm_id)
        self.task_id = task_id
        self.task_title = task_title
        self.priority = priority
        self.project_id = project_id
        self.assignee_id = assignee_id
        self.due_date = due_date
        self.user_id = user_id
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'task_title': self.task_title,
            'project_id': self.project_id,
            'assignee_id': self.assignee_id,
            'priority': self.priority,
            'due_date': self.due_date.isoformat() if self.due_date else None
        }
    


class TaskUpdatedEvent(BaseEvent):
    """Event fired when a task is updated"""
    
    def __init__(self, task_id: int, task_title: str, changes: Dict[str, Any],
                 priority: str = "Medium", project_id: Optional[int] = None, 
                 assigned_to: Optional[int] = None, due_date: Optional[datetime] = None,
                 firm_id: Optional[int] = None, user_id: Optional[int] = None):
        super().__init__(event_type=self.__class__.__name__, firm_id=firm_id)
        self.task_id = task_id
        self.task_title = task_title
        self.changes = changes
        self.priority = priority
        self.project_id = project_id
        self.assigned_to = assigned_to
        self.due_date = due_date
        self.user_id = user_id
    
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


class TaskStatusChangedEvent(BaseEvent):
    """Event fired when a task status changes"""
    
    def __init__(self, task_id: int, task_title: str, old_status: str, new_status: str,
                 priority: str = "Medium", project_id: Optional[int] = None, 
                 assigned_to: Optional[int] = None, firm_id: Optional[int] = None, 
                 user_id: Optional[int] = None):
        super().__init__(event_type=self.__class__.__name__, firm_id=firm_id)
        self.task_id = task_id
        self.task_title = task_title
        self.old_status = old_status
        self.new_status = new_status
        self.priority = priority
        self.project_id = project_id
        self.assigned_to = assigned_to
        self.user_id = user_id
    
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


class DocumentAnalysisStartedEvent(BaseEvent):
    """Event fired when AI document analysis is started"""
    
    def __init__(self, document_id: int, document_name: str, file_type: str,
                 checklist_id: Optional[int] = None, analysis_service: str = "unknown",
                 firm_id: Optional[int] = None, user_id: Optional[int] = None):
        super().__init__(event_type=self.__class__.__name__, firm_id=firm_id)
        self.document_id = document_id
        self.document_name = document_name
        self.file_type = file_type
        self.checklist_id = checklist_id
        self.analysis_service = analysis_service
        self.user_id = user_id
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'document_id': self.document_id,
            'document_name': self.document_name,
            'file_type': self.file_type,
            'checklist_id': self.checklist_id,
            'analysis_service': self.analysis_service
        }


class DocumentAnalysisCompletedEvent(BaseEvent):
    """Event fired when AI document analysis is completed"""
    
    def __init__(self, document_id: int, document_name: str, analysis_results: Dict[str, Any],
                 confidence_score: float, document_type: str, processing_time_ms: Optional[float] = None,
                 firm_id: Optional[int] = None, user_id: Optional[int] = None):
        super().__init__(event_type=self.__class__.__name__, firm_id=firm_id)
        self.document_id = document_id
        self.document_name = document_name
        self.analysis_results = analysis_results
        self.confidence_score = confidence_score
        self.document_type = document_type
        self.processing_time_ms = processing_time_ms
        self.user_id = user_id
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'document_id': self.document_id,
            'document_name': self.document_name,
            'analysis_results': self.analysis_results,
            'confidence_score': self.confidence_score,
            'document_type': self.document_type,
            'processing_time_ms': self.processing_time_ms
        }


class DocumentAnalysisFailedEvent(BaseEvent):
    """Event fired when AI document analysis fails"""
    
    def __init__(self, document_id: int, document_name: str, error_message: str, 
                 error_type: str, retry_count: int = 0, firm_id: Optional[int] = None, 
                 user_id: Optional[int] = None):
        super().__init__(event_type=self.__class__.__name__, firm_id=firm_id)
        self.document_id = document_id
        self.document_name = document_name
        self.error_message = error_message
        self.error_type = error_type
        self.retry_count = retry_count
        self.user_id = user_id
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'document_id': self.document_id,
            'document_name': self.document_name,
            'error_message': self.error_message,
            'error_type': self.error_type,
            'retry_count': self.retry_count
        }


class TaskDeletedEvent(BaseEvent):
    """Event fired when a task is deleted"""
    
    def __init__(self, task_id: int, task_title: str, priority: str = "Medium", 
                 project_id: Optional[int] = None, assigned_to: Optional[int] = None, 
                 firm_id: Optional[int] = None, user_id: Optional[int] = None):
        super().__init__(event_type=self.__class__.__name__, firm_id=firm_id)
        self.task_id = task_id
        self.task_title = task_title
        self.priority = priority
        self.project_id = project_id
        self.assigned_to = assigned_to
        self.user_id = user_id
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'task_title': self.task_title,
            'project_id': self.project_id,
            'assigned_to': self.assigned_to,
            'priority': self.priority
        }


class ErrorEvent(BaseEvent):
    """Event fired when system errors occur"""
    
    def __init__(self, error_type: str, error_message: str, stack_trace: Optional[str] = None, 
                 context: Optional[Dict[str, Any]] = None, firm_id: Optional[int] = None, 
                 user_id: Optional[int] = None):
        super().__init__(event_type=self.__class__.__name__, firm_id=firm_id)
        self.error_type = error_type
        self.error_message = error_message
        self.stack_trace = stack_trace
        self.context = context or {}
        self.user_id = user_id
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'error_type': self.error_type,
            'error_message': self.error_message,
            'stack_trace': self.stack_trace,
            'context': self.context
        }
class DocumentCreatedEvent(BaseEvent):
    """Event fired when a new document is created"""
    def __init__(self, document_id: int, firm_id: int, name: str, status: str):
        super().__init__(event_type=self.__class__.__name__, firm_id=firm_id)
        self.document_id = document_id
        self.name = name
        self.status = status

    def get_payload(self) -> dict:
        return {
            'document_id': self.document_id,
            'firm_id': self.firm_id,
            'name': self.name,
            'status': self.status
        }


class DocumentUpdatedEvent(BaseEvent):
    """Event fired when a document is updated"""
    def __init__(self, document_id: int, firm_id: int, name: str, status: str):
        super().__init__(event_type=self.__class__.__name__, firm_id=firm_id)
        self.document_id = document_id
        self.name = name
        self.status = status

    def get_payload(self) -> dict:
        return {
            'document_id': self.document_id,
            'firm_id': self.firm_id,
            'name': self.name,
            'status': self.status
        }


class ProjectCreatedEvent(BaseEvent):
    """Event fired when a new project is created"""
    def __init__(self, project_id: int, firm_id: int, name: str, client_id: Optional[int] = None, status: str = "Not Started"):
        super().__init__(event_type=self.__class__.__name__, firm_id=firm_id)
        self.project_id = project_id
        self.name = name
        self.client_id = client_id
        self.status = status

    def get_payload(self) -> Dict[str, Any]:
        return {
            'project_id': self.project_id,
            'firm_id': self.firm_id,
            'name': self.name,
            'client_id': self.client_id,
            'status': self.status
        }



class ProjectUpdatedEvent(BaseEvent):
    """Event fired when a project is updated"""
    def __init__(self, project_id: int, firm_id: int, name: str, changes: Dict[str, Any], client_id: Optional[int] = None):
        super().__init__(event_type=self.__class__.__name__, firm_id=firm_id)
        self.project_id = project_id
        self.name = name
        self.changes = changes
        self.client_id = client_id

    def get_payload(self) -> Dict[str, Any]:
        return {
            'project_id': self.project_id,
            'firm_id': self.firm_id,
            'name': self.name,
            'changes': self.changes,
            'client_id': self.client_id
        }

