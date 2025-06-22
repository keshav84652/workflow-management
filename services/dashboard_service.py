"""
Dashboard service layer for business logic
"""

from typing import Dict, Any, List
from datetime import datetime, date, timedelta
from flask import session

from core import db
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