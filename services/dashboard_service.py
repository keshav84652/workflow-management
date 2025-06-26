"""
Dashboard service layer for business logic
"""

from typing import Dict, Any, List
from datetime import datetime, date, timedelta
from flask import session

import importlib.util
import os

# Import db from root core.py file
spec = importlib.util.spec_from_file_location("core", os.path.join(os.path.dirname(os.path.dirname(__file__)), "core.py"))
core_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core_module)
db = core_module.db
from models import Project, Task, Client, User, WorkType, TaskStatus


class DashboardService:
    """Service class for dashboard-related business operations"""
    
    @staticmethod
    def get_dashboard_data(firm_id: int) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data for a firm
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            Dictionary containing all dashboard statistics and data
        """
        # Get basic counts
        projects = DashboardService.get_active_projects(firm_id)
        all_tasks = DashboardService.get_all_tasks_for_firm(firm_id)
        filtered_tasks = DashboardService.filter_tasks_by_dependency_mode(all_tasks)
        
        # Calculate task statistics
        total_tasks = len(filtered_tasks)
        completed_tasks = len([task for task in filtered_tasks if task.is_completed])
        overdue_tasks = len([task for task in filtered_tasks if task.is_overdue and not task.is_completed])
        in_progress_tasks = len([task for task in filtered_tasks if task.status == 'In Progress'])
        
        # Get client count
        active_clients = Client.query.filter_by(firm_id=firm_id, is_active=True).count()
        
        # Get user count
        users_count = User.query.filter_by(firm_id=firm_id).count()
        
        # Get recent tasks and projects
        recent_tasks = DashboardService.get_recent_tasks(firm_id, limit=5)
        recent_projects = DashboardService.get_recent_projects(firm_id, limit=5)
        
        # Get work type data
        work_type_data = DashboardService.get_work_type_status_data(firm_id)
        
        return {
            'projects': {
                'active': len(projects),
                'total': Project.query.filter_by(firm_id=firm_id).count()
            },
            'tasks': {
                'active': total_tasks - completed_tasks,
                'total': total_tasks,
                'completed': completed_tasks,
                'overdue': overdue_tasks,
                'in_progress': in_progress_tasks
            },
            'clients': {
                'active': active_clients
            },
            'users': {
                'count': users_count
            },
            'recent_tasks': recent_tasks,
            'recent_projects': recent_projects,
            'work_type_data': work_type_data,
            'projects_list': projects
        }
    
    @staticmethod
    def get_active_projects(firm_id: int) -> List[Project]:
        """
        Get all active projects for a firm
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            List of active Project objects
        """
        return Project.query.filter_by(firm_id=firm_id, status='Active').all()
    
    @staticmethod
    def get_all_tasks_for_firm(firm_id: int) -> List[Task]:
        """
        Get all tasks for a firm (both project and independent tasks)
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            List of Task objects ordered by due date and priority
        """
        return Task.query.outerjoin(Project).filter(
            db.or_(
                Project.firm_id == firm_id,
                db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            )
        ).order_by(
            Task.due_date.asc().nullslast(),
            db.case(
                (Task.priority == 'High', 1),
                (Task.priority == 'Medium', 2),
                (Task.priority == 'Low', 3),
                else_=4
            )
        ).all()
    
    @staticmethod
    def filter_tasks_by_dependency_mode(tasks: List[Task]) -> List[Task]:
        """
        Filter tasks based on project dependency mode
        For interdependent projects, only show the first active task
        
        Args:
            tasks: List of Task objects to filter
            
        Returns:
            List of filtered Task objects
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
    def get_recent_tasks(firm_id: int, limit: int = 5) -> List[Task]:
        """
        Get recently created or updated tasks
        
        Args:
            firm_id: The firm's ID
            limit: Maximum number of tasks to return
            
        Returns:
            List of recent Task objects
        """
        return Task.query.outerjoin(Project).filter(
            db.or_(
                Project.firm_id == firm_id,
                db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            )
        ).order_by(Task.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_recent_projects(firm_id: int, limit: int = 5) -> List[Project]:
        """
        Get recently created projects
        
        Args:
            firm_id: The firm's ID
            limit: Maximum number of projects to return
            
        Returns:
            List of recent Project objects
        """
        return Project.query.filter_by(firm_id=firm_id).order_by(
            Project.created_at.desc()
        ).limit(limit).all()
    
    @staticmethod
    def get_work_type_status_data(firm_id: int) -> Dict[str, Any]:
        """
        Get task status distribution by work type
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            Dictionary containing work type and status distribution data
        """
        work_types = WorkType.query.filter_by(firm_id=firm_id, is_active=True).all()
        work_type_data = {}
        
        for work_type in work_types:
            work_type_info = {
                'name': work_type.name,
                'color': work_type.color,
                'statuses': {}
            }
            
            for status in work_type.task_statuses:
                # Count tasks with this specific status
                count = Task.query.join(Project).filter(
                    Project.firm_id == firm_id,
                    Project.work_type_id == work_type.id,
                    Task.status_id == status.id
                ).count()
                
                work_type_info['statuses'][status.name] = {
                    'count': count,
                    'color': status.color,
                    'is_terminal': status.is_terminal
                }
            
            work_type_data[work_type.name] = work_type_info
        
        return work_type_data
    
    @staticmethod
    def get_overdue_tasks(firm_id: int) -> List[Task]:
        """
        Get all overdue tasks for a firm
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            List of overdue Task objects (excluding completed)
        """
        all_tasks = DashboardService.get_all_tasks_for_firm(firm_id)
        filtered_tasks = DashboardService.filter_tasks_by_dependency_mode(all_tasks)
        
        return [task for task in filtered_tasks if task.is_overdue and not task.is_completed]
    
    @staticmethod
    def get_tasks_by_priority(firm_id: int) -> Dict[str, List[Task]]:
        """
        Get tasks grouped by priority
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            Dictionary with priority levels as keys and lists of tasks as values
        """
        all_tasks = DashboardService.get_all_tasks_for_firm(firm_id)
        filtered_tasks = DashboardService.filter_tasks_by_dependency_mode(all_tasks)
        
        priority_groups = {
            'High': [],
            'Medium': [],
            'Low': []
        }
        
        for task in filtered_tasks:
            if not task.is_completed and task.priority in priority_groups:
                priority_groups[task.priority].append(task)
        
        return priority_groups
    
    @staticmethod
    def get_tasks_by_status(firm_id: int) -> Dict[str, List[Task]]:
        """
        Get tasks grouped by status
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            Dictionary with status names as keys and lists of tasks as values
        """
        all_tasks = DashboardService.get_all_tasks_for_firm(firm_id)
        filtered_tasks = DashboardService.filter_tasks_by_dependency_mode(all_tasks)
        
        status_groups = {}
        
        for task in filtered_tasks:
            status = task.status
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(task)
        
        return status_groups
    
    @staticmethod
    def get_team_workload(firm_id: int) -> Dict[str, Any]:
        """
        Get workload distribution across team members
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            Dictionary containing team workload statistics
        """
        users = User.query.filter_by(firm_id=firm_id).all()
        workload_data = {}
        
        for user in users:
            # Get tasks assigned to this user
            user_tasks = Task.query.outerjoin(Project).filter(
                Task.assigned_to == user.id,
                db.or_(
                    Project.firm_id == firm_id,
                    db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
                )
            ).all()
            
            # Filter by dependency mode
            filtered_tasks = DashboardService.filter_tasks_by_dependency_mode(user_tasks)
            
            active_tasks = [task for task in filtered_tasks if not task.is_completed]
            overdue_tasks = [task for task in filtered_tasks if task.is_overdue and not task.is_completed]
            
            workload_data[user.name] = {
                'user_id': user.id,
                'role': user.role,
                'total_tasks': len(filtered_tasks),
                'active_tasks': len(active_tasks),
                'overdue_tasks': len(overdue_tasks),
                'completion_rate': (len(filtered_tasks) - len(active_tasks)) / len(filtered_tasks) * 100 if filtered_tasks else 0
            }
        
        return workload_data
    
    @staticmethod
    def get_upcoming_deadlines(firm_id: int, days_ahead: int = 7) -> List[Task]:
        """
        Get tasks with upcoming deadlines
        
        Args:
            firm_id: The firm's ID
            days_ahead: Number of days to look ahead for deadlines
            
        Returns:
            List of Task objects with deadlines in the specified timeframe
        """
        end_date = date.today() + timedelta(days=days_ahead)
        
        all_tasks = DashboardService.get_all_tasks_for_firm(firm_id)
        filtered_tasks = DashboardService.filter_tasks_by_dependency_mode(all_tasks)
        
        upcoming_tasks = []
        for task in filtered_tasks:
            if (not task.is_completed and 
                task.due_date and 
                task.due_date <= end_date and 
                task.due_date >= date.today()):
                upcoming_tasks.append(task)
        
        return sorted(upcoming_tasks, key=lambda x: x.due_date)
    
    @staticmethod
    def get_project_progress_summary(firm_id: int) -> List[Dict[str, Any]]:
        """
        Get progress summary for all projects
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            List of dictionaries containing project progress information
        """
        projects = Project.query.filter_by(firm_id=firm_id).all()
        progress_data = []
        
        for project in projects:
            project_tasks = Task.query.filter_by(project_id=project.id).all()
            
            if project_tasks:
                completed_tasks = [task for task in project_tasks if task.is_completed]
                progress_percentage = len(completed_tasks) / len(project_tasks) * 100
            else:
                progress_percentage = 0
            
            progress_data.append({
                'project_id': project.id,
                'project_name': project.name,
                'client_name': project.client_name,
                'status': project.status,
                'total_tasks': len(project_tasks),
                'completed_tasks': len(completed_tasks) if project_tasks else 0,
                'progress_percentage': round(progress_percentage, 1),
                'due_date': project.due_date,
                'is_overdue': project.due_date and project.due_date < date.today() and project.status != 'Completed'
            })
        
        return progress_data
    
    @staticmethod
    def get_calendar_data(firm_id: int, year: int, month: int) -> Dict[str, Any]:
        """
        Get calendar data for a specific month with task distribution
        
        Args:
            firm_id: The firm's ID
            year: Calendar year
            month: Calendar month (1-12)
            
        Returns:
            Dict containing calendar data and tasks
        """
        from datetime import date, timedelta
        
        # Create date object for the requested month
        current_date = date(year, month, 1)
        
        # Get start and end dates for the calendar view (include previous/next month days)
        start_of_month = date(year, month, 1)
        
        # Get the first day of the week for the month
        first_weekday = start_of_month.weekday()
        # Adjust for Sunday start (weekday() returns 0=Monday, we want 0=Sunday)
        days_back = (first_weekday + 1) % 7
        calendar_start = start_of_month - timedelta(days=days_back)
        
        # Get end of month
        if month == 12:
            end_of_month = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_of_month = date(year, month + 1, 1) - timedelta(days=1)
        
        # Calculate days forward to complete the calendar grid (6 weeks * 7 days = 42 days)
        days_shown = (end_of_month - calendar_start).days + 1
        days_needed = 42 - days_shown
        calendar_end = end_of_month + timedelta(days=days_needed)
        
        # Query tasks for the calendar period - include both project and independent tasks
        tasks = Task.query.outerjoin(Project).filter(
            db.or_(
                Project.firm_id == firm_id,
                db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            ),
            Task.due_date.between(calendar_start, calendar_end)
        ).all()
        
        # Get all users for the firm for the assignment dropdown
        users = User.query.filter_by(firm_id=firm_id).all()
        
        # Organize tasks by date
        tasks_by_date = {}
        for task in tasks:
            if task.due_date:
                date_str = task.due_date.strftime('%Y-%m-%d')
                if date_str not in tasks_by_date:
                    tasks_by_date[date_str] = []
                tasks_by_date[date_str].append(task)
        
        return {
            'current_date': current_date,
            'calendar_start': calendar_start,
            'calendar_end': calendar_end,
            'start_of_month': start_of_month,
            'end_of_month': end_of_month,
            'tasks_by_date': tasks_by_date,
            'users': users,
            'year': year,
            'month': month
        }
    
    @staticmethod
    def search_tasks_and_projects(firm_id: int, query: str = '', filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Search tasks and projects with advanced filtering
        
        Args:
            firm_id: The firm's ID
            query: Search query string
            filters: Additional filters (status, assignee, project, etc.)
            
        Returns:
            Dict containing search results
        """
        if filters is None:
            filters = {}
        
        # Base queries for tasks and projects
        tasks_query = Task.query.outerjoin(Project).filter(
            db.or_(
                Project.firm_id == firm_id,
                db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            )
        )
        
        projects_query = Project.query.filter_by(firm_id=firm_id)
        
        # Apply text search if query provided
        if query:
            task_search = db.or_(
                Task.title.ilike(f'%{query}%'),
                Task.description.ilike(f'%{query}%')
            )
            project_search = db.or_(
                Project.name.ilike(f'%{query}%'),
                Project.description.ilike(f'%{query}%')
            )
            
            tasks_query = tasks_query.filter(task_search)
            projects_query = projects_query.filter(project_search)
        
        # Apply filters
        if filters.get('status'):
            tasks_query = tasks_query.filter(Task.status == filters['status'])
            projects_query = projects_query.filter(Project.status == filters['status'])
        
        if filters.get('assignee_id'):
            tasks_query = tasks_query.filter(Task.assignee_id == filters['assignee_id'])
        
        if filters.get('project_id'):
            tasks_query = tasks_query.filter(Task.project_id == filters['project_id'])
        
        if filters.get('priority'):
            tasks_query = tasks_query.filter(Task.priority == filters['priority'])
        
        # Get results
        tasks = tasks_query.order_by(Task.due_date.asc().nullslast()).all()
        projects = projects_query.order_by(Project.due_date.asc().nullslast()).all()
        
        # Get filter options for the form
        users = User.query.filter_by(firm_id=firm_id).all()
        all_projects = Project.query.filter_by(firm_id=firm_id).all()
        
        return {
            'tasks': tasks,
            'projects': projects,
            'users': users,
            'all_projects': all_projects,
            'query': query,
            'filters': filters,
            'total_tasks': len(tasks),
            'total_projects': len(projects)
        }
    
    @staticmethod
    def get_time_tracking_report(firm_id: int, start_date: date = None, end_date: date = None) -> Dict[str, Any]:
        """
        Generate time tracking report data
        
        Args:
            firm_id: The firm's ID
            start_date: Report start date (defaults to start of current month)
            end_date: Report end date (defaults to today)
            
        Returns:
            Dict containing time tracking data
        """
        from datetime import date, datetime
        
        if not start_date:
            today = date.today()
            start_date = date(today.year, today.month, 1)
        
        if not end_date:
            end_date = date.today()
        
        # Get all tasks with time logged for the firm
        tasks = Task.query.outerjoin(Project).filter(
            db.or_(
                Project.firm_id == firm_id,
                db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            ),
            Task.actual_hours.isnot(None),
            Task.actual_hours > 0
        ).all()
        
        # Filter tasks by date range if we had time tracking timestamps
        # For now, we'll include all tasks with logged time
        
        # Aggregate data
        total_hours = sum(task.actual_hours or 0 for task in tasks)
        billable_hours = sum(task.actual_hours or 0 for task in tasks if task.billable_rate and task.billable_rate > 0)
        total_revenue = sum((task.actual_hours or 0) * (task.billable_rate or 0) for task in tasks)
        
        # Group by user
        user_data = {}
        for task in tasks:
            if task.assignee:
                user_id = task.assignee.id
                if user_id not in user_data:
                    user_data[user_id] = {
                        'user': task.assignee,
                        'total_hours': 0,
                        'billable_hours': 0,
                        'revenue': 0,
                        'tasks_count': 0
                    }
                
                hours = task.actual_hours or 0
                rate = task.billable_rate or 0
                
                user_data[user_id]['total_hours'] += hours
                user_data[user_id]['tasks_count'] += 1
                
                if rate > 0:
                    user_data[user_id]['billable_hours'] += hours
                    user_data[user_id]['revenue'] += hours * rate
        
        # Group by project
        project_data = {}
        for task in tasks:
            project_name = task.project.name if task.project else 'Independent Tasks'
            if project_name not in project_data:
                project_data[project_name] = {
                    'total_hours': 0,
                    'billable_hours': 0,
                    'revenue': 0,
                    'tasks_count': 0
                }
            
            hours = task.actual_hours or 0
            rate = task.billable_rate or 0
            
            project_data[project_name]['total_hours'] += hours
            project_data[project_name]['tasks_count'] += 1
            
            if rate > 0:
                project_data[project_name]['billable_hours'] += hours
                project_data[project_name]['revenue'] += hours * rate
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'total_hours': total_hours,
            'billable_hours': billable_hours,
            'total_revenue': total_revenue,
            'user_data': list(user_data.values()),
            'project_data': project_data,
            'tasks_with_time': tasks
        }
    
    @staticmethod
    def get_kanban_data(firm_id: int) -> Dict[str, Any]:
        """
        Get kanban board data with projects organized by status
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            Dict containing kanban board data
        """
        # Get all active projects for the firm
        projects = Project.query.filter_by(firm_id=firm_id).order_by(Project.created_at.desc()).all()
        
        # Get all users for assignment
        users = User.query.filter_by(firm_id=firm_id).all()
        
        # Organize projects by status/column
        kanban_data = {
            'not_started': [],
            'in_progress': [],
            'needs_review': [],
            'completed': []
        }
        
        for project in projects:
            # Determine which column the project belongs to based on status
            if project.current_status_id == 1:  # Not Started
                column = 'not_started'
            elif project.current_status_id == 2:  # In Progress
                column = 'in_progress'
            elif project.current_status_id == 3:  # Needs Review
                column = 'needs_review'
            elif project.current_status_id == 4:  # Completed
                column = 'completed'
            else:
                # Fallback logic based on progress percentage
                if project.progress_percentage >= 100:
                    column = 'completed'
                elif project.progress_percentage >= 75:
                    column = 'needs_review'
                elif project.progress_percentage > 0:
                    column = 'in_progress'
                else:
                    column = 'not_started'
            
            kanban_data[column].append(project)
        
        return {
            'projects': kanban_data,
            'users': users,
            'total_projects': len(projects)
        }