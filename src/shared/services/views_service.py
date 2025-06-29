"""
Views Service for CPA WorkflowPilot
Handles view state management, user preferences, and UI customization.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from flask import session
from src.shared.database.db_import import db
from src.models import User
from src.shared.base import BaseService


class ViewsService(BaseService):
    """Service for managing user view preferences and UI state"""
    
    def __init__(self):
        super().__init__()
    
    def get_kanban_view_data(self, firm_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get data formatted for Kanban view
        
        Args:
            firm_id: Firm ID to get data for
            user_id: Optional user ID for personalized view
            
        Returns:
            Dict with kanban view data structure
        """
        # Import here to avoid circular imports
        from src.modules.project.task_service import TaskService
        from src.modules.project.service import ProjectService
        
        task_service = TaskService()
        project_service = ProjectService()
        
        # Get tasks grouped by status
        tasks_result = task_service.get_tasks_by_firm(firm_id)
        if not tasks_result['success']:
            return {
                'success': False,
                'message': tasks_result['message'],
                'columns': {}
            }
        
        tasks = tasks_result['tasks']
        
        # Group tasks by status for kanban columns
        kanban_columns = {
            'not_started': {
                'title': 'Not Started',
                'tasks': [],
                'color': 'gray'
            },
            'in_progress': {
                'title': 'In Progress',
                'tasks': [],
                'color': 'blue'
            },
            'needs_review': {
                'title': 'Needs Review',
                'tasks': [],
                'color': 'yellow'
            },
            'completed': {
                'title': 'Completed',
                'tasks': [],
                'color': 'green'
            }
        }
        
        # Categorize tasks
        for task in tasks:
            status = task.get('status', 'not_started').lower().replace(' ', '_')
            if status in kanban_columns:
                kanban_columns[status]['tasks'].append(task)
            else:
                # Default to not_started for unknown statuses
                kanban_columns['not_started']['tasks'].append(task)
        
        return {
            'success': True,
            'columns': kanban_columns,
            'total_tasks': len(tasks),
            'view_type': 'kanban'
        }
    
    def get_calendar_view_data(self, firm_id: int, month: Optional[int] = None, year: Optional[int] = None) -> Dict[str, Any]:
        """
        Get data formatted for calendar view
        
        Args:
            firm_id: Firm ID to get data for
            month: Optional month (1-12), defaults to current month
            year: Optional year, defaults to current year
            
        Returns:
            Dict with calendar view data structure
        """
        # Import here to avoid circular imports
        from src.modules.project.task_service import TaskService
        
        if not month or not year:
            now = datetime.now()
            month = month or now.month
            year = year or now.year
        
        task_service = TaskService()
        
        # Get tasks with due dates for the specified month/year
        tasks_result = task_service.get_tasks_by_firm(firm_id)
        if not tasks_result['success']:
            return {
                'success': False,
                'message': tasks_result['message'],
                'events': []
            }
        
        tasks = tasks_result['tasks']
        
        # Format tasks as calendar events
        calendar_events = []
        for task in tasks:
            if task.get('due_date'):
                try:
                    due_date = datetime.strptime(task['due_date'], '%Y-%m-%d') if isinstance(task['due_date'], str) else task['due_date']
                    if due_date.month == month and due_date.year == year:
                        event = {
                            'id': task['id'],
                            'title': task['title'],
                            'date': due_date.strftime('%Y-%m-%d'),
                            'type': 'task',
                            'status': task.get('status', 'Not Started'),
                            'project_name': task.get('project_name', ''),
                            'assignee': task.get('assignee_name', 'Unassigned')
                        }
                        calendar_events.append(event)
                except (ValueError, TypeError):
                    # Skip tasks with invalid date formats
                    continue
        
        return {
            'success': True,
            'events': calendar_events,
            'month': month,
            'year': year,
            'view_type': 'calendar'
        }
    
    def get_list_view_data(self, firm_id: int, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get data formatted for list view
        
        Args:
            firm_id: Firm ID to get data for
            filters: Optional filters to apply
            
        Returns:
            Dict with list view data structure
        """
        # Import here to avoid circular imports
        from src.modules.project.task_service import TaskService
        
        task_service = TaskService()
        
        # Apply filters if provided
        tasks_result = task_service.get_tasks_by_firm(firm_id, filters=filters)
        if not tasks_result['success']:
            return {
                'success': False,
                'message': tasks_result['message'],
                'tasks': []
            }
        
        tasks = tasks_result['tasks']
        
        # Sort tasks by priority and due date
        def sort_key(task):
            # Priority sorting (High=3, Medium=2, Low=1)
            priority_order = {'High': 3, 'Medium': 2, 'Low': 1}
            priority = priority_order.get(task.get('priority', 'Low'), 1)
            
            # Due date sorting (earlier dates first, None dates last)
            due_date = task.get('due_date')
            if due_date:
                try:
                    due_date_obj = datetime.strptime(due_date, '%Y-%m-%d') if isinstance(due_date, str) else due_date
                    return (-priority, due_date_obj)
                except (ValueError, TypeError):
                    return (-priority, datetime.max)
            else:
                return (-priority, datetime.max)
        
        sorted_tasks = sorted(tasks, key=sort_key)
        
        return {
            'success': True,
            'tasks': sorted_tasks,
            'total_count': len(sorted_tasks),
            'view_type': 'list'
        }
    
    def save_user_view_preference(self, user_id: int, firm_id: int, view_type: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save user's view preferences
        
        Args:
            user_id: User ID
            firm_id: Firm ID for validation
            view_type: Type of view (kanban, calendar, list)
            preferences: Dict of preference settings
            
        Returns:
            Dict with success status
        """
        # For now, store in session (could be moved to database later)
        if 'view_preferences' not in session:
            session['view_preferences'] = {}
        
        session['view_preferences'][view_type] = preferences
        session.permanent = True
        
        return {
            'success': True,
            'message': f'View preferences saved for {view_type}',
            'preferences': preferences
        }
    
    def get_user_view_preference(self, user_id: int, view_type: str) -> Dict[str, Any]:
        """
        Get user's view preferences
        
        Args:
            user_id: User ID
            view_type: Type of view (kanban, calendar, list)
            
        Returns:
            Dict with user preferences
        """
        # Get from session (could be moved to database later)
        view_preferences = session.get('view_preferences', {})
        preferences = view_preferences.get(view_type, {})
        
        # Default preferences
        default_preferences = {
            'kanban': {
                'columns_visible': ['not_started', 'in_progress', 'needs_review', 'completed'],
                'card_size': 'medium'
            },
            'calendar': {
                'default_view': 'month',
                'show_weekends': True
            },
            'list': {
                'items_per_page': 25,
                'sort_by': 'due_date',
                'sort_order': 'asc'
            }
        }
        
        # Merge with defaults
        final_preferences = default_preferences.get(view_type, {})
        final_preferences.update(preferences)
        
        return {
            'success': True,
            'preferences': final_preferences
        }