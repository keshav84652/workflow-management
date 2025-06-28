"""
DashboardAggregatorService: Orchestrates all dashboard-related services to provide comprehensive dashboard data.
This replaces the monolithic DashboardService and follows the Composition over Inheritance principle.
"""

from typing import Dict, Any
from services.base import BaseService
from services.task_analytics_service import TaskAnalyticsService
from services.project_analytics_service import ProjectAnalyticsService
from services.time_tracking_service import TimeTrackingService
from services.team_workload_service import TeamWorkloadService
from repositories.client_repository import ClientRepository
from repositories.user_repository import UserRepository


class DashboardAggregatorService(BaseService):
    """
    Main dashboard service that orchestrates other focused services.
    This service is responsible only for coordination, not implementation.
    """
    
    def __init__(self):
        super().__init__()
        
        # Initialize focused services
        self.task_analytics = TaskAnalyticsService()
        self.project_analytics = ProjectAnalyticsService()
        self.time_tracking = TimeTrackingService()
        self.team_workload = TeamWorkloadService()
        
        # Initialize repositories for basic data
        self.client_repository = ClientRepository()
        self.user_repository = UserRepository()
    
    def get_dashboard_data(self, firm_id: int) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data by orchestrating focused services
        Compatible with old DashboardService interface for seamless migration
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            Dictionary containing all dashboard statistics and data
        """
        try:
            # Get basic statistics
            task_stats = self.task_analytics.get_task_statistics(firm_id)
            project_stats = self.project_analytics.get_project_statistics(firm_id)
            
            # Get recent data
            recent_tasks = self.task_analytics.get_recent_tasks(firm_id, limit=5)
            recent_projects = self.project_analytics.get_recent_projects(firm_id, limit=5)
            
            # Get client and user counts
            active_clients = self.client_repository.get_active_count(firm_id)
            users_count = self.user_repository.get_count_by_firm(firm_id)
            
            # Get additional data for compatibility
            projects_list = self.project_analytics.get_active_projects(firm_id)
            filtered_tasks = self.task_analytics.get_filtered_tasks(firm_id)
            work_type_data = self._get_work_type_status_data(firm_id)
            
            return {
                'projects': {
                    'active': project_stats.get('active', 0),
                    'total': project_stats.get('total', 0)
                },
                'tasks': {
                    'active': task_stats.get('active', 0),
                    'total': task_stats.get('total', 0),
                    'completed': task_stats.get('completed', 0),
                    'overdue': task_stats.get('overdue', 0),
                    'in_progress': task_stats.get('in_progress', 0),
                    'due_soon': task_stats.get('due_soon', 0)
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
                'projects_list': projects_list,
                'filtered_tasks': filtered_tasks
            }
            
        except Exception as e:
            # Log error and return safe fallback
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting dashboard data for firm {firm_id}: {e}")
            
            return {
                'projects': {'active': 0, 'total': 0},
                'tasks': {'active': 0, 'total': 0, 'completed': 0, 'overdue': 0, 'in_progress': 0, 'due_soon': 0},
                'clients': {'active': 0},
                'users': {'count': 0},
                'recent_tasks': [],
                'recent_projects': [],
                'work_type_data': {},
                'projects_list': [],
                'filtered_tasks': [],
                'error': 'Unable to load dashboard data'
            }
    
    def _get_work_type_status_data(self, firm_id: int) -> Dict[str, Any]:
        """
        Get work type data (compatibility method)
        TODO: Move to WorkTypeRepository when available
        """
        try:
            from models import WorkType
            work_types = WorkType.query.filter_by(firm_id=firm_id, is_active=True).all()
            return {wt.name: {'name': wt.name, 'color': wt.color} for wt in work_types}
        except Exception:
            return {}
    
    def get_advanced_analytics(self, firm_id: int) -> Dict[str, Any]:
        """
        Get advanced analytics data for dashboard power users
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            Dictionary with advanced analytics
        """
        try:
            return {
                'project_progress': self.project_analytics.get_project_progress_summary(firm_id),
                'team_workload': self.team_workload.get_team_workload(firm_id),
                'time_tracking': self.time_tracking.get_time_tracking_report(firm_id),
                'task_distribution': {
                    'by_priority': self.task_analytics.get_tasks_by_priority(firm_id),
                    'by_status': self.task_analytics.get_tasks_by_status(firm_id)
                },
                'project_distribution': {
                    'by_priority': self.project_analytics.get_projects_by_priority(firm_id),
                    'by_status': self.project_analytics.get_projects_by_status(firm_id)
                }
            }
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting advanced analytics for firm {firm_id}: {e}")
            return {}
    
    def get_quick_stats(self, firm_id: int) -> Dict[str, Any]:
        """
        Get quick statistics for dashboard widgets
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            Dictionary with quick stats
        """
        try:
            task_stats = self.task_analytics.get_task_statistics(firm_id)
            project_stats = self.project_analytics.get_project_statistics(firm_id)
            
            return {
                'active_tasks': task_stats.get('active', 0),
                'active_projects': project_stats.get('active', 0),
                'overdue_count': len(self.task_analytics.get_overdue_tasks(firm_id)),
                'completion_rate': task_stats.get('completion_rate', 0)
            }
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting quick stats for firm {firm_id}: {e}")
            return {
                'active_tasks': 0,
                'active_projects': 0,
                'overdue_count': 0,
                'completion_rate': 0
            }
    
    def get_time_tracking_report(self, firm_id: int, start_date=None, end_date=None) -> Dict[str, Any]:
        """
        Get time tracking report by delegating to TimeTrackingService
        
        Args:
            firm_id: The firm's ID
            start_date: Start date for report (optional)
            end_date: End date for report (optional)
            
        Returns:
            Dictionary with time tracking analytics
        """
        return self.time_tracking.get_time_tracking_report(firm_id, start_date, end_date)
    
    def get_calendar_data(self, firm_id: int, year: int, month: int) -> Dict[str, Any]:
        """
        Get calendar data for a specific month and year
        
        Args:
            firm_id: The firm's ID
            year: Year for calendar view
            month: Month for calendar view
            
        Returns:
            Dictionary with calendar data including tasks by date
        """
        try:
            from datetime import date, timedelta
            import calendar
            
            # Get all tasks for the firm
            filtered_tasks = self.task_analytics.get_filtered_tasks(firm_id)
            
            # Get the month range
            first_day = date(year, month, 1)
            last_day = date(year, month, calendar.monthrange(year, month)[1])
            
            # Group tasks by date
            tasks_by_date = {}
            
            for task in filtered_tasks:
                if task.due_date:
                    # Only include tasks with due dates in the specified month
                    if first_day <= task.due_date <= last_day:
                        date_str = task.due_date.isoformat()
                        if date_str not in tasks_by_date:
                            tasks_by_date[date_str] = []
                        tasks_by_date[date_str].append(task)
            
            # Tasks already have computed properties as methods/properties
            # No need to set them manually - they're calculated on access
            
            return {
                'year': year,
                'month': month,
                'month_name': calendar.month_name[month],
                'tasks_by_date': tasks_by_date,
                'total_tasks': sum(len(tasks) for tasks in tasks_by_date.values()),
                'dates_with_tasks': list(tasks_by_date.keys())
            }
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting calendar data for firm {firm_id}, {year}-{month}: {e}")
            
            return {
                'year': year,
                'month': month,
                'month_name': calendar.month_name[month] if month <= 12 else 'Unknown',
                'tasks_by_date': {},
                'total_tasks': 0,
                'dates_with_tasks': [],
                'error': 'Unable to load calendar data'
            }