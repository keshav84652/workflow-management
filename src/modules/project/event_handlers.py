"""
Event Handlers for CPA WorkflowPilot
Handles event logic like notifications, logging, and real-time updates.
"""

from abc import ABC, abstractmethod
from src.shared.events.base import EventHandler, BaseEvent
from src.shared.events.schemas import (
    TaskCreatedEvent, TaskUpdatedEvent, ProjectWorkflowAdvancedEvent, ProjectCompletedEvent
)
from src.shared.database.db_import import db


class LoggingHandler(EventHandler):
    """Handler for logging events to a file or external service"""

    def can_handle(self, event: BaseEvent) -> bool:
        # Handle all events
        return True

    async def handle(self, event: BaseEvent) -> bool:
        try:
            # Log the event type for now
            print(f"[LoggingHandler] Event received: {event.event_type}")
            return True
        except Exception as e:
            print(f"Error in LoggingHandler: {e}")
            return False


class NotificationHandler(EventHandler):
    """Handler for sending notifications based on events"""

    def can_handle(self, event: BaseEvent) -> bool:
        # Handle task-related events
        return isinstance(event, (TaskCreatedEvent, TaskUpdatedEvent))

    async def handle(self, event: BaseEvent) -> bool:
        try:
            # Send a notification for demonstration purposes
            print(f"[NotificationHandler] Sending notification for {event.event_type}")
            return True
        except Exception as e:
            print(f"Error in NotificationHandler: {e}")
            return False


class ProjectWorkflowTaskUpdateHandler(EventHandler):
    """Handler for updating task statuses when project workflow advances
    
    This handler maintains domain boundaries by responding to events rather
    than allowing direct cross-domain manipulation. When a project advances
    in its workflow, this handler updates the associated task statuses.
    
    This replaces the cross-domain violation in ProjectService._update_project_tasks_for_workflow_change
    """
    
    def can_handle(self, event: BaseEvent) -> bool:
        return isinstance(event, ProjectWorkflowAdvancedEvent)
    
    async def handle(self, event: ProjectWorkflowAdvancedEvent) -> bool:
        """Handle project workflow advancement by updating task statuses"""
        try:
            print(f"[ProjectWorkflowTaskUpdateHandler] Handling workflow advancement for project {event.project_id}")
            
            # Only update tasks if we have valid status information
            if not event.new_status_id or not event.work_type_id:
                print(f"Skipping task update - insufficient status information")
                return True
            
            # Get all tasks for this project
            from .models import Task
            project_tasks = Task.query.filter_by(project_id=event.project_id).order_by(Task.id).all()
            
            if not project_tasks:
                print(f"No tasks found for project {event.project_id}")
                return True
            
            # Get workflow statuses to determine task update logic
            from src.models import TaskStatus
            workflow_statuses = TaskStatus.query.filter_by(
                work_type_id=event.work_type_id
            ).order_by(TaskStatus.position.asc()).all()
            
            if not workflow_statuses:
                print(f"No workflow statuses found for work type {event.work_type_id}")
                return True
            
            # Find the position of the new status
            new_position = None
            for i, status in enumerate(workflow_statuses):
                if status.id == event.new_status_id:
                    new_position = i
                    break
            
            if new_position is None:
                print(f"Invalid status ID {event.new_status_id} for work type {event.work_type_id}")
                return True
            
            # Update task statuses based on workflow position
            # This is the same logic as before, but now properly contained within the project domain
            updated_count = 0
            for i, task in enumerate(project_tasks):
                old_status = task.status
                
                if i < new_position:
                    # Tasks before current position should be "Completed"
                    task.status = 'Completed'
                elif i == new_position:
                    # Current position task should be "In Progress"
                    task.status = 'In Progress'
                else:
                    # Tasks after current position should be "Not Started"
                    task.status = 'Not Started'
                
                if old_status != task.status:
                    updated_count += 1
            
            # Commit the changes
            db.session.commit()
            
            print(f"Updated {updated_count} task statuses for project {event.project_id} workflow advancement")
            
            # Log the activity
            if event.user_id:
                try:
                    from src.shared.services.activity_service import ActivityService
                    activity_service = ActivityService()
                    activity_service.log_entity_operation(
                        entity_type='PROJECT',
                        operation='WORKFLOW_TASKS_UPDATED',
                        entity_id=event.project_id,
                        entity_name=event.project_name,
                        details=f'Updated {updated_count} task statuses due to workflow advancement to {event.new_status_name}',
                        user_id=event.user_id
                    )
                except Exception as activity_error:
                    print(f"Failed to log activity: {activity_error}")
            
            return True
            
        except Exception as e:
            print(f"Error in ProjectWorkflowTaskUpdateHandler: {e}")
            db.session.rollback()
            return False


class ProjectCompletionTaskUpdateHandler(EventHandler):
    """Handler for updating task statuses when a project is completed
    
    This handler maintains domain boundaries by responding to events rather
    than allowing direct cross-domain manipulation. When a project is marked
    as completed, this handler marks all associated tasks as completed.
    
    This replaces the cross-domain violation in ProjectService.move_project_status
    """
    
    def can_handle(self, event: BaseEvent) -> bool:
        return isinstance(event, ProjectCompletedEvent)
    
    async def handle(self, event: ProjectCompletedEvent) -> bool:
        """Handle project completion by marking all tasks as completed"""
        try:
            print(f"[ProjectCompletionTaskUpdateHandler] Handling completion for project {event.project_id}")
            
            # Get all tasks for this project
            from .models import Task
            project_tasks = Task.query.filter_by(project_id=event.project_id).all()
            
            if not project_tasks:
                print(f"No tasks found for project {event.project_id}")
                return True
            
            # Mark all incomplete tasks as completed
            updated_count = 0
            for task in project_tasks:
                if task.status != 'Completed':
                    task.status = 'Completed'
                    updated_count += 1
            
            # Commit the changes
            db.session.commit()
            
            print(f"Marked {updated_count} tasks as completed for project {event.project_id}")
            
            # Log the activity
            if event.user_id:
                try:
                    from src.shared.services.activity_service import ActivityService
                    activity_service = ActivityService()
                    activity_service.log_entity_operation(
                        entity_type='PROJECT',
                        operation='TASKS_COMPLETED',
                        entity_id=event.project_id,
                        entity_name=event.project_name,
                        details=f'Marked {updated_count} tasks as completed due to project completion',
                        user_id=event.user_id
                    )
                except Exception as activity_error:
                    print(f"Failed to log activity: {activity_error}")
            
            return True
            
        except Exception as e:
            print(f"Error in ProjectCompletionTaskUpdateHandler: {e}")
            db.session.rollback()
            return False

