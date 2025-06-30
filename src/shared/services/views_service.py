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
        # Use service registry to avoid circular imports and coupling
        from src.shared.bootstrap import get_task_service, get_project_service
        
        task_service = get_task_service()
        project_service = get_project_service()
        
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
        Get data formatted for calendar view - OPTIMIZED to filter at database level
        
        Args:
            firm_id: Firm ID to get data for
            month: Optional month (1-12), defaults to current month
            year: Optional year, defaults to current year
            
        Returns:
            Dict with calendar view data structure
        """
        if not month or not year:
            now = datetime.now()
            month = month or now.month
            year = year or now.year
        
        # Calculate date range for the requested month
        from datetime import date
        from calendar import monthrange
        
        start_date = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end_date = date(year, month, last_day)
        
        # Use optimized repository method to filter at database level
        from src.modules.project.task_repository import TaskRepository
        task_repo = TaskRepository()
        tasks = task_repo.get_tasks_by_date_range(firm_id, start_date, end_date)
        
        # Format tasks as calendar events (much smaller dataset now!)
        calendar_events = []
        for task in tasks:
            if task.due_date:
                event = {
                    'id': task.id,
                    'title': task.title,
                    'date': task.due_date.strftime('%Y-%m-%d'),
                    'type': 'task',
                    'status': task.status,
                    'project_name': task.project.name if task.project else '',
                    'assignee': task.assignee.name if task.assignee else 'Unassigned'
                }
                calendar_events.append(event)
        
        return {
            'success': True,
            'events': calendar_events,
            'month': month,
            'year': year,
            'view_type': 'calendar'
        }
    
    def get_list_view_data(self, firm_id: int, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get data formatted for list view - OPTIMIZED to filter and sort at database level
        
        Args:
            firm_id: Firm ID to get data for
            filters: Optional filters to apply
            
        Returns:
            Dict with list view data structure
        """
        # Use optimized repository method to filter AND sort at database level
        from src.modules.project.task_repository import TaskRepository
        task_repo = TaskRepository()
        
        # Get filtered and sorted tasks directly from database
        limit = filters.get('limit') if filters else None
        tasks = task_repo.get_filtered_tasks(firm_id, filters, limit)
        
        # Convert to DTOs to prevent N+1 queries
        task_dtos = []
        for task in tasks:
            task_dto = {
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
                'created_at': task.created_at.strftime('%Y-%m-%d %H:%M') if task.created_at else None,
                'estimated_hours': task.estimated_hours
            }
            task_dtos.append(task_dto)
        
        return {
            'success': True,
            'tasks': task_dtos,
            'total_count': len(task_dtos),
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
    
    @staticmethod
    def get_time_tracking_data(firm_id: int, start_date: str = None, end_date: str = None, 
                             user_id: int = None, project_id: int = None) -> Dict[str, Any]:
        """
        Get time tracking data for specified parameters
        
        Args:
            firm_id: Firm ID to get data for
            start_date: Optional start date filter
            end_date: Optional end date filter
            user_id: Optional user ID filter
            project_id: Optional project ID filter
            
        Returns:
            Dict containing time tracking data
        """
        try:
            # For now, return empty data structure
            # This can be expanded when time tracking is fully implemented
            return {
                'success': True,
                'time_entries': [],
                'total_hours': 0,
                'filters': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'user_id': user_id,
                    'project_id': project_id
                }
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error getting time tracking data: {str(e)}',
                'time_entries': [],
                'total_hours': 0
            }
    
    @staticmethod
    def get_kanban_data(firm_id: int, work_type_filter: str = None, 
                       priority_filter: str = None, due_filter: str = None) -> Dict[str, Any]:
        """
        Get kanban board data with filtering
        
        Args:
            firm_id: Firm ID to get data for
            work_type_filter: Optional work type filter
            priority_filter: Optional priority filter
            due_filter: Optional due date filter
            
        Returns:
            Dict containing kanban board data
        """
        try:
            # Use service registry to reduce coupling
            from src.shared.bootstrap import get_project_service, get_task_service
            
            project_service = get_project_service()
            task_service = get_task_service()
            
            # Get projects and tasks
            projects_result = project_service.get_projects_by_firm(firm_id)
            tasks_result = task_service.get_tasks_by_firm(firm_id)
            
            if not projects_result['success'] or not tasks_result['success']:
                return {
                    'success': False,
                    'message': 'Error retrieving kanban data',
                    'columns': []
                }
            
            # Organize data by status columns
            columns = [
                {'name': 'Not Started', 'projects': [], 'tasks': []},
                {'name': 'In Progress', 'projects': [], 'tasks': []},
                {'name': 'Needs Review', 'projects': [], 'tasks': []},
                {'name': 'Completed', 'projects': [], 'tasks': []}
            ]
            
            # Apply filters and organize by status
            # This is a simplified implementation
            return {
                'success': True,
                'columns': columns,
                'filters': {
                    'work_type': work_type_filter,
                    'priority': priority_filter,
                    'due': due_filter
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error getting kanban data: {str(e)}',
                'columns': []
            }
    
    @staticmethod
    def organize_projects_by_kanban_columns(projects: List[Dict[str, Any]], 
                                          kanban_columns: List[str]) -> Dict[str, Any]:
        """
        Organize projects by kanban columns
        
        Args:
            projects: List of project dictionaries
            kanban_columns: List of column names to organize by
            
        Returns:
            Dict containing organized projects and counts
        """
        try:
            projects_by_column = {}
            project_counts = {}
            
            # Initialize columns
            for column in kanban_columns:
                projects_by_column[column] = []
                project_counts[column] = 0
            
            # Organize projects by status
            for project in projects:
                status = project.get('status', 'Not Started')
                if status in projects_by_column:
                    projects_by_column[status].append(project)
                    project_counts[status] += 1
                else:
                    # Default to first column if status not found
                    if kanban_columns:
                        projects_by_column[kanban_columns[0]].append(project)
                        project_counts[kanban_columns[0]] += 1
            
            return {
                'success': True,
                'projects_by_column': projects_by_column,
                'project_counts': project_counts
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error organizing projects: {str(e)}',
                'projects_by_column': {},
                'project_counts': {}
            }