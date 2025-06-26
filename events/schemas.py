"""
Event Schemas for CPA WorkflowPilot
Pydantic models for event validation and serialization.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from events.base import BaseEvent, register_event


# Task Lifecycle Events
@register_event
@dataclass
class TaskCreatedEvent(BaseEvent):
    """Event fired when a new task is created"""
    task_id: int
    task_title: str
    project_id: Optional[int] = None
    assigned_to: Optional[int] = None
    priority: str = "Medium"
    due_date: Optional[datetime] = None
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'task_title': self.task_title,
            'project_id': self.project_id,
            'assigned_to': self.assigned_to,
            'priority': self.priority,
            'due_date': self.due_date.isoformat() if self.due_date else None
        }


@register_event
@dataclass
class TaskUpdatedEvent(BaseEvent):
    """Event fired when a task is updated"""
    task_id: int
    changes: Dict[str, Any]
    previous_values: Dict[str, Any]
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'changes': self.changes,
            'previous_values': self.previous_values
        }


@register_event
@dataclass
class TaskStatusChangedEvent(BaseEvent):
    """Event fired when task status changes"""
    task_id: int
    old_status: str
    new_status: str
    task_title: str
    project_id: Optional[int] = None
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'task_title': self.task_title,
            'project_id': self.project_id
        }


@register_event
@dataclass
class TaskCompletedEvent(BaseEvent):
    """Event fired when a task is completed"""
    task_id: int
    task_title: str
    project_id: Optional[int] = None
    completion_time: datetime
    assigned_to: Optional[int] = None
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'task_title': self.task_title,
            'project_id': self.project_id,
            'completion_time': self.completion_time.isoformat(),
            'assigned_to': self.assigned_to
        }


@register_event
@dataclass
class TaskAssignedEvent(BaseEvent):
    """Event fired when a task is assigned to a user"""
    task_id: int
    task_title: str
    assigned_to: int
    assigned_by: int
    previous_assignee: Optional[int] = None
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'task_title': self.task_title,
            'assigned_to': self.assigned_to,
            'assigned_by': self.assigned_by,
            'previous_assignee': self.previous_assignee
        }


@register_event
@dataclass
class TaskOverdueEvent(BaseEvent):
    """Event fired when a task becomes overdue"""
    task_id: int
    task_title: str
    due_date: datetime
    assigned_to: Optional[int] = None
    project_id: Optional[int] = None
    days_overdue: int = 0
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'task_title': self.task_title,
            'due_date': self.due_date.isoformat(),
            'assigned_to': self.assigned_to,
            'project_id': self.project_id,
            'days_overdue': self.days_overdue
        }


# Project Lifecycle Events
@register_event
@dataclass
class ProjectCreatedEvent(BaseEvent):
    """Event fired when a new project is created"""
    project_id: int
    project_name: str
    client_id: Optional[int] = None
    template_id: Optional[int] = None
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'project_id': self.project_id,
            'project_name': self.project_name,
            'client_id': self.client_id,
            'template_id': self.template_id
        }


@register_event
@dataclass
class ProjectStatusChangedEvent(BaseEvent):
    """Event fired when project status changes"""
    project_id: int
    project_name: str
    old_status: str
    new_status: str
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'project_id': self.project_id,
            'project_name': self.project_name,
            'old_status': self.old_status,
            'new_status': self.new_status
        }


@register_event
@dataclass
class ProjectCompletedEvent(BaseEvent):
    """Event fired when a project is completed"""
    project_id: int
    project_name: str
    completion_time: datetime
    total_tasks: int
    completed_tasks: int
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'project_id': self.project_id,
            'project_name': self.project_name,
            'completion_time': self.completion_time.isoformat(),
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed_tasks
        }


# Document Analysis Events
@register_event
@dataclass
class DocumentAnalysisStartedEvent(BaseEvent):
    """Event fired when AI document analysis is started"""
    document_id: int
    document_name: str
    file_type: str
    checklist_id: Optional[int] = None
    analysis_service: str = "unknown"
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'document_id': self.document_id,
            'document_name': self.document_name,
            'file_type': self.file_type,
            'checklist_id': self.checklist_id,
            'analysis_service': self.analysis_service
        }


@register_event
@dataclass
class DocumentAnalysisCompletedEvent(BaseEvent):
    """Event fired when AI document analysis is completed"""
    document_id: int
    document_name: str
    analysis_results: Dict[str, Any]
    confidence_score: float
    document_type: str
    processing_time_ms: Optional[float] = None
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'document_id': self.document_id,
            'document_name': self.document_name,
            'analysis_results': self.analysis_results,
            'confidence_score': self.confidence_score,
            'document_type': self.document_type,
            'processing_time_ms': self.processing_time_ms
        }


@register_event
@dataclass
class DocumentAnalysisFailedEvent(BaseEvent):
    """Event fired when AI document analysis fails"""
    document_id: int
    document_name: str
    error_message: str
    error_type: str
    retry_count: int = 0
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'document_id': self.document_id,
            'document_name': self.document_name,
            'error_message': self.error_message,
            'error_type': self.error_type,
            'retry_count': self.retry_count
        }


# Client Management Events
@register_event
@dataclass
class ClientCreatedEvent(BaseEvent):
    """Event fired when a new client is created"""
    client_id: int
    client_name: str
    entity_type: str
    contact_email: Optional[str] = None
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'client_id': self.client_id,
            'client_name': self.client_name,
            'entity_type': self.entity_type,
            'contact_email': self.contact_email
        }


@register_event
@dataclass
class ClientUpdatedEvent(BaseEvent):
    """Event fired when client information is updated"""
    client_id: int
    changes: Dict[str, Any]
    previous_values: Dict[str, Any]
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'client_id': self.client_id,
            'changes': self.changes,
            'previous_values': self.previous_values
        }


# User Activity Events
@register_event
@dataclass
class UserLoginEvent(BaseEvent):
    """Event fired when a user logs in"""
    login_time: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'login_time': self.login_time.isoformat(),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent
        }


@register_event
@dataclass
class UserLogoutEvent(BaseEvent):
    """Event fired when a user logs out"""
    logout_time: datetime
    session_duration_minutes: Optional[float] = None
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'logout_time': self.logout_time.isoformat(),
            'session_duration_minutes': self.session_duration_minutes
        }


# System Events
@register_event
@dataclass
class SystemHealthCheckEvent(BaseEvent):
    """Event fired during system health checks"""
    component_name: str
    status: str  # healthy, warning, error
    metrics: Dict[str, Any]
    check_time: datetime
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'component_name': self.component_name,
            'status': self.status,
            'metrics': self.metrics,
            'check_time': self.check_time.isoformat()
        }


@register_event
@dataclass
class ErrorEvent(BaseEvent):
    """Event fired when system errors occur"""
    error_type: str
    error_message: str
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = None
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'error_type': self.error_type,
            'error_message': self.error_message,
            'stack_trace': self.stack_trace,
            'context': self.context or {}
        }


# Notification Events
@register_event
@dataclass
class NotificationEvent(BaseEvent):
    """Event for triggering notifications"""
    recipient_user_id: int
    notification_type: str
    title: str
    message: str
    priority: str = "normal"  # low, normal, high, urgent
    action_url: Optional[str] = None
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'recipient_user_id': self.recipient_user_id,
            'notification_type': self.notification_type,
            'title': self.title,
            'message': self.message,
            'priority': self.priority,
            'action_url': self.action_url
        }


# Backup and Sync Events
@register_event
@dataclass
class BackupCreatedEvent(BaseEvent):
    """Event fired when a backup is created"""
    backup_id: str
    backup_type: str
    file_size_bytes: int
    backup_location: str
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'backup_id': self.backup_id,
            'backup_type': self.backup_type,
            'file_size_bytes': self.file_size_bytes,
            'backup_location': self.backup_location
        }


@register_event
@dataclass
class IntegrationSyncEvent(BaseEvent):
    """Event for third-party integration synchronization"""
    integration_type: str  # onedrive, sharepoint, etc.
    sync_direction: str  # inbound, outbound, bidirectional
    items_synced: int
    sync_status: str  # success, partial, failed
    error_details: Optional[str] = None
    
    def get_payload(self) -> Dict[str, Any]:
        return {
            'integration_type': self.integration_type,
            'sync_direction': self.sync_direction,
            'items_synced': self.items_synced,
            'sync_status': self.sync_status,
            'error_details': self.error_details
        }
