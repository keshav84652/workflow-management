"""
TemplateService: Handles all business logic for templates and related operations.
"""

from core.db_import import db
from models import Template, Task, ActivityLog, TaskComment


class TemplateService:
    @staticmethod
    def get_templates_by_firm(firm_id):
        """Get all templates for a specific firm"""
        return Template.query.filter_by(firm_id=firm_id).all()
    
    @staticmethod
    def get_tasks_by_project(project_id):
        """Get all tasks for a specific project"""
        return Task.query.filter_by(project_id=project_id).order_by(Task.due_date.asc()).all()
    
    @staticmethod
    def get_activity_logs_for_project(project_id, limit=10):
        """Get recent activity logs for a project"""
        return ActivityLog.query.filter_by(project_id=project_id).order_by(
            ActivityLog.timestamp.desc()
        ).limit(limit).all()
    
    @staticmethod
    def get_activity_logs_for_task(task_id, limit=10):
        """Get recent activity logs for a task"""
        return ActivityLog.query.filter_by(task_id=task_id).order_by(
            ActivityLog.timestamp.desc()
        ).limit(limit).all()
    
    @staticmethod
    def get_task_comments(task_id):
        """Get all comments for a task"""
        return TaskComment.query.filter_by(task_id=task_id).order_by(
            TaskComment.created_at.desc()
        ).all()
    
    @staticmethod
    def get_project_tasks_for_dependency(project_id):
        """Get tasks for dependency calculations"""
        return Task.query.filter_by(project_id=project_id).order_by(Task.title).all()