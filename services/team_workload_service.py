"""
TeamWorkloadService: Handles team workload analysis and distribution calculations.
Extracted from DashboardService God Object to follow Single Responsibility Principle.
"""

from typing import Dict, Any, List
from datetime import datetime, date, timedelta
from repositories.task_repository import TaskRepository
from repositories.user_repository import UserRepository
from services.base import BaseService


class TeamWorkloadService(BaseService):
    """Service for team workload analysis and distribution"""
    
    def __init__(self):
        super().__init__()
        self.task_repository = TaskRepository()
        self.user_repository = UserRepository()
    
    def get_team_workload(self, firm_id: int) -> Dict[str, Any]:
        """
        Analyze workload distribution across team members
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            Dictionary with team workload analysis
        """
        # Get all users and tasks
        users = self.user_repository.get_users_by_firm(firm_id)
        all_tasks = self.task_repository.get_tasks_by_firm(firm_id)
        active_tasks = [task for task in all_tasks if not task.is_completed]
        
        workload_data = []
        
        for user in users:
            user_tasks = [task for task in active_tasks if task.assignee_id == user.id]
            
            # Calculate workload metrics
            total_assigned = len(user_tasks)
            high_priority = len([task for task in user_tasks if task.priority == 'High'])
            medium_priority = len([task for task in user_tasks if task.priority == 'Medium'])
            low_priority = len([task for task in user_tasks if task.priority == 'Low'])
            overdue = len([task for task in user_tasks if task.is_overdue])
            
            # Calculate estimated hours
            estimated_hours = sum([task.estimated_hours or 0 for task in user_tasks])
            
            # Calculate urgency score based on due dates and priorities
            urgency_score = self._calculate_urgency_score(user_tasks)
            
            # Determine workload status
            workload_status = self._determine_workload_status(total_assigned, urgency_score, overdue)
            
            workload_data.append({
                'user_id': user.id,
                'name': user.name,
                'email': user.email,
                'total_tasks': total_assigned,
                'high_priority_tasks': high_priority,
                'medium_priority_tasks': medium_priority,
                'low_priority_tasks': low_priority,
                'overdue_tasks': overdue,
                'estimated_hours': round(estimated_hours, 1),
                'urgency_score': urgency_score,
                'workload_status': workload_status,
                'recent_tasks': user_tasks[:3]  # Most recent 3 tasks for preview
            })
        
        # Sort by urgency score (highest first)
        workload_data.sort(key=lambda x: x['urgency_score'], reverse=True)
        
        # Calculate team statistics
        total_team_tasks = sum([user['total_tasks'] for user in workload_data])
        avg_tasks_per_user = total_team_tasks / len(workload_data) if workload_data else 0
        
        overloaded_users = [user for user in workload_data if user['workload_status'] == 'Overloaded']
        underutilized_users = [user for user in workload_data if user['workload_status'] == 'Light']
        
        return {
            'users': workload_data,
            'team_summary': {
                'total_active_tasks': total_team_tasks,
                'average_tasks_per_user': round(avg_tasks_per_user, 1),
                'overloaded_users': len(overloaded_users),
                'balanced_users': len([user for user in workload_data if user['workload_status'] == 'Balanced']),
                'underutilized_users': len(underutilized_users),
                'total_estimated_hours': sum([user['estimated_hours'] for user in workload_data]),
                'workload_balance_score': self._calculate_workload_balance_score(workload_data)
            },
            'recommendations': self._generate_workload_recommendations(workload_data)
        }
    
    def get_workload_trends(self, firm_id: int, weeks_back: int = 4) -> Dict[str, Any]:
        """
        Analyze workload trends over time
        
        Args:
            firm_id: The firm's ID
            weeks_back: Number of weeks to analyze
            
        Returns:
            Dictionary with workload trend data
        """
        # This is a simplified implementation
        # In a real system, you'd track historical workload data
        
        users = self.user_repository.get_users_by_firm(firm_id)
        trend_data = []
        
        for user in users:
            # Get current workload
            current_workload = self.get_user_current_workload(user.id, firm_id)
            
            # Simulate historical data (in a real system, this would come from a log table)
            weeks_data = []
            for week in range(weeks_back):
                week_date = date.today() - timedelta(weeks=week)
                # Simulate some variance in workload
                variance = 0.8 + (week * 0.05)  # Slight increase over time
                simulated_tasks = int(current_workload['total_tasks'] * variance)
                
                weeks_data.append({
                    'week_starting': week_date.isoformat(),
                    'tasks_assigned': simulated_tasks,
                    'tasks_completed': int(simulated_tasks * 0.7),  # Assume 70% completion
                    'hours_logged': simulated_tasks * 8  # Assume 8 hours per task
                })
            
            trend_data.append({
                'user_id': user.id,
                'name': user.name,
                'weekly_data': weeks_data,
                'trend_direction': 'increasing' if weeks_data[0]['tasks_assigned'] > weeks_data[-1]['tasks_assigned'] else 'decreasing'
            })
        
        return {
            'users': trend_data,
            'period': f'{weeks_back} weeks'
        }
    
    def get_user_current_workload(self, user_id: int, firm_id: int) -> Dict[str, Any]:
        """
        Get detailed workload for a specific user
        
        Args:
            user_id: The user's ID
            firm_id: The firm's ID
            
        Returns:
            Dictionary with user workload details
        """
        all_tasks = self.task_repository.get_tasks_by_firm(firm_id)
        user_tasks = [task for task in all_tasks if task.assignee_id == user_id and not task.is_completed]
        
        return {
            'total_tasks': len(user_tasks),
            'high_priority': len([task for task in user_tasks if task.priority == 'High']),
            'medium_priority': len([task for task in user_tasks if task.priority == 'Medium']),
            'low_priority': len([task for task in user_tasks if task.priority == 'Low']),
            'overdue': len([task for task in user_tasks if task.is_overdue]),
            'due_this_week': len([task for task in user_tasks if task.due_date and task.due_date <= date.today() + timedelta(days=7)]),
            'estimated_hours': sum([task.estimated_hours or 0 for task in user_tasks])
        }
    
    def _calculate_urgency_score(self, tasks: List) -> float:
        """
        Calculate urgency score based on task priorities and due dates
        
        Args:
            tasks: List of tasks for a user
            
        Returns:
            Urgency score (0-100)
        """
        if not tasks:
            return 0
        
        score = 0
        for task in tasks:
            # Priority scoring
            if task.priority == 'High':
                score += 10
            elif task.priority == 'Medium':
                score += 5
            else:  # Low priority
                score += 2
            
            # Due date urgency
            if task.due_date:
                days_until_due = (task.due_date - date.today()).days
                if days_until_due < 0:  # Overdue
                    score += 15
                elif days_until_due <= 1:  # Due today or tomorrow
                    score += 10
                elif days_until_due <= 3:  # Due this week
                    score += 5
        
        # Normalize to 0-100 scale
        max_possible_score = len(tasks) * 25  # Max possible score per task
        normalized_score = (score / max_possible_score * 100) if max_possible_score > 0 else 0
        
        return min(100, round(normalized_score, 1))
    
    def _determine_workload_status(self, task_count: int, urgency_score: float, overdue_count: int) -> str:
        """
        Determine workload status based on task metrics
        
        Args:
            task_count: Number of assigned tasks
            urgency_score: Calculated urgency score
            overdue_count: Number of overdue tasks
            
        Returns:
            Workload status string
        """
        if overdue_count > 3 or urgency_score > 80 or task_count > 15:
            return 'Overloaded'
        elif task_count < 3 and urgency_score < 20:
            return 'Light'
        else:
            return 'Balanced'
    
    def _calculate_workload_balance_score(self, workload_data: List[Dict]) -> float:
        """
        Calculate overall team workload balance score
        
        Args:
            workload_data: List of user workload data
            
        Returns:
            Balance score (0-100, higher is better)
        """
        if not workload_data:
            return 0
        
        task_counts = [user['total_tasks'] for user in workload_data]
        avg_tasks = sum(task_counts) / len(task_counts)
        
        # Calculate standard deviation
        variance = sum([(count - avg_tasks) ** 2 for count in task_counts]) / len(task_counts)
        std_dev = variance ** 0.5
        
        # Convert to balance score (lower std dev = higher balance)
        # Assume perfect balance would have std dev of 0, worst case std dev of avg_tasks
        if avg_tasks == 0:
            return 100
        
        balance_score = max(0, 100 - (std_dev / avg_tasks * 100))
        return round(balance_score, 1)
    
    def _generate_workload_recommendations(self, workload_data: List[Dict]) -> List[str]:
        """
        Generate recommendations for workload balancing
        
        Args:
            workload_data: List of user workload data
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        overloaded_users = [user for user in workload_data if user['workload_status'] == 'Overloaded']
        underutilized_users = [user for user in workload_data if user['workload_status'] == 'Light']
        
        if overloaded_users:
            recommendations.append(f"{len(overloaded_users)} team member(s) are overloaded. Consider redistributing tasks.")
        
        if underutilized_users:
            recommendations.append(f"{len(underutilized_users)} team member(s) have light workloads and could take on more tasks.")
        
        if overloaded_users and underutilized_users:
            recommendations.append("Consider moving tasks from overloaded to underutilized team members.")
        
        high_overdue = [user for user in workload_data if user['overdue_tasks'] > 2]
        if high_overdue:
            recommendations.append(f"{len(high_overdue)} team member(s) have multiple overdue tasks. Review priorities and deadlines.")
        
        return recommendations