"""
Task service layer for business logic
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from flask import session
from core import db
from models import Task, Project, User, ActivityLog, TaskComment, TemplateTask
from services.activity_service import ActivityService


class TaskService:
    """Service class for task-related business operations"""
    
    @staticmethod
    def get_tasks_for_firm(firm_id: int) -> List[Task]:
        """Get all tasks for a firm"""
        return Task.query.filter_by(firm_id=firm_id).all()
    
    @staticmethod
    def get_task_by_id(task_id: int, firm_id: int) -> Optional[Task]:
        """Get a task by ID, ensuring it belongs to the firm"""
        return Task.query.filter_by(id=task_id, firm_id=firm_id).first()
    
    @staticmethod
    def update_task_status(task_id: int, status: str, firm_id: Optional[int] = None) -> Dict[str, Any]:
        """Update task status"""
        if firm_id is None:
            firm_id = session['firm_id']
        
        try:
            task = TaskService.get_task_by_id(task_id, firm_id)
            if not task:
                return {'success': False, 'message': 'Task not found'}
            
            old_status = task.status
            task.status = status
            db.session.commit()
            
            # Create activity log
            ActivityService.create_activity_log(
                action=f'Updated task "{task.title}" status from {old_status} to {status}',
                user_id=session.get('user_id'),
                task_id=task_id
            )
            
            return {'success': True, 'message': f'Task status updated to {status}'}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'Error updating task: {str(e)}'}
    
    @staticmethod
    def get_task_statistics(firm_id: Optional[int] = None) -> Dict[str, Any]:
        """Get task statistics for dashboard"""
        if firm_id is None:
            firm_id = session['firm_id']
        
        tasks = TaskService.get_tasks_for_firm(firm_id)
        
        stats = {
            'total': len(tasks),
            'not_started': len([t for t in tasks if t.status == 'Not Started']),
            'in_progress': len([t for t in tasks if t.status == 'In Progress']),
            'completed': len([t for t in tasks if t.status == 'Completed']),
            'overdue': len([t for t in tasks if t.is_overdue]),
        }
        
        return stats
    
    @staticmethod
    def get_filtered_tasks_optimized(firm_id: int, filters: Dict[str, Any] = None) -> List[Task]:
        """
        Get tasks with optimized eager loading to prevent N+1 queries
        
        Args:
            firm_id: The firm's ID
            filters: Dictionary of filter parameters
        
        Returns:
            List of filtered Task objects with eager loaded relationships
        """
        from sqlalchemy.orm import selectinload, joinedload
        
        if filters is None:
            filters = {}
        
        # Base query with eager loading for all relationships used in properties
        query = Task.query.options(
            joinedload(Task.project),  # For is_overdue, is_due_soon checks
            joinedload(Task.assignee),  # For assignee info
            joinedload(Task.task_status_ref),  # For status properties
            selectinload(Task.subtasks)  # For subtask operations
        ).outerjoin(Project).filter(
            db.or_(
                Project.firm_id == firm_id,
                db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            )
        )
        
        # Apply filters (same as original method)
        if not filters.get('show_completed', False):
            query = query.filter(Task.status != 'Completed')
        
        if filters.get('status_filters'):
            query = query.filter(Task.status.in_(filters['status_filters']))
        
        if filters.get('priority_filters'):
            query = query.filter(Task.priority.in_(filters['priority_filters']))
        
        if filters.get('assignee_filters'):
            assignee_conditions = []
            if 'unassigned' in filters['assignee_filters']:
                assignee_conditions.append(Task.assignee_id.is_(None))
            
            user_ids = [f for f in filters['assignee_filters'] if f != 'unassigned']
            if user_ids:
                assignee_conditions.append(Task.assignee_id.in_(user_ids))
            
            if assignee_conditions:
                query = query.filter(db.or_(*assignee_conditions))
        
        if filters.get('project_filters'):
            project_conditions = []
            if 'independent' in filters['project_filters']:
                project_conditions.append(Task.project_id.is_(None))
            
            project_ids = [f for f in filters['project_filters'] if f != 'independent']
            if project_ids:
                project_conditions.append(Task.project_id.in_(project_ids))
            
            if project_conditions:
                query = query.filter(db.or_(*project_conditions))
        
        # Date-based filters
        today = date.today()
        if filters.get('overdue_filter') == 'true':
            query = query.filter(
                Task.due_date < today, 
                Task.status != 'Completed',
                db.or_(
                    Task.project_id.is_(None),
                    Project.status != 'Completed'
                )
            )
        elif filters.get('due_date_filter') == 'today':
            query = query.filter(Task.due_date == today)
        elif filters.get('due_date_filter') == 'soon':
            soon_date = today + timedelta(days=3)
            query = query.filter(Task.due_date.between(today, soon_date))
        
        # Get all tasks with optimized ordering
        all_tasks = query.order_by(
            Task.due_date.asc().nullslast(),
            db.case(
                (Task.priority == 'High', 1),
                (Task.priority == 'Medium', 2),
                (Task.priority == 'Low', 3),
                else_=4
            )
        ).all()
        
        # Filter to show only current active task per interdependent project
        tasks = []
        seen_projects = set()
        
        for task in all_tasks:
            if task.project and task.project.task_dependency_mode:
                if task.project_id not in seen_projects and not task.is_completed:
                    tasks.append(task)
                    seen_projects.add(task.project_id)
            else:
                tasks.append(task)
        
        return tasks
    
    @staticmethod
    def get_filtered_tasks(firm_id: int, filters: Dict[str, Any] = None) -> List[Task]:
        """
        Get tasks with various filters applied
        
        Args:
            firm_id: The firm's ID
            filters: Dictionary of filter parameters
        
        Returns:
            List of filtered Task objects
        """
        if filters is None:
            filters = {}
        
        # Base query - include both project tasks and independent tasks
        query = Task.query.outerjoin(Project).filter(
            db.or_(
                Project.firm_id == firm_id,
                db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            )
        )
        
        # Hide completed tasks by default
        if not filters.get('show_completed', False):
            query = query.filter(Task.status != 'Completed')
        
        # Apply multi-select filters
        if filters.get('status_filters'):
            query = query.filter(Task.status.in_(filters['status_filters']))
        
        if filters.get('priority_filters'):
            query = query.filter(Task.priority.in_(filters['priority_filters']))
        
        if filters.get('assignee_filters'):
            assignee_conditions = []
            if 'unassigned' in filters['assignee_filters']:
                assignee_conditions.append(Task.assignee_id.is_(None))
            
            user_ids = [f for f in filters['assignee_filters'] if f != 'unassigned']
            if user_ids:
                assignee_conditions.append(Task.assignee_id.in_(user_ids))
            
            if assignee_conditions:
                query = query.filter(db.or_(*assignee_conditions))
        
        if filters.get('project_filters'):
            project_conditions = []
            if 'independent' in filters['project_filters']:
                project_conditions.append(Task.project_id.is_(None))
            
            project_ids = [f for f in filters['project_filters'] if f != 'independent']
            if project_ids:
                project_conditions.append(Task.project_id.in_(project_ids))
            
            if project_conditions:
                query = query.filter(db.or_(*project_conditions))
        
        # Date-based filters
        today = date.today()
        if filters.get('overdue_filter') == 'true':
            query = query.filter(
                Task.due_date < today, 
                Task.status != 'Completed',
                db.or_(
                    Task.project_id.is_(None),
                    Project.status != 'Completed'
                )
            )
        elif filters.get('due_date_filter') == 'today':
            query = query.filter(Task.due_date == today)
        elif filters.get('due_date_filter') == 'soon':
            soon_date = today + timedelta(days=3)
            query = query.filter(Task.due_date.between(today, soon_date))
        
        # Get all tasks first
        all_tasks = query.order_by(
            Task.due_date.asc().nullslast(),
            db.case(
                (Task.priority == 'High', 1),
                (Task.priority == 'Medium', 2),
                (Task.priority == 'Low', 3),
                else_=4
            )
        ).all()
        
        # Filter to show only current active task per interdependent project
        tasks = []
        seen_projects = set()
        
        for task in all_tasks:
            if task.project and task.project.task_dependency_mode:
                if task.project_id not in seen_projects and not task.is_completed:
                    tasks.append(task)
                    seen_projects.add(task.project_id)
            else:
                tasks.append(task)
        
        return tasks
    
    @staticmethod
    def create_task_from_form(form_data: Dict[str, Any], firm_id: int, user_id: int) -> Dict[str, Any]:
        """
        Create a task from form data with comprehensive validation and processing
        
        Args:
            form_data: Form data dictionary from request.form
            firm_id: The firm's ID
            user_id: The creating user's ID
            
        Returns:
            Dict containing success status, task data, and any error messages
        """
        try:
            # Extract form data
            title = form_data.get('title', '').strip()
            description = form_data.get('description', '').strip()
            project_id = form_data.get('project_id')
            assignee_id = form_data.get('assignee_id')
            priority = form_data.get('priority', 'Medium')
            due_date_str = form_data.get('due_date')
            estimated_hours_str = form_data.get('estimated_hours')
            
            # Recurring task options
            is_recurring = form_data.get('is_recurring') == 'on'
            recurrence_rule = form_data.get('recurrence_rule')
            recurrence_interval_str = form_data.get('recurrence_interval')
            
            # Validate required fields
            if not title:
                return {
                    'success': False,
                    'message': 'Task title is required'
                }
            
            # Parse due date
            due_date_obj = None
            if due_date_str:
                try:
                    due_date_obj = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                except ValueError:
                    return {
                        'success': False,
                        'message': 'Invalid due date format'
                    }
            
            # Parse estimated hours
            estimated_hours_float = None
            if estimated_hours_str:
                try:
                    estimated_hours_float = float(estimated_hours_str)
                except ValueError:
                    estimated_hours_float = None
            
            # Parse project ID
            project_id_int = None
            if project_id:
                try:
                    project_id_int = int(project_id)
                except ValueError:
                    return {
                        'success': False,
                        'message': 'Invalid project selected'
                    }
            
            # Parse assignee ID
            assignee_id_int = None
            if assignee_id:
                try:
                    assignee_id_int = int(assignee_id)
                except ValueError:
                    assignee_id_int = None
            
            # Parse recurrence interval
            recurrence_interval_int = None
            if is_recurring and recurrence_interval_str:
                try:
                    recurrence_interval_int = int(recurrence_interval_str)
                except ValueError:
                    recurrence_interval_int = 1
            
            # Call the core create_task method
            return TaskService.create_task(
                title=title,
                description=description,
                firm_id=firm_id,
                user_id=user_id,
                project_id=project_id_int,
                assignee_id=assignee_id_int,
                priority=priority,
                due_date=due_date_obj,
                estimated_hours=estimated_hours_float,
                is_recurring=is_recurring,
                recurrence_rule=recurrence_rule,
                recurrence_interval=recurrence_interval_int
            )
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error processing form data: {str(e)}'
            }
    
    @staticmethod
    def create_task(title: str, description: str, firm_id: int, user_id: int,
                   project_id: Optional[int] = None, assignee_id: Optional[int] = None,
                   priority: str = 'Medium', due_date: Optional[date] = None,
                   estimated_hours: Optional[float] = None,
                   is_recurring: bool = False, recurrence_rule: Optional[str] = None,
                   recurrence_interval: Optional[int] = None) -> Dict[str, Any]:
        """
        Create a new task with comprehensive business logic
        
        Args:
            title: Task title
            description: Task description
            firm_id: The firm's ID
            user_id: The creating user's ID
            project_id: Optional project ID
            assignee_id: Optional assignee user ID
            priority: Task priority (High, Medium, Low)
            due_date: Optional due date
            estimated_hours: Optional estimated hours
            is_recurring: Whether task is recurring
            recurrence_rule: Recurrence rule if recurring
            recurrence_interval: Recurrence interval if recurring
            
        Returns:
            Dict containing success status, task data, and any error messages
        """
        try:
            # Input validation
            if not title or not title.strip():
                return {
                    'success': False,
                    'message': 'Task title is required'
                }
            
            # Verify project belongs to firm (if project selected)
            if project_id:
                project = Project.query.filter_by(id=project_id, firm_id=firm_id).first()
                if not project:
                    return {
                        'success': False,
                        'message': 'Invalid project selected'
                    }
            
            # Validate estimated hours
            if estimated_hours is not None:
                try:
                    estimated_hours = float(estimated_hours) if estimated_hours else None
                except (ValueError, TypeError):
                    estimated_hours = None
            
            # Validate recurrence interval
            if is_recurring and recurrence_interval:
                try:
                    recurrence_interval = int(recurrence_interval)
                except (ValueError, TypeError):
                    recurrence_interval = 1
            
            # Create task
            task = Task(
                title=title.strip(),
                description=description.strip() if description else None,
                due_date=due_date,
                priority=priority,
                estimated_hours=estimated_hours,
                project_id=project_id,
                firm_id=firm_id,
                assignee_id=assignee_id if assignee_id else None,
                is_recurring=is_recurring,
                recurrence_rule=recurrence_rule if is_recurring else None,
                recurrence_interval=recurrence_interval if is_recurring else None
            )
            
            # Calculate next due date for recurring tasks after object creation
            if is_recurring:
                task.next_due_date = task.calculate_next_due_date()
                
                # Create the first upcoming instance immediately
                next_instance = task.create_next_instance()
                if next_instance:
                    db.session.add(next_instance)
            
            db.session.add(task)
            db.session.commit()
            
            # Activity log
            if project_id:
                from utils import create_activity_log
                create_activity_log(f'Task "{task.title}" created', user_id, project_id, task.id)
            else:
                from utils import create_activity_log
                create_activity_log(f'Independent task "{task.title}" created', user_id, None, task.id)
            
            return {
                'success': True,
                'message': 'Task created successfully',
                'task': {
                    'id': task.id,
                    'title': task.title
                }
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error creating task: {str(e)}'
            }
    
    @staticmethod
    def get_task_by_id_with_access_check(task_id: int, firm_id: int) -> Optional[Task]:
        """
        Get a task by ID with access control for both project and independent tasks
        
        Args:
            task_id: The task's ID
            firm_id: The firm's ID for security check
            
        Returns:
            Task object if found and accessible, None otherwise
        """
        task = Task.query.get(task_id)
        if not task:
            return None
        
        # Check access for both project tasks and independent tasks
        if task.project and task.project.firm_id != firm_id:
            return None
        elif not task.project and task.firm_id != firm_id:
            return None
        
        return task
    
    @staticmethod
    def update_task_from_form(task_id: int, form_data: Dict[str, Any], firm_id: int, user_id: int) -> Dict[str, Any]:
        """
        Update a task from form data with comprehensive validation and processing
        
        Args:
            task_id: The task's ID
            form_data: Form data dictionary from request.form
            firm_id: The firm's ID for security check
            user_id: The updating user's ID
            
        Returns:
            Dict containing success status and any error messages
        """
        try:
            task = TaskService.get_task_by_id_with_access_check(task_id, firm_id)
            if not task:
                return {
                    'success': False,
                    'message': 'Task not found or access denied'
                }
            
            # Track original values for change detection
            original_assignee_id = task.assignee_id
            original_assignee_name = task.assignee.name if task.assignee else 'Unassigned'
            original_status = task.status
            
            # Extract and validate form data
            title = form_data.get('title', '').strip()
            if not title:
                return {
                    'success': False,
                    'message': 'Task title is required'
                }
            
            # Update basic fields
            task.title = title
            task.description = form_data.get('description', '').strip()
            task.priority = form_data.get('priority', 'Medium')
            
            # Handle assignee
            assignee_id = form_data.get('assignee_id')
            new_assignee_id = int(assignee_id) if assignee_id else None
            task.assignee_id = new_assignee_id
            
            # Handle status
            new_status = form_data.get('status', task.status)
            task.status = new_status
            
            # Handle due date
            due_date_str = form_data.get('due_date')
            if due_date_str:
                try:
                    task.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                except ValueError:
                    return {
                        'success': False,
                        'message': 'Invalid due date format'
                    }
            else:
                task.due_date = None
            
            # Handle estimated hours
            estimated_hours_str = form_data.get('estimated_hours')
            if estimated_hours_str:
                try:
                    task.estimated_hours = float(estimated_hours_str)
                except ValueError:
                    task.estimated_hours = None
            else:
                task.estimated_hours = None
            
            # Handle comments
            comments = form_data.get('comments')
            if comments:
                task.comments = comments
            
            # Handle dependencies (only for project tasks)
            if task.project_id:
                dependencies = form_data.getlist('dependencies')
                if dependencies:
                    # Validate dependencies - ensure no circular dependencies
                    valid_dependencies = []
                    for dep_id in dependencies:
                        try:
                            dep_id = int(dep_id)
                            dep_task = Task.query.filter_by(id=dep_id, project_id=task.project_id).first()
                            if dep_task and dep_id != task.id:
                                # Check for circular dependency - simple check for now
                                valid_dependencies.append(str(dep_id))
                        except ValueError:
                            pass
                    task.dependencies = ','.join(valid_dependencies) if valid_dependencies else None
                else:
                    task.dependencies = None
            
            # Handle sequential task dependencies before committing
            TaskService._handle_sequential_dependencies(task, original_status, new_status)
            
            db.session.commit()
            
            # Log assignee change if it occurred
            if original_assignee_id != new_assignee_id:
                new_assignee_name = task.assignee.name if task.assignee else 'Unassigned'
                assignee_log_msg = f'Task "{task.title}" assignee changed from "{original_assignee_name}" to "{new_assignee_name}"'
                if task.project_id:
                    from utils import create_activity_log
                    create_activity_log(assignee_log_msg, user_id, task.project_id, task.id)
                else:
                    from utils import create_activity_log
                    create_activity_log(assignee_log_msg, user_id, None, task.id)
            
            # General activity log
            if task.project_id:
                from utils import create_activity_log
                create_activity_log(f'Task "{task.title}" updated', user_id, task.project_id, task.id)
            else:
                from utils import create_activity_log
                create_activity_log(f'Independent task "{task.title}" updated', user_id, None, task.id)
            
            return {
                'success': True,
                'message': 'Task updated successfully',
                'task': {
                    'id': task.id,
                    'title': task.title
                }
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error updating task: {str(e)}'
            }
    
    @staticmethod
    def update_task(task_id: int, firm_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a task with the provided changes
        
        Args:
            task_id: The task's ID
            firm_id: The firm's ID for security check
            updates: Dictionary of field updates
            
        Returns:
            Dict containing success status and any error messages
        """
        try:
            task = TaskService.get_task_by_id_with_access_check(task_id, firm_id)
            if not task:
                return {
                    'success': False,
                    'message': 'Task not found or access denied'
                }
            
            # Track changes for activity logging
            changes = []
            original_assignee_id = task.assignee_id
            original_status = task.status
            
            # Apply updates
            for field, value in updates.items():
                if hasattr(task, field):
                    old_value = getattr(task, field)
                    if old_value != value:
                        setattr(task, field, value)
                        changes.append(f"{field}: {old_value} → {value}")
            
            # Handle sequential task dependencies if status changed
            if 'status' in updates and original_status != updates['status']:
                TaskService._handle_sequential_dependencies(task, original_status, updates['status'])
            
            db.session.commit()
            
            # Log specific changes
            if original_assignee_id != task.assignee_id:
                original_assignee_name = User.query.get(original_assignee_id).name if original_assignee_id else 'Unassigned'
                new_assignee_name = task.assignee.name if task.assignee else 'Unassigned'
                assignee_log_msg = f'Task "{task.title}" assignee changed from "{original_assignee_name}" to "{new_assignee_name}"'
                
                if task.project_id:
                    create_activity_log(assignee_log_msg, session['user_id'], task.project_id, task.id)
                else:
                    create_activity_log(assignee_log_msg, session['user_id'], None, task.id)
            
            # General activity log
            if task.project_id:
                create_activity_log(f'Task "{task.title}" updated', session['user_id'], task.project_id, task.id)
            else:
                create_activity_log(f'Independent task "{task.title}" updated', session['user_id'], None, task.id)
            
            return {
                'success': True,
                'message': 'Task updated successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error updating task: {str(e)}'
            }
    
    @staticmethod
    def delete_task(task_id: int, firm_id: int) -> Dict[str, Any]:
        """
        Delete a task and its associated data
        
        Args:
            task_id: The task's ID
            firm_id: The firm's ID for security check
            
        Returns:
            Dict containing success status and any error messages
        """
        try:
            task = TaskService.get_task_by_id_with_access_check(task_id, firm_id)
            if not task:
                return {
                    'success': False,
                    'message': 'Task not found or access denied'
                }
            
            task_title = task.title
            project_id = task.project_id
            
            # Create activity log before deletion
            if project_id:
                create_activity_log(f'Task "{task_title}" deleted', session['user_id'], project_id)
            else:
                create_activity_log(f'Independent task "{task_title}" deleted', session['user_id'])
            
            # Delete associated comments first
            TaskComment.query.filter_by(task_id=task_id).delete()
            
            # Delete the task
            db.session.delete(task)
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Task deleted successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error deleting task: {str(e)}'
            }
    
    @staticmethod
    def add_task_comment(task_id: int, firm_id: int, comment_text: str, user_id: int) -> Dict[str, Any]:
        """
        Add a comment to a task
        
        Args:
            task_id: The task's ID
            firm_id: The firm's ID for security check
            comment_text: The comment text
            user_id: The user adding the comment
            
        Returns:
            Dict containing success status, comment data, and any error messages
        """
        try:
            task = TaskService.get_task_by_id_with_access_check(task_id, firm_id)
            if not task:
                return {
                    'success': False,
                    'message': 'Task not found or access denied'
                }
            
            if not comment_text.strip():
                return {
                    'success': False,
                    'message': 'Comment cannot be empty'
                }
            
            # Create comment
            comment = TaskComment(
                comment=comment_text.strip(),
                task_id=task.id,
                user_id=user_id
            )
            db.session.add(comment)
            
            # Create activity log
            create_activity_log(
                f'Comment added to task "{task.title}"',
                user_id,
                task.project_id if task.project_id else None,
                task.id
            )
            
            db.session.commit()
            
            return {
                'success': True,
                'comment': {
                    'id': comment.id,
                    'comment': comment.comment,
                    'user_name': comment.user.name,
                    'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M:%S')
                }
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error adding comment: {str(e)}'
            }
    
    @staticmethod
    def _handle_sequential_dependencies(task: Task, old_status: str, new_status: str) -> None:
        """Handle sequential task dependencies when task status changes"""
        if not task.project_id or not task.project:
            return
        
        # Check if project has task dependency mode enabled
        if not task.project.task_dependency_mode:
            return
        
        # Get all tasks in the project ordered by creation/position
        project_tasks = Task.query.filter_by(project_id=task.project_id).order_by(Task.id.asc()).all()
        
        # Find current task position
        current_task_index = None
        for i, t in enumerate(project_tasks):
            if t.id == task.id:
                current_task_index = i
                break
        
        if current_task_index is None:
            return
        
        # If task is marked as completed
        if new_status == 'Completed' and old_status != 'Completed':
            # Mark all previous tasks as completed
            for i in range(current_task_index):
                prev_task = project_tasks[i]
                if prev_task.status != 'Completed':
                    prev_task.status = 'Completed'
                    create_activity_log(
                        f'Task "{prev_task.title}" auto-completed due to sequential dependency',
                        session.get('user_id', 1),
                        task.project_id,
                        prev_task.id
                    )
        
        # If task is marked as not started or in progress
        elif new_status in ['Not Started', 'In Progress'] and old_status == 'Completed':
            # Mark all subsequent tasks as not started
            for i in range(current_task_index + 1, len(project_tasks)):
                next_task = project_tasks[i]
                if next_task.status == 'Completed':
                    next_task.status = 'Not Started'
                    create_activity_log(
                        f'Task "{next_task.title}" reset due to sequential dependency',
                        session.get('user_id', 1),
                        task.project_id,
                        next_task.id
                    )
    
    @staticmethod
    def get_task_dependencies_optimized(task_ids: List[int], firm_id: int) -> Dict[int, Dict[str, Any]]:
        """
        Get dependency information for multiple tasks efficiently to avoid N+1 queries
        
        Args:
            task_ids: List of task IDs to get dependencies for
            firm_id: The firm's ID for security
            
        Returns:
            Dict mapping task_id to dependency info: {task_id: {'is_blocked': bool, 'blocking_count': int}}
        """
        if not task_ids:
            return {}
        
        # Get all tasks with their dependencies
        tasks = Task.query.filter(
            Task.id.in_(task_ids),
            db.or_(
                Task.firm_id == firm_id,
                db.and_(Task.project_id.isnot(None), Task.project.has(firm_id=firm_id))
            )
        ).all()
        
        # Collect all dependency task IDs
        all_dependency_ids = set()
        task_dependencies = {}
        
        for task in tasks:
            if task.dependencies:
                deps = [int(id.strip()) for id in task.dependencies.split(',') if id.strip()]
                task_dependencies[task.id] = deps
                all_dependency_ids.update(deps)
            else:
                task_dependencies[task.id] = []
        
        # Get completion status of all dependency tasks in one query
        dependency_completion = {}
        if all_dependency_ids:
            dependency_tasks = Task.query.filter(
                Task.id.in_(all_dependency_ids),
                Task.firm_id == firm_id
            ).all()
            
            dependency_completion = {
                task.id: task.is_completed for task in dependency_tasks
            }
        
        # Build blocking relationships - find tasks that depend on our tasks
        blocking_counts = {}
        if task_ids:
            # Query for tasks that have dependencies on our task IDs
            blocking_tasks = Task.query.filter(
                Task.dependencies.isnot(None),
                Task.firm_id == firm_id
            ).all()
            
            for task_id in task_ids:
                blocking_counts[task_id] = 0
                
            for blocking_task in blocking_tasks:
                if blocking_task.dependencies:
                    deps = [int(id.strip()) for id in blocking_task.dependencies.split(',') if id.strip()]
                    for dep_id in deps:
                        if dep_id in blocking_counts and not blocking_task.is_completed:
                            blocking_counts[dep_id] += 1
        
        # Calculate results
        result = {}
        for task in tasks:
            task_deps = task_dependencies[task.id]
            is_blocked = False
            
            if task_deps:
                # Task is blocked if any dependency is not completed
                is_blocked = any(
                    not dependency_completion.get(dep_id, False) 
                    for dep_id in task_deps
                )
            
            result[task.id] = {
                'is_blocked': is_blocked,
                'blocking_count': blocking_counts.get(task.id, 0),
                'dependency_ids': task_deps
            }
        
        return result
    
    @staticmethod
    def get_tasks_with_dependency_info(firm_id: int, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Get tasks with all dependency information pre-calculated to avoid N+1 queries
        
        Args:
            firm_id: The firm's ID
            filters: Dictionary of filter parameters
            
        Returns:
            List of dictionaries containing task data and dependency info
        """
        # Get optimized tasks
        tasks = TaskService.get_filtered_tasks_optimized(firm_id, filters)
        
        if not tasks:
            return []
        
        # Get dependency info for all tasks in one batch
        task_ids = [task.id for task in tasks]
        dependency_info = TaskService.get_task_dependencies_optimized(task_ids, firm_id)
        
        # Combine task data with dependency info
        result = []
        for task in tasks:
            task_data = {
                'task': task,
                'dependency_info': dependency_info.get(task.id, {
                    'is_blocked': False,
                    'blocking_count': 0,
                    'dependency_ids': []
                })
            }
            result.append(task_data)
        
        return result
    
    @staticmethod
    def calculate_task_due_date(project_start_date: date, template_task: TemplateTask) -> Optional[date]:
        """Calculate due date for a task based on project start and template settings"""
        if template_task.days_from_start:
            return project_start_date + timedelta(days=template_task.days_from_start)
        elif template_task.recurrence_rule:
            return TaskService.calculate_next_due_date(template_task.recurrence_rule, project_start_date)
        return None
    
    @staticmethod
    def calculate_next_due_date(recurrence_rule: str, base_date: Optional[date] = None) -> Optional[date]:
        """Calculate next due date based on recurrence rule"""
        if not recurrence_rule:
            return None
        
        if base_date is None:
            base_date = date.today()
        
        parts = recurrence_rule.split(':')
        frequency = parts[0]
        
        if frequency == 'daily':
            return base_date + timedelta(days=1)
        
        elif frequency == 'weekly':
            return base_date + timedelta(weeks=1)
        
        elif frequency == 'monthly':
            if len(parts) > 1:
                day = parts[1]
                if day == 'last_day':
                    next_month = base_date.replace(day=1) + relativedelta(months=1)
                    return next_month.replace(day=calendar.monthrange(next_month.year, next_month.month)[1])
                elif day == 'last_biz_day':
                    next_month = base_date.replace(day=1) + relativedelta(months=1)
                    last_day = next_month.replace(day=calendar.monthrange(next_month.year, next_month.month)[1])
                    while last_day.weekday() > 4:  # Saturday = 5, Sunday = 6
                        last_day -= timedelta(days=1)
                    return last_day
                else:
                    try:
                        day_num = int(day)
                        next_month = base_date.replace(day=1) + relativedelta(months=1)
                        max_day = calendar.monthrange(next_month.year, next_month.month)[1]
                        actual_day = min(day_num, max_day)
                        return next_month.replace(day=actual_day)
                    except ValueError:
                        pass
            return base_date + relativedelta(months=1)
        
        elif frequency == 'quarterly':
            if len(parts) > 1 and parts[1] == 'last_biz_day':
                next_quarter_start = base_date.replace(day=1) + relativedelta(months=3)
                quarter_end_month = ((next_quarter_start.month - 1) // 3 + 1) * 3
                quarter_end = next_quarter_start.replace(month=quarter_end_month)
                quarter_end = quarter_end.replace(day=calendar.monthrange(quarter_end.year, quarter_end.month)[1])
                while quarter_end.weekday() > 4:
                    quarter_end -= timedelta(days=1)
                return quarter_end
            return base_date + relativedelta(months=3)
        
        elif frequency == 'annually':
            return base_date + relativedelta(years=1)
        
        return None
    
    @staticmethod
    def process_recurring_tasks() -> Dict[str, Any]:
        """Process both template-based and standalone recurring tasks"""
        try:
            tasks_created = 0
            
            # Process template-based recurring tasks
            template_tasks = TemplateTask.query.filter(TemplateTask.recurrence_rule.isnot(None)).all()
            
            for template_task in template_tasks:
                last_generated = Task.query.filter_by(
                    template_task_origin_id=template_task.id
                ).order_by(Task.due_date.desc()).first()
                
                if last_generated:
                    next_due = TaskService.calculate_next_due_date(template_task.recurrence_rule, last_generated.due_date)
                else:
                    next_due = TaskService.calculate_next_due_date(template_task.recurrence_rule)
                
                if next_due and next_due <= date.today():
                    projects = Project.query.filter_by(
                        template_origin_id=template_task.template_id,
                        status='Active'
                    ).all()
                    
                    for project in projects:
                        existing_task = Task.query.filter_by(
                            project_id=project.id,
                            template_task_origin_id=template_task.id,
                            due_date=next_due
                        ).first()
                        
                        if not existing_task:
                            task = Task(
                                title=template_task.title,
                                description=template_task.description,
                                due_date=next_due,
                                project_id=project.id,
                                assignee_id=template_task.default_assignee_id,
                                template_task_origin_id=template_task.id,
                                firm_id=project.firm_id
                            )
                            db.session.add(task)
                            tasks_created += 1
            
            db.session.commit()
            
            return {
                'success': True,
                'tasks_created': tasks_created,
                'message': f'Created {tasks_created} recurring tasks'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': f'Failed to process recurring tasks: {str(e)}'
            }
    
    @staticmethod
    def bulk_update_tasks(task_ids: List[int], updates: Dict[str, Any], firm_id: int, user_id: int) -> Dict[str, Any]:
        """
        Bulk update multiple tasks with the provided changes
        
        Args:
            task_ids: List of task IDs to update
            updates: Dictionary of field updates to apply to all tasks
            firm_id: The firm's ID for security check
            user_id: The updating user's ID
            
        Returns:
            Dict containing success status and any error messages
        """
        try:
            if not task_ids:
                return {
                    'success': False,
                    'message': 'No tasks selected'
                }
            
            # Get tasks that belong to the firm
            tasks = Task.query.outerjoin(Project).filter(
                Task.id.in_(task_ids),
                db.or_(
                    Project.firm_id == firm_id,
                    db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
                )
            ).all()
            
            if not tasks:
                return {
                    'success': False,
                    'message': 'No valid tasks found'
                }
            
            updated_count = 0
            for task in tasks:
                # Update status if provided
                if 'status' in updates:
                    old_status = task.status
                    task.status = updates['status']
                    if old_status != task.status:
                        # Log status change
                        from utils import create_activity_log
                        create_activity_log(
                            f'Task "{task.title}" status changed from "{old_status}" to "{task.status}" (bulk update)',
                            user_id,
                            task.project_id if task.project_id else None,
                            task.id
                        )
                
                # Update assignee if provided
                if 'assignee_id' in updates:
                    old_assignee_name = task.assignee.name if task.assignee else 'Unassigned'
                    task.assignee_id = updates['assignee_id'] if updates['assignee_id'] else None
                    new_assignee_name = task.assignee.name if task.assignee else 'Unassigned'
                    if old_assignee_name != new_assignee_name:
                        # Log assignee change
                        from utils import create_activity_log
                        create_activity_log(
                            f'Task "{task.title}" assignee changed from "{old_assignee_name}" to "{new_assignee_name}" (bulk update)',
                            user_id,
                            task.project_id if task.project_id else None,
                            task.id
                        )
                
                # Update priority if provided
                if 'priority' in updates:
                    old_priority = task.priority
                    task.priority = updates['priority']
                    if old_priority != task.priority:
                        # Log priority change
                        from utils import create_activity_log
                        create_activity_log(
                            f'Task "{task.title}" priority changed from "{old_priority}" to "{task.priority}" (bulk update)',
                            user_id,
                            task.project_id if task.project_id else None,
                            task.id
                        )
                
                updated_count += 1
            
            db.session.commit()
            
            return {
                'success': True,
                'message': f'Successfully updated {updated_count} tasks'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error updating tasks: {str(e)}'
            }
    
    @staticmethod
    def bulk_delete_tasks(task_ids: List[int], firm_id: int, user_id: int) -> Dict[str, Any]:
        """
        Bulk delete multiple tasks and their associated data
        
        Args:
            task_ids: List of task IDs to delete
            firm_id: The firm's ID for security check
            user_id: The deleting user's ID
            
        Returns:
            Dict containing success status and any error messages
        """
        try:
            if not task_ids:
                return {
                    'success': False,
                    'message': 'No tasks selected'
                }
            
            # Get tasks that belong to the firm
            tasks = Task.query.outerjoin(Project).filter(
                Task.id.in_(task_ids),
                db.or_(
                    Project.firm_id == firm_id,
                    db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
                )
            ).all()
            
            if not tasks:
                return {
                    'success': False,
                    'message': 'No valid tasks found'
                }
            
            deleted_count = 0
            for task in tasks:
                # Log deletion
                from utils import create_activity_log
                create_activity_log(
                    f'Task "{task.title}" deleted (bulk operation)',
                    user_id,
                    task.project_id if task.project_id else None,
                    None  # task_id will be None since task is being deleted
                )
                
                # Delete associated comments first
                TaskComment.query.filter_by(task_id=task.id).delete()
                
                # Delete the task
                db.session.delete(task)
                deleted_count += 1
            
            db.session.commit()
            
            return {
                'success': True,
                'message': f'Successfully deleted {deleted_count} tasks'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Error deleting tasks: {str(e)}'
            }