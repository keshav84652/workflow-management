"""
TimeTrackingService: Handles time tracking reports, billable hours, and revenue calculations.
Extracted from DashboardService God Object to follow Single Responsibility Principle.
"""

from typing import Dict, Any, List
from datetime import datetime, date, timedelta
from repositories.task_repository import TaskRepository
from repositories.project_repository import ProjectRepository
from repositories.user_repository import UserRepository
from services.base import BaseService


class TimeTrackingService(BaseService):
    """Service for time tracking and billing analytics"""
    
    def __init__(self):
        super().__init__()
        self.task_repository = TaskRepository()
        self.project_repository = ProjectRepository()
        self.user_repository = UserRepository()
    
    def get_time_tracking_report(self, firm_id: int, start_date: date = None, end_date: date = None) -> Dict[str, Any]:
        """
        Generate comprehensive time tracking report
        
        Args:
            firm_id: The firm's ID
            start_date: Start date for report (optional)
            end_date: End date for report (optional)
            
        Returns:
            Dictionary with time tracking analytics
        """
        # Default to current month if no dates provided
        if not start_date:
            start_date = date.today().replace(day=1)
        if not end_date:
            end_date = date.today()
        
        # Get all tasks with time tracking data
        tasks = self.task_repository.get_tasks_by_firm(firm_id)
        
        # Filter tasks with logged time in the date range
        tracked_tasks = []
        for task in tasks:
            if task.actual_hours and task.actual_hours > 0:
                # For now, include all tasks with logged time
                # TODO: Add date filtering based on time log entries
                tracked_tasks.append(task)
        
        # Calculate totals
        total_hours = sum([task.actual_hours or 0 for task in tracked_tasks])
        billable_hours = sum([task.actual_hours or 0 for task in tracked_tasks if getattr(task, 'is_billable', True)])
        
        # Calculate revenue (assuming billable rate exists)
        total_revenue = 0
        billable_revenue = 0
        
        for task in tracked_tasks:
            task_hours = task.actual_hours or 0
            # Default rate if not specified
            hourly_rate = getattr(task, 'hourly_rate', 150)  # Default $150/hour
            
            task_revenue = task_hours * hourly_rate
            total_revenue += task_revenue
            
            if getattr(task, 'is_billable', True):
                billable_revenue += task_revenue
        
        # Group by user
        user_time = {}
        for task in tracked_tasks:
            if task.assignee:
                user_id = task.assignee.id
                user_name = task.assignee.name
                
                if user_id not in user_time:
                    user_time[user_id] = {
                        'name': user_name,
                        'total_hours': 0,
                        'billable_hours': 0,
                        'revenue': 0,
                        'tasks_count': 0
                    }
                
                task_hours = task.actual_hours or 0
                user_time[user_id]['total_hours'] += task_hours
                user_time[user_id]['tasks_count'] += 1
                
                if getattr(task, 'is_billable', True):
                    user_time[user_id]['billable_hours'] += task_hours
                    hourly_rate = getattr(task, 'hourly_rate', 150)
                    user_time[user_id]['revenue'] += task_hours * hourly_rate
        
        # Group by project
        project_time = {}
        for task in tracked_tasks:
            if task.project:
                project_id = task.project.id
                project_name = task.project.name
                
                if project_id not in project_time:
                    project_time[project_id] = {
                        'name': project_name,
                        'total_hours': 0,
                        'billable_hours': 0,
                        'revenue': 0,
                        'tasks_count': 0
                    }
                
                task_hours = task.actual_hours or 0
                project_time[project_id]['total_hours'] += task_hours
                project_time[project_id]['tasks_count'] += 1
                
                if getattr(task, 'is_billable', True):
                    project_time[project_id]['billable_hours'] += task_hours
                    hourly_rate = getattr(task, 'hourly_rate', 150)
                    project_time[project_id]['revenue'] += task_hours * hourly_rate
        
        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'summary': {
                'total_hours': round(total_hours, 2),
                'billable_hours': round(billable_hours, 2),
                'non_billable_hours': round(total_hours - billable_hours, 2),
                'billable_percentage': round((billable_hours / total_hours * 100) if total_hours > 0 else 0, 1),
                'total_revenue': round(total_revenue, 2),
                'billable_revenue': round(billable_revenue, 2),
                'average_hourly_rate': round((billable_revenue / billable_hours) if billable_hours > 0 else 0, 2),
                'tasks_with_time': len(tracked_tasks)
            },
            'by_user': list(user_time.values()),
            'by_project': list(project_time.values()),
            'detailed_tasks': [
                {
                    'id': task.id,
                    'title': task.title,
                    'project': task.project.name if task.project else 'No Project',
                    'assignee': task.assignee.name if task.assignee else 'Unassigned',
                    'hours': task.actual_hours or 0,
                    'estimated_hours': task.estimated_hours or 0,
                    'variance': (task.actual_hours or 0) - (task.estimated_hours or 0),
                    'is_billable': getattr(task, 'is_billable', True),
                    'hourly_rate': getattr(task, 'hourly_rate', 150)
                }
                for task in tracked_tasks
            ]
        }
    
    def get_user_productivity_metrics(self, firm_id: int, days_back: int = 30) -> Dict[str, Any]:
        """
        Calculate productivity metrics for users
        
        Args:
            firm_id: The firm's ID
            days_back: Number of days to analyze (default 30)
            
        Returns:
            Dictionary with user productivity data
        """
        # Get users and their tasks
        users = self.user_repository.get_users_by_firm(firm_id)
        tasks = self.task_repository.get_tasks_by_firm(firm_id)
        
        user_metrics = []
        
        for user in users:
            user_tasks = [task for task in tasks if task.assignee_id == user.id]
            
            # Calculate metrics
            total_tasks = len(user_tasks)
            completed_tasks = len([task for task in user_tasks if task.is_completed])
            overdue_tasks = len([task for task in user_tasks if task.is_overdue and not task.is_completed])
            total_hours = sum([task.actual_hours or 0 for task in user_tasks])
            
            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            avg_hours_per_task = (total_hours / completed_tasks) if completed_tasks > 0 else 0
            
            user_metrics.append({
                'user_id': user.id,
                'name': user.name,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'overdue_tasks': overdue_tasks,
                'completion_rate': round(completion_rate, 1),
                'total_hours_logged': round(total_hours, 2),
                'avg_hours_per_task': round(avg_hours_per_task, 2),
                'productivity_score': self._calculate_productivity_score(completion_rate, overdue_tasks, total_tasks)
            })
        
        # Sort by productivity score
        user_metrics.sort(key=lambda x: x['productivity_score'], reverse=True)
        
        return {
            'users': user_metrics,
            'team_averages': {
                'avg_completion_rate': sum([u['completion_rate'] for u in user_metrics]) / len(user_metrics) if user_metrics else 0,
                'total_team_hours': sum([u['total_hours_logged'] for u in user_metrics]),
                'total_team_tasks': sum([u['total_tasks'] for u in user_metrics])
            }
        }
    
    def _calculate_productivity_score(self, completion_rate: float, overdue_tasks: int, total_tasks: int) -> float:
        """
        Calculate a productivity score based on completion rate and overdue tasks
        
        Args:
            completion_rate: Percentage of completed tasks
            overdue_tasks: Number of overdue tasks
            total_tasks: Total number of tasks
            
        Returns:
            Productivity score (0-100)
        """
        # Base score from completion rate
        score = completion_rate
        
        # Penalty for overdue tasks
        if total_tasks > 0:
            overdue_penalty = (overdue_tasks / total_tasks) * 30  # Max 30 point penalty
            score = max(0, score - overdue_penalty)
        
        return round(score, 1)