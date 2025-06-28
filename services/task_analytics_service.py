"""
TaskAnalyticsService: Handles task statistics, overdue calculations, and task-related analytics.
Extracted from DashboardService God Object to follow Single Responsibility Principle.
"""

from typing import Dict, Any, List
from datetime import datetime, date, timedelta
from repositories.task_repository import TaskRepository
from services.base import BaseService


class TaskAnalyticsService(BaseService):
    """Service for task analytics and statistics"""
    
    def __init__(self):
        super().__init__()
        self.task_repository = TaskRepository()
    
    def get_task_statistics(self, firm_id: int, filtered_tasks: List = None) -> Dict[str, Any]:
        """
        Calculate comprehensive task statistics for a firm
        
        Args:
            firm_id: The firm's ID
            filtered_tasks: Pre-filtered tasks list (optional)
            
        Returns:
            Dictionary with task statistics
        """
        if filtered_tasks is None:
            all_tasks = self.task_repository.get_tasks_by_firm(firm_id)
            filtered_tasks = self._filter_tasks_by_dependency_mode(all_tasks)
        
        total_tasks = len(filtered_tasks)
        completed_tasks = len([task for task in filtered_tasks if task.is_completed])
        overdue_tasks = len([task for task in filtered_tasks if task.is_overdue and not task.is_completed])
        in_progress_tasks = len([task for task in filtered_tasks if task.status == 'In Progress'])
        not_started_tasks = len([task for task in filtered_tasks if task.status == 'Not Started'])
        needs_review_tasks = len([task for task in filtered_tasks if task.status == 'Needs Review'])
        
        return {
            'total': total_tasks,
            'active': total_tasks - completed_tasks,
            'completed': completed_tasks,
            'overdue': overdue_tasks,
            'in_progress': in_progress_tasks,
            'not_started': not_started_tasks,
            'needs_review': needs_review_tasks,
            'completion_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        }
    
    def get_overdue_tasks(self, firm_id: int) -> List:
        """
        Get all overdue tasks for a firm
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            List of overdue Task objects
        """
        all_tasks = self.task_repository.get_tasks_by_firm(firm_id)
        filtered_tasks = self._filter_tasks_by_dependency_mode(all_tasks)
        
        return [task for task in filtered_tasks if task.is_overdue and not task.is_completed]
    
    def get_tasks_by_priority(self, firm_id: int) -> Dict[str, List]:
        """
        Group tasks by priority level
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            Dictionary with tasks grouped by priority
        """
        all_tasks = self.task_repository.get_tasks_by_firm(firm_id)
        filtered_tasks = self._filter_tasks_by_dependency_mode(all_tasks)
        
        priority_groups = {
            'High': [],
            'Medium': [],
            'Low': []
        }
        
        for task in filtered_tasks:
            if not task.is_completed:  # Only include active tasks
                priority = task.priority or 'Medium'
                if priority in priority_groups:
                    priority_groups[priority].append(task)
        
        return priority_groups
    
    def get_tasks_by_status(self, firm_id: int) -> Dict[str, List]:
        """
        Group tasks by status
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            Dictionary with tasks grouped by status
        """
        all_tasks = self.task_repository.get_tasks_by_firm(firm_id)
        filtered_tasks = self._filter_tasks_by_dependency_mode(all_tasks)
        
        status_groups = {
            'Not Started': [],
            'In Progress': [],
            'Needs Review': [],
            'Completed': []
        }
        
        for task in filtered_tasks:
            status = task.status or 'Not Started'
            if status in status_groups:
                status_groups[status].append(task)
        
        return status_groups
    
    def get_upcoming_deadlines(self, firm_id: int, days_ahead: int = 7) -> List:
        """
        Get tasks with upcoming deadlines
        
        Args:
            firm_id: The firm's ID
            days_ahead: Number of days to look ahead (default 7)
            
        Returns:
            List of tasks with upcoming deadlines
        """
        all_tasks = self.task_repository.get_tasks_by_firm(firm_id)
        filtered_tasks = self._filter_tasks_by_dependency_mode(all_tasks)
        
        upcoming = []
        cutoff_date = date.today() + timedelta(days=days_ahead)
        
        for task in filtered_tasks:
            if (task.due_date and 
                not task.is_completed and 
                task.due_date <= cutoff_date and 
                task.due_date >= date.today()):
                upcoming.append(task)
        
        # Sort by due date
        upcoming.sort(key=lambda t: t.due_date or date.max)
        return upcoming
    
    def _filter_tasks_by_dependency_mode(self, tasks: List) -> List:
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
    
    def get_recent_tasks(self, firm_id: int, limit: int = 5) -> List:
        """
        Get recently created tasks for a firm
        
        Args:
            firm_id: The firm's ID
            limit: Maximum number of tasks to return
            
        Returns:
            List of recent Task objects
        """
        return self.task_repository.get_recent_tasks(firm_id, limit=limit)