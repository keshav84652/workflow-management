"""
TaskService: Handles all business logic for tasks and subtasks.
"""

from core.db_import import db
from models import Task
from sqlalchemy import or_, and_
from services.activity_logging_service import ActivityLoggingService as ActivityService
from services.base import BaseService, transactional

class TaskService(BaseService):
    @transactional
    def create_task(self, title, description, firm_id, user_id, project_id=None, assignee_id=None,
                   due_date=None, priority='Medium', estimated_hours=None):
        """Create a new task."""
        # Validation
        if not title or not title.strip():
            return {'success': False, 'message': 'Title is required'}
        if not firm_id:
            return {'success': False, 'message': 'Firm ID is required'}
        if not user_id:
            return {'success': False, 'message': 'User ID is required'}
        
        # Convert string date to date object if needed
        if due_date and isinstance(due_date, str):
            from datetime import datetime
            due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
        task = Task(
            title=title,
            description=description,
            firm_id=firm_id,
            assignee_id=assignee_id or user_id,
            project_id=project_id,
            due_date=due_date,
            priority=priority,
            estimated_hours=estimated_hours
        )
        db.session.add(task)
        
        # Log activity (will be committed by @transactional decorator)
        ActivityService.log_task_operation(
            operation='CREATE',
            task_id=task.id,
            task_title=title,
            details=f'Task created with priority {priority}',
            user_id=user_id,
            project_id=project_id
        )
        
        return {
            'success': True,
            'task_id': task.id,
            'task': {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.current_status,
                'priority': task.priority,
                'assignee_name': task.assignee.name if task.assignee else 'Unassigned',
                'created_at': task.created_at.strftime('%m/%d/%Y %I:%M %p')
            }
        }

    @transactional
    def create_subtask(self, parent_task_id, title, description, user_id):
        parent_task = Task.query.get_or_404(parent_task_id)
        max_order = db.session.query(db.func.max(Task.subtask_order)).filter_by(parent_task_id=parent_task_id).scalar() or 0
        subtask = Task(
            title=title,
            description=description,
            parent_task_id=parent_task_id,
            subtask_order=max_order + 1,
            project_id=parent_task.project_id,
            firm_id=parent_task.firm_id,
            assignee_id=parent_task.assignee_id,
            priority=parent_task.priority,
            status_id=parent_task.status_id,
            status=parent_task.status if not parent_task.status_id else 'Not Started'
        )
        db.session.add(subtask)
        ActivityService.log_task_operation(
            operation='CREATE',
            task_id=subtask.id,
            task_title=f'Subtask: {title}',
            details=f'Created as subtask of "{parent_task.title}"',
            user_id=user_id,
            project_id=parent_task.project_id
        )
        return {
            'success': True,
            'subtask': {
                'id': subtask.id,
                'title': subtask.title,
                'description': subtask.description,
                'status': subtask.current_status,
                'assignee_name': subtask.assignee.name if subtask.assignee else 'Unassigned',
                'created_at': subtask.created_at.strftime('%m/%d/%Y %I:%M %p')
            }
        }

    @transactional
    def reorder_subtasks(self, task_id, subtask_ids, user_id):
        for index, subtask_id in enumerate(subtask_ids):
            subtask = Task.query.get(subtask_id)
            if subtask and subtask.parent_task_id == task_id:
                subtask.subtask_order = index + 1
        return {'success': True, 'message': 'Subtasks reordered successfully'}

    @transactional
    def convert_to_subtask(self, task_id, parent_task_id, user_id):
        task = Task.query.get_or_404(task_id)
        parent_task = Task.query.get(parent_task_id)
        if not parent_task:
            return {'success': False, 'message': 'Parent task not found'}, 404
        # Prevent circular relationships
        if parent_task_id == task_id:
            return {'success': False, 'message': 'Cannot make task a subtask of itself'}, 400
        current = parent_task
        while current.parent_task:
            if current.parent_task.id == task_id:
                return {'success': False, 'message': 'Cannot create circular subtask relationship'}, 400
            current = current.parent_task
        max_order = db.session.query(db.func.max(Task.subtask_order)).filter_by(parent_task_id=parent_task_id).scalar() or 0
        task.parent_task_id = parent_task_id
        task.subtask_order = max_order + 1
        ActivityService.log_task_operation(
            operation='UPDATE',
            task_id=task.id,
            task_title=task.title,
            details=f'Converted to subtask of "{parent_task.title}"',
            user_id=user_id,
            project_id=parent_task.project_id
        )
        return {'success': True, 'message': 'Task converted to subtask successfully'}
    
    def get_tasks_with_dependency_info(self, firm_id, filters=None):
        """
        Get tasks with dependency information for a firm
        CRITICAL: This applies interdependency filtering for sequential projects
        """
        from repositories.task_repository import TaskRepository
        task_repo = TaskRepository()
        all_tasks = task_repo.get_filtered_tasks(firm_id, filters)
        
        # Apply interdependency filtering - only show first active task per sequential project
        filtered_tasks = self._filter_tasks_by_dependency_mode(all_tasks)
        
        # Return in the format expected by blueprint
        return [{'task': task} for task in filtered_tasks]
    
    def _filter_tasks_by_dependency_mode(self, tasks):
        """
        Filter tasks based on project dependency mode
        For interdependent projects, only show the first active task
        COPIED FROM DashboardService to ensure consistency
        """
        filtered_tasks = []
        seen_projects = set()
        
        for task in tasks:
            if task.project and task.project.task_dependency_mode:
                # For interdependent projects, only count the first active task per project
                if task.project_id not in seen_projects and not task.is_completed:
                    filtered_tasks.append(task)
                    seen_projects.add(task.project_id)
            else:
                # For independent tasks or non-interdependent projects, count all tasks
                filtered_tasks.append(task)
        
        return filtered_tasks
    
    @staticmethod
    def get_task_by_id_with_access_check(task_id, firm_id):
        """Get task by ID with firm access verification"""
        from models import Project
        task = Task.query.outerjoin(Project).filter(
            Task.id == task_id,
            or_(
                Project.firm_id == firm_id,
                and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            )
        ).first()
        return task
    
    @staticmethod
    def get_project_tasks(project_id, firm_id, include_completed=True):
        """Get all tasks for a specific project"""
        from repositories.task_repository import TaskRepository
        task_repo = TaskRepository()
        return task_repo.get_project_tasks(project_id, firm_id, include_completed)
    
    @staticmethod
    def create_task_from_form(form_data, firm_id, user_id):
        """Create task from form data"""
        try:
            title = form_data.get('title', '').strip()
            if not title:
                return {'success': False, 'message': 'Title is required'}
            
            project_id = form_data.get('project_id')
            if project_id:
                project_id = int(project_id) if project_id != '' else None
            
            assignee_id = form_data.get('assignee_id')
            if assignee_id:
                assignee_id = int(assignee_id) if assignee_id != '' else None
            
            due_date = form_data.get('due_date')
            if due_date:
                from datetime import datetime
                due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
            
            estimated_hours = form_data.get('estimated_hours')
            if estimated_hours:
                estimated_hours = float(estimated_hours)
            
            return TaskService.create_task(
                title=title,
                description=form_data.get('description', ''),
                firm_id=firm_id,
                user_id=user_id,
                project_id=project_id,
                assignee_id=assignee_id,
                due_date=due_date,
                priority=form_data.get('priority', 'Medium'),
                estimated_hours=estimated_hours
            )
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def update_task_from_form(task_id, form_data, firm_id, user_id):
        """Update task from form data"""
        try:
            task = TaskService.get_task_by_id_with_access_check(task_id, firm_id)
            if not task:
                return {'success': False, 'message': 'Task not found or access denied'}
            
            # Update fields
            task.title = form_data.get('title', task.title)
            task.description = form_data.get('description', task.description)
            task.priority = form_data.get('priority', task.priority)
            
            assignee_id = form_data.get('assignee_id')
            if assignee_id:
                task.assignee_id = int(assignee_id) if assignee_id != '' else None
            
            due_date = form_data.get('due_date')
            if due_date:
                from datetime import datetime
                task.due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
            
            estimated_hours = form_data.get('estimated_hours')
            if estimated_hours:
                task.estimated_hours = float(estimated_hours)
            
            db.session.commit()
            
            ActivityService.log_task_operation(
                operation='UPDATE',
                task_id=task.id,
                task_title=task.title,
                details='Task updated',
                user_id=user_id,
                project_id=task.project_id
            )
            
            return {'success': True, 'message': 'Task updated successfully'}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def delete_task(task_id, firm_id, user_id):
        """Delete a task with access check"""
        try:
            task = TaskService.get_task_by_id_with_access_check(task_id, firm_id)
            if not task:
                return {'success': False, 'message': 'Task not found or access denied'}
            
            task_title = task.title
            db.session.delete(task)
            db.session.commit()
            
            ActivityService.log_task_operation(
                operation='DELETE',
                task_id=task_id,
                task_title=task_title,
                details='Task deleted',
                user_id=user_id,
                project_id=task.project_id
            )
            
            # Publish task deletion event
            from events.schemas import TaskDeletedEvent
            from events.publisher import publish_event
            event = TaskDeletedEvent(
                task_id=task_id,
                task_title=task_title,
                assigned_to=task.assignee_id,
                firm_id=firm_id,
                user_id=user_id
            )
            publish_event(event)
            
            return {'success': True, 'message': 'Task deleted successfully'}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def add_task_comment(task_id, firm_id, comment_text, user_id):
        """Add comment to task"""
        try:
            if not comment_text.strip():
                return {'success': False, 'message': 'Comment cannot be empty'}
            
            task = TaskService.get_task_by_id_with_access_check(task_id, firm_id)
            if not task:
                return {'success': False, 'message': 'Task not found or access denied'}
            
            from models import TaskComment
            comment = TaskComment(
                comment=comment_text,
                task_id=task_id,
                user_id=user_id
            )
            db.session.add(comment)
            db.session.commit()
            
            return {
                'success': True,
                'comment': {
                    'id': comment.id,
                    'comment': comment.comment,
                    'user_name': comment.user.name,
                    'created_at': comment.created_at.strftime('%m/%d/%Y %I:%M %p')
                }
            }
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def bulk_update_tasks(task_ids, updates, firm_id, user_id):
        """Bulk update multiple tasks"""
        try:
            from repositories.task_repository import TaskRepository
            task_repo = TaskRepository()
            result = task_repo.bulk_update(task_ids, updates, firm_id)
            
            if result['success']:
                db.session.commit()
                
                ActivityService.log_entity_operation(
                    entity_type='TASK',
                    operation='UPDATE',
                    entity_id=0,  # Bulk operation
                    entity_name=f'{len(task_ids)} tasks',
                    details=f'Bulk updated: {updates}',
                    user_id=user_id
                )
            
            return result
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def bulk_delete_tasks(task_ids, firm_id, user_id):
        """Bulk delete multiple tasks"""
        try:
            from repositories.task_repository import TaskRepository
            task_repo = TaskRepository()
            result = task_repo.bulk_delete(task_ids, firm_id)
            
            if result['success']:
                db.session.commit()
                
                ActivityService.log_entity_operation(
                    entity_type='TASK',
                    operation='DELETE',
                    entity_id=0,  # Bulk operation
                    entity_name=f'{result["deleted_count"]} tasks',
                    details='Bulk deleted tasks',
                    user_id=user_id
                )
            
            return result
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def update_task_status(task_id, new_status, firm_id, user_id):
        """Update task status"""
        try:
            task = TaskService.get_task_by_id_with_access_check(task_id, firm_id)
            if not task:
                return {'success': False, 'message': 'Task not found or access denied'}
            
            old_status = task.current_status
            task.status = new_status
            db.session.commit()
            
            # Log status change activity
            ActivityService.log_task_operation(
                operation='STATUS_CHANGE',
                task_id=task_id,
                task_title=task.title,
                details=f'Status changed from {old_status} to {new_status}',
                user_id=user_id,
                project_id=task.project_id
            )
            
            # Publish status change event
            from events.schemas import TaskStatusChangedEvent
            from events.publisher import publish_event
            event = TaskStatusChangedEvent(
                task_id=task_id,
                task_title=task.title,
                old_status=old_status,
                new_status=new_status,
                project_id=task.project_id,
                assigned_to=task.assignee_id,
                firm_id=firm_id,
                user_id=user_id
            )
            publish_event(event)
            
            return {'success': True, 'message': 'Task status updated successfully'}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
