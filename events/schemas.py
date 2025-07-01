"""
Event Schemas for CPA WorkflowPilot
Event definitions for core business events using the proper BaseEvent architecture.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from events.base import BaseEvent, register_event


@register_event
@dataclass
class ClientCreatedEvent(BaseEvent):
    """Event fired when a new client is created"""
    client_id: int
    name: str
    is_active: bool
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'client_id': self.client_id,
            'name': self.name,
            'is_active': self.is_active
        }


@register_event
@dataclass
class ClientUpdatedEvent(BaseEvent):
    """Event fired when a client is updated"""
    client_id: int
    name: str
    previous_name: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'client_id': self.client_id,
            'name': self.name,
            'previous_name': self.previous_name,
            'changes': self.changes or {}
        }


@register_event
@dataclass
class TaskCreatedEvent(BaseEvent):
    """Event fired when a new task is created"""
    task_id: int
    title: str
    project_id: Optional[int] = None
    assignee_id: Optional[int] = None
    priority: str = 'Medium'
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'title': self.title,
            'project_id': self.project_id,
            'assignee_id': self.assignee_id,
            'priority': self.priority,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'estimated_hours': self.estimated_hours
        }


@register_event
@dataclass
class TaskUpdatedEvent(BaseEvent):
    """Event fired when a task is updated"""
    task_id: int
    title: str
    previous_title: Optional[str] = None
    project_id: Optional[int] = None
    assignee_id: Optional[int] = None
    priority: str = 'Medium'
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    changes: Optional[Dict[str, Any]] = None
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'title': self.title,
            'previous_title': self.previous_title,
            'project_id': self.project_id,
            'assignee_id': self.assignee_id,
            'priority': self.priority,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'estimated_hours': self.estimated_hours,
            'changes': self.changes or {}
        }


@register_event
@dataclass
class TaskStatusChangedEvent(BaseEvent):
    """Event fired when a task status changes"""
    task_id: int
    title: str
    new_status: str
    previous_status: str
    project_id: Optional[int] = None
    assignee_id: Optional[int] = None
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'title': self.title,
            'new_status': self.new_status,
            'previous_status': self.previous_status,
            'project_id': self.project_id,
            'assignee_id': self.assignee_id
        }


@register_event
@dataclass
class TaskDeletedEvent(BaseEvent):
    """Event fired when a task is deleted"""
    task_id: int
    title: str
    project_id: Optional[int] = None
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'title': self.title,
            'project_id': self.project_id
        }


@register_event
@dataclass
class DocumentAnalysisStartedEvent(BaseEvent):
    """Event fired when document analysis begins"""
    document_id: int
    checklist_id: int
    filename: str
    file_size: Optional[int] = None
    ai_service: str = 'azure'
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'document_id': self.document_id,
            'checklist_id': self.checklist_id,
            'filename': self.filename,
            'file_size': self.file_size,
            'ai_service': self.ai_service
        }


@register_event
@dataclass
class DocumentAnalysisCompletedEvent(BaseEvent):
    """Event fired when document analysis completes successfully"""
    document_id: int
    checklist_id: int
    filename: str
    analysis_results: Dict[str, Any]
    confidence_score: float = 0.0
    processing_time_ms: Optional[float] = None
    ai_service: str = 'azure'
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'document_id': self.document_id,
            'checklist_id': self.checklist_id,
            'filename': self.filename,
            'analysis_results': self.analysis_results,
            'confidence_score': self.confidence_score,
            'processing_time_ms': self.processing_time_ms,
            'ai_service': self.ai_service
        }


@register_event
@dataclass
class DocumentAnalysisFailedEvent(BaseEvent):
    """Event fired when document analysis fails"""
    document_id: int
    checklist_id: int
    filename: str
    error_message: str
    ai_service: str = 'azure'
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'document_id': self.document_id,
            'checklist_id': self.checklist_id,
            'filename': self.filename,
            'error_message': self.error_message,
            'ai_service': self.ai_service
        }


@register_event
@dataclass
class DocumentCreatedEvent(BaseEvent):
    """Event fired when a document is created"""
    document_id: int
    name: str
    status: str = 'pending'
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'document_id': self.document_id,
            'name': self.name,
            'status': self.status
        }


@register_event
@dataclass
class DocumentUpdatedEvent(BaseEvent):
    """Event fired when a document is updated"""
    document_id: int
    name: str
    changes: Optional[Dict[str, Any]] = None
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'document_id': self.document_id,
            'name': self.name,
            'changes': self.changes or {}
        }


@register_event
@dataclass
class ProjectCreatedEvent(BaseEvent):
    """Event fired when a new project is created"""
    project_id: int
    name: str
    client_name: str
    template_name: Optional[str] = None
    priority: str = 'Medium'
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'project_id': self.project_id,
            'name': self.name,
            'client_name': self.client_name,
            'template_name': self.template_name,
            'priority': self.priority
        }


@register_event
@dataclass
class ProjectUpdatedEvent(BaseEvent):
    """Event fired when a project is updated"""
    project_id: int
    name: str
    client_name: str
    status: str
    changes: Optional[Dict[str, Any]] = None
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'project_id': self.project_id,
            'name': self.name,
            'client_name': self.client_name,
            'status': self.status,
            'changes': self.changes or {}
        }


@register_event
@dataclass
class ErrorEvent(BaseEvent):
    """Generic error event for system errors"""
    error_type: str
    error_message: str
    context: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'error_type': self.error_type,
            'error_message': self.error_message,
            'context': self.context or {},
            'stack_trace': self.stack_trace
        }