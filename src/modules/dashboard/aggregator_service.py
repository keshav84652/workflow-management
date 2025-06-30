"""
Dashboard Aggregator Service

This service follows Gemini's aggregator pattern to properly decouple the dashboard
from other modules. It's the ONLY service that's allowed to coordinate between
multiple modules, keeping the dashboard blueprint thin and focused.
"""

from typing import Dict, Any, List
import logging
from src.shared.di_container import get_service
from src.modules.client.interface import IClientService
from src.modules.project.interface import IProjectService, ITaskService
from src.modules.auth.interface import IAuthService
from src.shared.base import BaseService

logger = logging.getLogger(__name__)


class DashboardAggregatorService(BaseService):
    """
    Aggregator service for dashboard data coordination.
    
    This is the designated place for orchestrating calls to multiple module services.
    Following Gemini's architectural principle: "Blueprints shall be thin and unintelligent."
    """
    
    def __init__(self):
        super().__init__()
        # Use dependency injection to get service instances
        # DI Container setup is now mandatory - no fallback logic
        self.client_service = get_service(IClientService)
        self.project_service = get_service(IProjectService)
        self.task_service = get_service(ITaskService)
        self.auth_service = get_service(IAuthService)
    
    def get_dashboard_data(self, firm_id: int, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data by orchestrating calls to multiple services
        
        Args:
            firm_id: Firm ID for data filtering
            user_id: User ID for personalized data
            
        Returns:
            Complete dashboard data structure
        """
        try:
            # Get data from each service's public interface
            tasks_result = self.task_service.get_task_statistics(firm_id)
            projects_result = self.project_service.get_project_statistics(firm_id)
            clients_result = self.client_service.get_client_statistics(firm_id)
            
            # Get lists for display
            recent_tasks_result = self.task_service.get_recent_tasks(firm_id, limit=10)
            recent_projects_result = self.project_service.get_recent_projects(firm_id, limit=5)
            filtered_tasks_result = self.task_service.get_tasks_for_dashboard(firm_id, user_id)
            
            # Extract data safely with fallbacks
            tasks_data = tasks_result.get('statistics', {}) if tasks_result.get('success') else {}
            projects_data = projects_result.get('statistics', {}) if projects_result.get('success') else {}
            clients_data = clients_result.get('statistics', {}) if clients_result.get('success') else {}
            
            recent_tasks = recent_tasks_result.get('tasks', []) if recent_tasks_result.get('success') else []
            recent_projects = recent_projects_result.get('projects', []) if recent_projects_result.get('success') else []
            filtered_tasks = filtered_tasks_result.get('tasks', []) if filtered_tasks_result.get('success') else []
            
            # Aggregate and structure the data for the dashboard template
            dashboard_data = {
                # Core statistics
                'tasks': {
                    'total': tasks_data.get('total', 0),
                    'completed': tasks_data.get('completed', 0),
                    'in_progress': tasks_data.get('in_progress', 0),
                    'overdue': tasks_data.get('overdue', 0),
                    'active': tasks_data.get('active', 0),
                    'due_soon': tasks_data.get('due_soon', 0)
                },
                'projects': {
                    'total': projects_data.get('total', 0),
                    'active': projects_data.get('active', 0),
                    'completed': projects_data.get('completed', 0)
                },
                'clients': {
                    'total': clients_data.get('total', 0),
                    'active': clients_data.get('active', 0)
                },
                
                # Lists for display
                'recent_tasks': recent_tasks,
                'recent_projects': recent_projects,
                'filtered_tasks': filtered_tasks,
                
                # Legacy data for template compatibility
                'projects_list': recent_projects,
                'task_status_data': {
                    'Not Started': tasks_data.get('total', 0) - tasks_data.get('in_progress', 0) - tasks_data.get('completed', 0),
                    'In Progress': tasks_data.get('in_progress', 0),
                    'Needs Review': 0,
                    'Completed': tasks_data.get('completed', 0)
                },
                'work_type_data': {},
                'priority_data': {},
                'user_workload': {},
                'upcoming_tasks': [],
                'today_tasks_count': 0,
                'users': {'count': 0}
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error aggregating dashboard data for firm {firm_id}: {e}")
            # Return safe default data structure
            return {
                'tasks': {'total': 0, 'completed': 0, 'in_progress': 0, 'overdue': 0, 'active': 0, 'due_soon': 0},
                'projects': {'total': 0, 'active': 0, 'completed': 0},
                'clients': {'total': 0, 'active': 0},
                'recent_tasks': [],
                'recent_projects': [],
                'filtered_tasks': [],
                'projects_list': [],
                'task_status_data': {'Not Started': 0, 'In Progress': 0, 'Needs Review': 0, 'Completed': 0},
                'work_type_data': {},
                'priority_data': {},
                'user_workload': {},
                'upcoming_tasks': [],
                'today_tasks_count': 0,
                'users': {'count': 0}
            }
    
    def get_search_data(self, firm_id: int, query: str, search_type: str = 'all', limit: int = 20) -> Dict[str, Any]:
        """
        Coordinate search across multiple modules
        
        Args:
            firm_id: Firm ID for data filtering
            query: Search query
            search_type: Type of search ('all', 'tasks', 'projects', 'clients')
            limit: Maximum results per module
            
        Returns:
            Aggregated search results
        """
        try:
            if not query.strip():
                return {
                    'tasks': [],
                    'projects': [],
                    'clients': [],
                    'total_results': 0,
                    'search_type': search_type
                }
            
            # Search each module's data through their public interfaces
            search_results = {
                'tasks': [],
                'projects': [],
                'clients': [],
                'search_type': search_type
            }
            
            if search_type in ['all', 'tasks']:
                tasks_result = self.task_service.search_tasks(firm_id, query, limit)
                search_results['tasks'] = tasks_result.get('tasks', []) if tasks_result.get('success') else []
            
            if search_type in ['all', 'projects']:
                projects_result = self.project_service.search_projects(firm_id, query, limit)
                search_results['projects'] = projects_result.get('projects', []) if projects_result.get('success') else []
            
            if search_type in ['all', 'clients']:
                clients_result = self.client_service.search_clients(firm_id, query, limit)
                search_results['clients'] = clients_result.get('clients', []) if clients_result.get('success') else []
            
            search_results['total_results'] = (
                len(search_results['tasks']) + 
                len(search_results['projects']) + 
                len(search_results['clients'])
            )
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error performing search for query '{query}' in firm {firm_id}: {e}")
            return {
                'tasks': [],
                'projects': [],
                'clients': [],
                'total_results': 0,
                'search_type': search_type
            }
    
    def get_calendar_data(self, firm_id: int, year: int, month: int) -> Dict[str, Any]:
        """
        Get calendar data by coordinating with task service
        
        Args:
            firm_id: Firm ID for data filtering
            year: Calendar year
            month: Calendar month
            
        Returns:
            Calendar data structure
        """
        try:
            calendar_result = self.task_service.get_tasks_for_calendar(firm_id, year, month)
            
            if calendar_result.get('success'):
                return {
                    'tasks_by_date': calendar_result.get('tasks_by_date', {}),
                    'current_date': calendar_result.get('current_date'),
                    'year': year,
                    'month': month
                }
            else:
                return {
                    'tasks_by_date': {},
                    'current_date': None,
                    'year': year,
                    'month': month
                }
                
        except Exception as e:
            logger.error(f"Error getting calendar data for {year}-{month} in firm {firm_id}: {e}")
            return {
                'tasks_by_date': {},
                'current_date': None,
                'year': year,
                'month': month
            }