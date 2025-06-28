"""
ProjectAnalyticsService: Handles project statistics, progress calculations, and project-related analytics.
Extracted from DashboardService God Object to follow Single Responsibility Principle.
"""

from typing import Dict, Any, List
from datetime import datetime, date, timedelta
from repositories.project_repository import ProjectRepository
from repositories.task_repository import TaskRepository
from services.base import BaseService


class ProjectAnalyticsService(BaseService):
    """Service for project analytics and statistics"""
    
    def __init__(self):
        super().__init__()
        self.project_repository = ProjectRepository()
        self.task_repository = TaskRepository()
    
    def get_project_statistics(self, firm_id: int) -> Dict[str, Any]:
        """
        Calculate comprehensive project statistics for a firm
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            Dictionary with project statistics
        """
        all_projects = self.project_repository.get_projects_by_firm(firm_id)
        active_projects = [p for p in all_projects if p.status == 'Active']
        completed_projects = [p for p in all_projects if p.status == 'Completed']
        
        return {
            'total': len(all_projects),
            'active': len(active_projects),
            'completed': len(completed_projects),
            'completion_rate': (len(completed_projects) / len(all_projects) * 100) if all_projects else 0
        }
    
    def get_project_progress_summary(self, firm_id: int) -> Dict[str, Any]:
        """
        Get detailed progress summary for all projects
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            Dictionary with project progress data
        """
        projects = self.project_repository.get_projects_by_firm(firm_id)
        progress_data = []
        
        for project in projects:
            if project.status == 'Active':
                # Get tasks for this project
                project_tasks = self.task_repository.get_tasks_by_project(project.id)
                
                total_tasks = len(project_tasks)
                completed_tasks = len([t for t in project_tasks if t.is_completed])
                
                progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
                
                # Calculate estimated vs actual hours
                estimated_hours = sum([t.estimated_hours or 0 for t in project_tasks])
                actual_hours = sum([t.actual_hours or 0 for t in project_tasks])
                
                progress_data.append({
                    'project_id': project.id,
                    'project_name': project.name,
                    'client_name': project.client.name if project.client else 'No Client',
                    'progress_percentage': round(progress_percentage, 1),
                    'total_tasks': total_tasks,
                    'completed_tasks': completed_tasks,
                    'remaining_tasks': total_tasks - completed_tasks,
                    'estimated_hours': estimated_hours,
                    'actual_hours': actual_hours,
                    'due_date': project.due_date,
                    'is_overdue': project.due_date and project.due_date < date.today() and project.status == 'Active',
                    'priority': project.priority
                })
        
        # Sort by progress percentage (lowest first - needs attention)
        progress_data.sort(key=lambda x: x['progress_percentage'])
        
        return {
            'projects': progress_data,
            'summary': {
                'total_projects': len(progress_data),
                'avg_progress': sum([p['progress_percentage'] for p in progress_data]) / len(progress_data) if progress_data else 0,
                'projects_at_risk': len([p for p in progress_data if p['is_overdue'] or p['progress_percentage'] < 25]),
                'projects_on_track': len([p for p in progress_data if not p['is_overdue'] and p['progress_percentage'] >= 25])
            }
        }
    
    def get_recent_projects(self, firm_id: int, limit: int = 5) -> List:
        """
        Get recently created projects for a firm
        
        Args:
            firm_id: The firm's ID
            limit: Maximum number of projects to return
            
        Returns:
            List of recent Project objects
        """
        return self.project_repository.get_recent_projects(firm_id, limit=limit)
    
    def get_projects_by_status(self, firm_id: int) -> Dict[str, List]:
        """
        Group projects by status
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            Dictionary with projects grouped by status
        """
        projects = self.project_repository.get_projects_by_firm(firm_id)
        
        status_groups = {
            'Active': [],
            'On Hold': [],
            'Completed': [],
            'Cancelled': []
        }
        
        for project in projects:
            status = project.status or 'Active'
            if status in status_groups:
                status_groups[status].append(project)
        
        return status_groups
    
    def get_projects_by_priority(self, firm_id: int) -> Dict[str, List]:
        """
        Group projects by priority level
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            Dictionary with projects grouped by priority
        """
        projects = self.project_repository.get_projects_by_firm(firm_id)
        active_projects = [p for p in projects if p.status == 'Active']
        
        priority_groups = {
            'High': [],
            'Medium': [],
            'Low': []
        }
        
        for project in active_projects:
            priority = project.priority or 'Medium'
            if priority in priority_groups:
                priority_groups[priority].append(project)
        
        return priority_groups