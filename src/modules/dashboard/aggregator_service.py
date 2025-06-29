"""
Dashboard Aggregator Service for CPA WorkflowPilot
Aggregates data from multiple services for dashboard display.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from src.shared.base import BaseService


class DashboardAggregatorService(BaseService):
    """Service that aggregates data from multiple domain services for dashboard views"""
    
    def __init__(self):
        super().__init__()
    
    def get_dashboard_data(self, firm_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get complete dashboard data by aggregating from all relevant services
        
        Args:
            firm_id: Firm ID to get data for
            user_id: Optional user ID for personalized data
            
        Returns:
            Dict containing all dashboard data sections
        """
        try:
            # Import services here to avoid circular imports
            from src.modules.project.task_service import TaskService
            from src.modules.project.service import ProjectService
            from src.modules.client.service import ClientService
            from src.modules.auth.service import AuthService
            
            # Initialize services
            task_service = TaskService()
            project_service = ProjectService()
            client_service = ClientService()
            auth_service = AuthService()
            
            # Get data from each service
            tasks_data = self._get_tasks_data(task_service, firm_id)
            projects_data = self._get_projects_data(project_service, firm_id)
            clients_data = self._get_clients_data(client_service, firm_id)
            users_data = self._get_users_data(auth_service, firm_id)
            
            # Get work type statistics
            work_type_data = self._get_work_type_data(task_service, firm_id)
            
            # Get recent items
            recent_tasks = self._get_recent_tasks(task_service, firm_id, limit=10)
            recent_projects = self._get_recent_projects(project_service, firm_id, limit=5)
            
            # Get filtered task list for main display
            filtered_tasks = self._get_filtered_tasks(task_service, firm_id, user_id)
            
            return {
                'tasks': tasks_data,
                'projects': projects_data,
                'projects_list': projects_data.get('list', []),
                'clients': clients_data,
                'users': users_data,
                'work_type_data': work_type_data,
                'recent_tasks': recent_tasks,
                'recent_projects': recent_projects,
                'filtered_tasks': filtered_tasks
            }
            
        except Exception as e:
            # Return safe defaults on error
            return self._get_empty_dashboard_data(error=str(e))
    
    def _get_tasks_data(self, task_service: 'TaskService', firm_id: int) -> Dict[str, Any]:
        """Get task statistics and counts"""
        try:
            result = task_service.get_task_statistics(firm_id)
            if result['success']:
                stats = result['statistics']
                return {
                    'total': stats.get('total', 0),
                    'completed': stats.get('completed', 0),
                    'pending': stats.get('pending', 0),
                    'overdue': stats.get('overdue', 0),
                    'in_progress': stats.get('in_progress', 0),
                    'active': stats.get('active', 0),
                    'due_soon': stats.get('due_soon', 0)
                }
        except Exception:
            pass
        
        return {
            'total': 0, 'completed': 0, 'pending': 0, 'overdue': 0,
            'in_progress': 0, 'active': 0, 'due_soon': 0
        }
    
    def _get_projects_data(self, project_service: 'ProjectService', firm_id: int) -> Dict[str, Any]:
        """Get project statistics and list"""
        try:
            # Get project statistics
            stats_result = project_service.get_project_statistics(firm_id)
            
            # Get project list
            list_result = project_service.get_projects_by_firm(firm_id)
            
            if stats_result['success'] and list_result['success']:
                stats = stats_result['statistics']
                projects_list = list_result['projects']
                
                return {
                    'active': stats.get('active', 0),
                    'total': stats.get('total', 0),
                    'completed': stats.get('completed', 0),
                    'list': projects_list
                }
        except Exception:
            pass
        
        return {'active': 0, 'total': 0, 'completed': 0, 'list': []}
    
    def _get_clients_data(self, client_service: 'ClientService', firm_id: int) -> Dict[str, Any]:
        """Get client statistics"""
        try:
            result = client_service.get_client_statistics(firm_id)
            if result['success']:
                stats = result['statistics']
                return {
                    'total': stats.get('total', 0),
                    'active': stats.get('active', 0)
                }
        except Exception:
            pass
        
        return {'total': 0, 'active': 0}
    
    def _get_users_data(self, auth_service: 'AuthService', firm_id: int) -> Dict[str, Any]:
        """Get user statistics"""
        try:
            users = auth_service.get_users_for_firm(firm_id)
            return {
                'count': len(users),
                'list': [{'id': u.id, 'name': u.name, 'role': u.role} for u in users]
            }
        except Exception:
            pass
        
        return {'count': 0, 'list': []}
    
    def _get_work_type_data(self, task_service: 'TaskService', firm_id: int) -> Dict[str, Any]:
        """Get work type distribution"""
        try:
            result = task_service.get_work_type_distribution(firm_id)
            if result['success']:
                return result['distribution']
        except Exception:
            pass
        
        return {}
    
    def _get_recent_tasks(self, task_service: 'TaskService', firm_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent tasks"""
        try:
            result = task_service.get_recent_tasks(firm_id, limit=limit)
            if result['success']:
                return result['tasks']
        except Exception:
            pass
        
        return []
    
    def _get_recent_projects(self, project_service: 'ProjectService', firm_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent projects"""
        try:
            result = project_service.get_recent_projects(firm_id, limit=limit)
            if result['success']:
                return result['projects']
        except Exception:
            pass
        
        return []
    
    def _get_filtered_tasks(self, task_service: 'TaskService', firm_id: int, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get filtered task list for main dashboard display"""
        try:
            filters = {'limit': 25}  # Limit for dashboard display
            if user_id:
                filters['assignee_id'] = user_id
            
            result = task_service.get_tasks_by_firm(firm_id, filters=filters)
            if result['success']:
                return result['tasks']
        except Exception:
            pass
        
        return []
    
    def _get_empty_dashboard_data(self, error: Optional[str] = None) -> Dict[str, Any]:
        """Return empty dashboard data structure"""
        return {
            'tasks': {
                'total': 0, 'completed': 0, 'pending': 0, 'overdue': 0,
                'in_progress': 0, 'active': 0, 'due_soon': 0
            },
            'projects': {'active': 0, 'total': 0, 'completed': 0, 'list': []},
            'projects_list': [],
            'clients': {'total': 0, 'active': 0},
            'users': {'count': 0, 'list': []},
            'work_type_data': {},
            'recent_tasks': [],
            'recent_projects': [],
            'filtered_tasks': [],
            '_error': error
        }