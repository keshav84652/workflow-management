"""
TaskService: Handles all business logic for tasks and subtasks.
"""

from typing import Dict, Any, Optional
from src.shared.database.db_import import db
from src.models import Task
from sqlalchemy import or_, and_
from src.shared.services import ActivityLoggingService as ActivityService
from src.shared.base import BaseService, transactional
from src.shared.interfaces import ITaskService
from .task_repository import TaskRepository

class TaskService(BaseService, ITaskService):
    def __init__(self):
        super().__init__()
        self.task_repository = TaskRepository()
        
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
        from .task_repository import TaskRepository
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
    
    def get_task_by_id_with_access_check(self, task_id, firm_id):
        """Get task by ID with firm access verification"""
        return self.task_repository.get_by_id_with_firm_access(task_id, firm_id)
    
    def get_project_tasks(self, project_id, firm_id, include_completed=True):
        """Get all tasks for a specific project"""
        return self.task_repository.get_project_tasks(project_id, firm_id, include_completed)
    
    @transactional
    def create_task_from_form(self, form_data, firm_id, user_id):
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
            
            return self.create_task(
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
    
    @transactional
    def update_task_from_form(self, task_id, form_data, firm_id, user_id):
        """Update task from form data"""
            task = self.get_task_by_id_with_access_check(task_id, firm_id)
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
            
            ActivityService.log_task_operation(
                operation='UPDATE',
                task_id=task.id,
                task_title=task.title,
                details='Task updated',
                user_id=user_id,
                project_id=task.project_id
            )
            
            return {'success': True, 'message': 'Task updated successfully'}
    
    @transactional
    def delete_task(self, task_id, firm_id, user_id):
        """Delete a task with access check"""
            task = self.get_task_by_id_with_access_check(task_id, firm_id)
            if not task:
                return {'success': False, 'message': 'Task not found or access denied'}
            
            task_title = task.title
            db.session.delete(task)
            
            ActivityService.log_task_operation(
                operation='DELETE',
                task_id=task_id,
                task_title=task_title,
                details='Task deleted',
                user_id=user_id,
                project_id=task.project_id
            )
            
            # Publish task deletion event
            from src.shared.events.schemas import TaskDeletedEvent
            from src.shared.events.publisher import publish_event
            event = TaskDeletedEvent(
                task_id=task_id,
                task_title=task_title,
                assigned_to=task.assignee_id,
                firm_id=firm_id,
                user_id=user_id
            )
            publish_event(event)
            
            return {'success': True, 'message': 'Task deleted successfully'}
    
    @transactional
    def add_task_comment(self, task_id, firm_id, comment_text, user_id):
        """Add comment to task"""
            if not comment_text.strip():
                return {'success': False, 'message': 'Comment cannot be empty'}
            
            task = self.get_task_by_id_with_access_check(task_id, firm_id)
            if not task:
                return {'success': False, 'message': 'Task not found or access denied'}
            
            from src.models import TaskComment
            comment = TaskComment(
                comment=comment_text,
                task_id=task_id,
                user_id=user_id
            )
            db.session.add(comment)
            
            return {
                'success': True,
                'comment': {
                    'id': comment.id,
                    'comment': comment.comment,
                    'user_name': comment.user.name,
                    'created_at': comment.created_at.strftime('%m/%d/%Y %I:%M %p')
                }
            }
    
    @transactional
    def bulk_update_tasks(self, task_ids, updates, firm_id, user_id):
        """Bulk update multiple tasks"""
            from .task_repository import TaskRepository
            task_repo = TaskRepository()
            result = task_repo.bulk_update(task_ids, updates, firm_id)
            
            if result['success']:
                ActivityService.log_entity_operation(
                    entity_type='TASK',
                    operation='UPDATE',
                    entity_id=0,  # Bulk operation
                    entity_name=f'{len(task_ids)} tasks',
                    details=f'Bulk updated: {updates}',
                    user_id=user_id
                )
            
            return result
    
    @transactional
    def bulk_delete_tasks(self, task_ids, firm_id, user_id):
        """Bulk delete multiple tasks"""
        from .task_repository import TaskRepository
        task_repo = TaskRepository()
        result = task_repo.bulk_delete(task_ids, firm_id)
        
        if result['success']:
            ActivityService.log_entity_operation(
                entity_type='TASK',
                operation='DELETE',
                entity_id=0,  # Bulk operation
                entity_name=f'{result["deleted_count"]} tasks',
                details='Bulk deleted tasks',
                user_id=user_id
            )
        
        return result
    
    @transactional
    def update_task_status(self, task_id, new_status, firm_id, user_id):
        """Update task status"""
        try:
            task = self.get_task_by_id_with_access_check(task_id, firm_id)
            if not task:
                return {'success': False, 'message': 'Task not found or access denied'}
            
            old_status = task.current_status
            task.status = new_status
            
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
            from src.shared.events.schemas import TaskStatusChangedEvent
            from src.shared.events.publisher import publish_event
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
    
    def would_create_circular_dependency(self, task_id, dependency_id):
        """
        Check if adding dependency_id as a dependency of task_id would create a circular dependency.
        Optimized version that fetches all dependencies at once to avoid N+1 query problem.
        """
        # Fetch all task dependencies in a single query
        all_tasks = Task.query.filter(
            Task.dependencies.isnot(None),
            Task.dependencies != ''
        ).all()
        
        # Build dependency graph in memory
        dependency_graph = {}
        for task in all_tasks:
            task_deps = task.dependency_list  # Uses the property that parses the comma-separated string
            if task_deps:
                dependency_graph[task.id] = task_deps
        
        def has_path_in_graph(from_id, to_id, visited=None):
            """Check if there's a path from from_id to to_id using in-memory graph"""
            if visited is None:
                visited = set()
            
            if from_id == to_id:
                return True
            
            if from_id in visited:
                return False
            
            visited.add(from_id)
            
            # Check all tasks that depend on from_id
            for task_id_key, deps in dependency_graph.items():
                if from_id in deps:  # task_id_key depends on from_id
                    if has_path_in_graph(task_id_key, to_id, visited.copy()):
                        return True
            
            return False
        
        # Check if dependency_id already depends on task_id (would create cycle)
        return has_path_in_graph(dependency_id, task_id)
    
    def get_task_statistics(self, firm_id: int) -> dict:
        """Get task statistics for dashboard"""
        try:
            # Import models here to avoid circular imports
            from src.models import Task, Project
            from datetime import date
            
            # Base query for firm tasks
            base_query = db.session.query(Task).join(Project).filter(Project.firm_id == firm_id)
            
            total = base_query.count()
            completed = base_query.filter(Task.status == 'Completed').count()
            in_progress = base_query.filter(Task.status == 'In Progress').count()
            not_started = base_query.filter(Task.status == 'Not Started').count()
            
            # Overdue tasks (due date in the past and not completed)
            today = date.today()
            overdue = base_query.filter(
                Task.due_date < today,
                Task.status != 'Completed'
            ).count()
            
            # Due soon (next 7 days)
            from datetime import timedelta
            week_from_now = today + timedelta(days=7)
            due_soon = base_query.filter(
                Task.due_date >= today,
                Task.due_date <= week_from_now,
                Task.status != 'Completed'
            ).count()
            
            return {
                'success': True,
                'statistics': {
                    'total': total,
                    'completed': completed,
                    'pending': not_started,
                    'in_progress': in_progress,
                    'active': total - completed,
                    'overdue': overdue,
                    'due_soon': due_soon
                }
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to get task statistics: {str(e)}',
                'statistics': {}
            }
    
    def get_work_type_distribution(self, firm_id: int) -> dict:
        """Get work type distribution for dashboard"""
        try:
            from src.models import Task, Project, WorkType
            
            # Get work type distribution
            query = db.session.query(
                WorkType.name, 
                db.func.count(Task.id)
            ).join(
                Task, Task.work_type_id == WorkType.id
            ).join(
                Project, Task.project_id == Project.id
            ).filter(
                Project.firm_id == firm_id
            ).group_by(WorkType.name)
            
            distribution = {}
            for work_type_name, count in query.all():
                distribution[work_type_name] = count
            
            return {
                'success': True,
                'distribution': distribution
            }
        except Exception as e:
            return {
                'success': False,
                'distribution': {}
            }
    
    def get_recent_tasks(self, firm_id: int, limit: int = 10) -> dict:
        """Get recent tasks for dashboard"""
        try:
            from src.models import Task, Project, User
            from datetime import datetime, timedelta
            
            # Get tasks created in the last 30 days
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            query = db.session.query(Task).join(Project).outerjoin(User).filter(
                Project.firm_id == firm_id,
                Task.created_at >= thirty_days_ago
            ).order_by(Task.created_at.desc()).limit(limit)
            
            tasks = []
            for task in query.all():
                task_dict = {
                    'id': task.id,
                    'title': task.title,
                    'status': task.status,
                    'priority': task.priority,
                    'due_date': task.due_date.strftime('%Y-%m-%d') if task.due_date else None,
                    'project_name': task.project.name if task.project else '',
                    'assignee_name': task.assignee.name if task.assignee else 'Unassigned',
                    'created_at': task.created_at.strftime('%Y-%m-%d %H:%M')
                }
                tasks.append(task_dict)
            
            return {
                'success': True,
                'tasks': tasks
            }
        except Exception as e:
            return {
                'success': False,
                'tasks': [],
                'message': str(e)
            }
    
    def get_tasks_by_firm(self, firm_id: int, filters: dict = None) -> dict:
        """Get all tasks for a firm with optional filtering"""
        try:
            from src.models import Task, Project, User
            
            # Base query
            query = db.session.query(Task).join(Project).outerjoin(User).filter(
                Project.firm_id == firm_id
            )
            
            # Apply filters
            if filters:
                if 'status' in filters:
                    query = query.filter(Task.status == filters['status'])
                if 'assignee_id' in filters:
                    query = query.filter(Task.assignee_id == filters['assignee_id'])
                if 'project_id' in filters:
                    query = query.filter(Task.project_id == filters['project_id'])
                if 'priority' in filters:
                    query = query.filter(Task.priority == filters['priority'])
                if 'limit' in filters:
                    query = query.limit(filters['limit'])
            
            tasks = []
            for task in query.all():
                task_dict = {
                    'id': task.id,
                    'title': task.title,
                    'description': task.description,
                    'status': task.status,
                    'priority': task.priority,
                    'due_date': task.due_date.strftime('%Y-%m-%d') if task.due_date else None,
                    'project_id': task.project_id,
                    'project_name': task.project.name if task.project else '',
                    'assignee_id': task.assignee_id,
                    'assignee_name': task.assignee.name if task.assignee else 'Unassigned',
                    'created_at': task.created_at.strftime('%Y-%m-%d %H:%M'),
                    'estimated_hours': task.estimated_hours
                }
                tasks.append(task_dict)
            
            return {
                'success': True,
                'tasks': tasks
            }
        except Exception as e:
            return {
                'success': False,
                'tasks': [],
                'message': str(e)
            }

    def get_activity_logs_for_task(self, task_id: int, limit: int = 10) -> List['ActivityLog']:
        """Get recent activity logs for a task"""
        from src.models import ActivityLog
        return ActivityLog.query.filter_by(task_id=task_id).order_by(
            ActivityLog.timestamp.desc()
        ).limit(limit).all()
    
    @transactional
    def log_time_to_task(self, task_id: int, hours: float, user_id: int) -> Dict[str, Any]:
        """
        Log time to a task
        
        Args:
            task_id: ID of the task to log time to
            hours: Number of hours to log
            user_id: ID of the user logging time
            
        Returns:
            Dict containing success status and any error messages
        """
        try:
            # Validate inputs
            if not task_id or not hours or not user_id:
                return {
                    'success': False,
                    'message': 'Task ID, hours, and user ID are required'
                }
            
            if hours <= 0:
                return {
                    'success': False,
                    'message': 'Hours must be greater than 0'
                }
            
            # Get task to verify it exists
            task = Task.query.get(task_id)
            if not task:
                return {
                    'success': False,
                    'message': 'Task not found'
                }
            
            # For now, we'll log this as an activity (could be expanded to a separate TimeLog model)
            from src.shared.services import ActivityLoggingService as ActivityService
            activity_service = ActivityService()
            
            # Log the time as an activity
            activity_result = activity_service.log_activity(
                action=f'Time logged: {hours} hours',
                user_id=user_id,
                firm_id=task.firm_id,
                project_id=task.project_id,
                task_id=task_id,
                details=f'User logged {hours} hours to task "{task.title}"'
            )
            
            if activity_result['success']:
                return {
                    'success': True,
                    'message': f'Successfully logged {hours} hours to task',
                    'hours_logged': hours,
                    'task_id': task_id
                }
            else:
                return {
                    'success': False,
                    'message': f'Failed to log activity: {activity_result["message"]}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Error logging time: {str(e)}'
            }

    def get_task_comments(self, task_id: int) -> List['TaskComment']:
        """Get all comments for a task"""
        from src.models import TaskComment
        return TaskComment.query.filter_by(task_id=task_id).order_by(
            TaskComment.created_at.desc()
        ).all()
