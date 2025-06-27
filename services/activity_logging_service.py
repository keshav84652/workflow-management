"""
Enhanced Activity Logging Service for CPA WorkflowPilot

Provides standardized activity logging across all services with
consistent patterns and better categorization.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from core.db_import import db
from models import ActivityLog
from .base import SessionService


class ActivityLoggingService:
    """
    Standardized activity logging service
    """
    
    # Activity categories for better organization
    CATEGORIES = {
        'TASK': 'Task Management',
        'PROJECT': 'Project Management', 
        'CLIENT': 'Client Management',
        'DOCUMENT': 'Document Management',
        'USER': 'User Management',
        'SYSTEM': 'System Operations',
        'AUTH': 'Authentication',
        'AI': 'AI Processing'
    }
    
    # Operation types for consistency
    OPERATIONS = {
        'CREATE': 'Created',
        'UPDATE': 'Updated',
        'DELETE': 'Deleted',
        'VIEW': 'Viewed',
        'UPLOAD': 'Uploaded',
        'DOWNLOAD': 'Downloaded',
        'ANALYZE': 'Analyzed',
        'ASSIGN': 'Assigned',
        'UNASSIGN': 'Unassigned',
        'COMPLETE': 'Completed',
        'REOPEN': 'Reopened'
    }
    

    def log_entity_operation(
        entity_type: str,
        operation: str, 
        entity_id: int,
        entity_name: str = None,
        details: str = None,
        user_id: Optional[int] = None,
        firm_id: Optional[int] = None,
        project_id: Optional[int] = None,
        task_id: Optional[int] = None
    ) -> None:
        """
        Log an operation on an entity with standardized format
        
        Args:
            entity_type: Type of entity (TASK, PROJECT, CLIENT, etc.)
            operation: Operation performed (CREATE, UPDATE, DELETE, etc.)
            entity_id: ID of the affected entity
            entity_name: Name/title of the entity for readable logs
            details: Additional details about the operation
            user_id: User who performed the operation (defaults to session user)
            firm_id: Firm context (defaults to session firm)
            project_id: Related project ID if applicable
            task_id: Related task ID if applicable
        """
        try:
            # Get defaults from session if not provided
            if user_id is None:
                user_id = SessionService.get_current_user_id()
            if firm_id is None:
                firm_id = SessionService.get_current_firm_id()
            
            # Format standardized action message
            entity_display = entity_name or f"{entity_type} #{entity_id}"
            operation_display = ActivityLoggingService.OPERATIONS.get(operation, operation)
            action = f"{operation_display} {entity_display}"
            
            # Add category prefix for clarity
            if entity_type in ActivityLoggingService.CATEGORIES:
                category = ActivityLoggingService.CATEGORIES[entity_type]
                action = f"[{category}] {action}"
            
            # Create activity log entry
            log_entry = ActivityLog(
                action=action,
                user_id=user_id,
                project_id=project_id,
                task_id=task_id,
                details=details,
                timestamp=datetime.utcnow()
            )
            
            db.session.add(log_entry)
            db.session.commit()
            
        except Exception as e:
            # Don't let activity logging failure break the main operation
            print(f"Warning: Failed to create activity log: {e}")
            db.session.rollback()
    

    def log_task_operation(
        operation: str,
        task_id: int,
        task_title: str = None,
        details: str = None,
        user_id: Optional[int] = None,
        project_id: Optional[int] = None
    ) -> None:
        """
        Convenience method for task operations
        """
        ActivityLoggingService.log_entity_operation(
            entity_type='TASK',
            operation=operation,
            entity_id=task_id,
            entity_name=task_title,
            details=details,
            user_id=user_id,
            project_id=project_id,
            task_id=task_id
        )
    

    def log_project_operation(
        operation: str,
        project_id: int,
        project_name: str = None,
        details: str = None,
        user_id: Optional[int] = None
    ) -> None:
        """
        Convenience method for project operations
        """
        ActivityLoggingService.log_entity_operation(
            entity_type='PROJECT',
            operation=operation,
            entity_id=project_id,
            entity_name=project_name,
            details=details,
            user_id=user_id,
            project_id=project_id
        )
    

    def log_client_operation(
        operation: str,
        client_id: int,
        client_name: str = None,
        details: str = None,
        user_id: Optional[int] = None
    ) -> None:
        """
        Convenience method for client operations
        """
        ActivityLoggingService.log_entity_operation(
            entity_type='CLIENT',
            operation=operation,
            entity_id=client_id,
            entity_name=client_name,
            details=details,
            user_id=user_id
        )
    

    def log_document_operation(
        operation: str,
        document_id: int,
        document_name: str = None,
        details: str = None,
        user_id: Optional[int] = None,
        project_id: Optional[int] = None
    ) -> None:
        """
        Convenience method for document operations
        """
        ActivityLoggingService.log_entity_operation(
            entity_type='DOCUMENT',
            operation=operation,
            entity_id=document_id,
            entity_name=document_name,
            details=details,
            user_id=user_id,
            project_id=project_id
        )
    

    def log_ai_operation(
        operation: str,
        target_id: int,
        target_name: str = None,
        details: str = None,
        user_id: Optional[int] = None,
        project_id: Optional[int] = None
    ) -> None:
        """
        Convenience method for AI operations
        """
        ActivityLoggingService.log_entity_operation(
            entity_type='AI',
            operation=operation,
            entity_id=target_id,
            entity_name=target_name,
            details=details,
            user_id=user_id,
            project_id=project_id
        )
    

    def log_bulk_operation(
        entity_type: str,
        operation: str,
        entity_count: int,
        details: str = None,
        user_id: Optional[int] = None,
        firm_id: Optional[int] = None
    ) -> None:
        """
        Log bulk operations that affect multiple entities
        """
        ActivityLoggingService.log_entity_operation(
            entity_type=entity_type,
            operation=operation,
            entity_id=0,  # No specific entity for bulk operations
            entity_name=f"{entity_count} {entity_type.lower()}s",
            details=details,
            user_id=user_id,
            firm_id=firm_id
        )


__all__ = ['ActivityLoggingService']