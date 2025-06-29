"""
Project Helper Service for CPA WorkflowPilot
Contains helper methods for project and task operations that were previously in TemplateService.
"""

from typing import List
from src.shared.base import BaseService
from src.models import Task, ActivityLog, TaskComment


class ProjectHelperService(BaseService):
    """Helper service for project-related operations"""
    
    def __init__(self):
        super().__init__()
    
    def get_tasks_by_project(self, project_id: int) -> List[Task]:
        """Get all tasks for a specific project"""
        return Task.query.filter_by(project_id=project_id).order_by(Task.due_date.asc()).all()
    
    def get_activity_logs_for_project(self, project_id: int, limit: int = 10) -> List[ActivityLog]:
        """Get recent activity logs for a project"""
        return ActivityLog.query.filter_by(project_id=project_id).order_by(
            ActivityLog.timestamp.desc()
        ).limit(limit).all()
    
    def get_activity_logs_for_task(self, task_id: int, limit: int = 10) -> List[ActivityLog]:
        """Get recent activity logs for a task"""
        return ActivityLog.query.filter_by(task_id=task_id).order_by(
            ActivityLog.timestamp.desc()
        ).limit(limit).all()
    
    def get_task_comments(self, task_id: int) -> List[TaskComment]:
        """Get all comments for a task"""
        return TaskComment.query.filter_by(task_id=task_id).order_by(
            TaskComment.created_at.desc()
        ).all()
    
    def get_project_tasks_for_dependency(self, project_id: int) -> List[Task]:
        """Get tasks for dependency calculations"""
        return Task.query.filter_by(project_id=project_id).order_by(Task.title).all()