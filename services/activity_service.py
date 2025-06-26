"""
Activity Service for managing activity logs and audit trails
Centralized business logic for activity tracking
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

import importlib.util
import os

# Import db from root core.py file
spec = importlib.util.spec_from_file_location("core", os.path.join(os.path.dirname(os.path.dirname(__file__)), "core.py"))
core_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core_module)
db = core_module.db
from models import ActivityLog


class ActivityService:
    """Service for handling activity logs and audit trails"""
    
    @staticmethod
    def create_activity_log(action: str, user_id: int, project_id: Optional[int] = None, 
                          task_id: Optional[int] = None, details: Optional[str] = None) -> None:
        """Create an activity log entry"""
        try:
            log = ActivityLog(
                action=action,
                user_id=user_id,
                project_id=project_id,
                task_id=task_id,
                details=details
            )
            db.session.add(log)
            db.session.commit()
            logging.info(f"Activity log created: {action} by user {user_id}")
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Failed to create activity log: {str(e)}")
            raise
    
    @staticmethod
    def get_project_activity(project_id: int, limit: int = 50) -> List[ActivityLog]:
        """Get recent activity for a project"""
        try:
            return ActivityLog.query.filter_by(
                project_id=project_id
            ).order_by(ActivityLog.timestamp.desc()).limit(limit).all()
            
        except Exception as e:
            logging.error(f"Failed to get project activity: {str(e)}")
            return []
    
    @staticmethod
    def get_task_activity(task_id: int, limit: int = 50) -> List[ActivityLog]:
        """Get recent activity for a task"""
        try:
            return ActivityLog.query.filter_by(
                task_id=task_id
            ).order_by(ActivityLog.timestamp.desc()).limit(limit).all()
            
        except Exception as e:
            logging.error(f"Failed to get task activity: {str(e)}")
            return []
    
    @staticmethod
    def get_user_activity(user_id: int, limit: int = 50) -> List[ActivityLog]:
        """Get recent activity for a user"""
        try:
            return ActivityLog.query.filter_by(
                user_id=user_id
            ).order_by(ActivityLog.timestamp.desc()).limit(limit).all()
            
        except Exception as e:
            logging.error(f"Failed to get user activity: {str(e)}")
            return []
    
    @staticmethod
    def get_recent_activity(firm_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent activity across the system or for a specific firm"""
        try:
            query = ActivityLog.query
            
            # If firm_id provided, filter by firm through project relationship
            if firm_id:
                from models import Project
                query = query.join(Project, ActivityLog.project_id == Project.id, isouter=True).filter(
                    db.or_(
                        Project.firm_id == firm_id,
                        ActivityLog.project_id.is_(None)  # Include activities without project
                    )
                )
            
            activities = query.order_by(ActivityLog.timestamp.desc()).limit(limit).all()
            
            # Format for API response
            result = []
            for activity in activities:
                result.append({
                    'id': activity.id,
                    'action': activity.action,
                    'user_id': activity.user_id,
                    'user_name': activity.user.name if hasattr(activity, 'user') and activity.user else 'Unknown',
                    'project_id': activity.project_id,
                    'project_name': activity.project.name if hasattr(activity, 'project') and activity.project else None,
                    'task_id': activity.task_id,
                    'task_title': activity.task.title if hasattr(activity, 'task') and activity.task else None,
                    'timestamp': activity.timestamp.isoformat() if activity.timestamp else None,
                    'details': activity.details
                })
            
            return result
            
        except Exception as e:
            logging.error(f"Failed to get recent activity: {str(e)}")
            return []