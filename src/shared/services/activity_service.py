"""
Activity Logging Service for CPA WorkflowPilot
Handles all activity logging across the application.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from src.shared.database.db_import import db
from src.models import ActivityLog, User, Project, Task
from src.shared.base import BaseService, transactional


class ActivityService(BaseService):
    """Service for logging and retrieving user activities"""
    
    def __init__(self):
        super().__init__()
    
    @transactional
    def log_activity(
        self,
        action: str,
        user_id: int,
        firm_id: int,
        project_id: Optional[int] = None,
        task_id: Optional[int] = None,
        details: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Log a user activity
        
        Args:
            action: Description of the action performed
            user_id: ID of the user performing the action
            firm_id: ID of the firm (for security validation)
            project_id: Optional project ID if action relates to a project
            task_id: Optional task ID if action relates to a task
            details: Optional additional details about the action
            
        Returns:
            Dict with success status and activity log data
        """
        try:
            # Validate user belongs to firm
            user = User.query.filter_by(id=user_id, firm_id=firm_id).first()
            if not user:
                return {
                    'success': False,
                    'message': 'User not found or access denied'
                }
            
            # Create activity log
            activity_log = ActivityLog(
                action=action,
                user_id=user_id,
                project_id=project_id,
                task_id=task_id,
                details=details,
                timestamp=datetime.utcnow()
            )
            
            db.session.add(activity_log)
            
            return {
                'success': True,
                'message': 'Activity logged successfully',
                'activity_id': activity_log.id
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to log activity: {str(e)}'
            }
    
    def get_recent_activities(
        self,
        firm_id: int,
        limit: int = 50,
        user_id: Optional[int] = None,
        project_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent activities for a firm
        
        Args:
            firm_id: Firm ID to get activities for
            limit: Maximum number of activities to return
            user_id: Optional filter by specific user
            project_id: Optional filter by specific project
            
        Returns:
            List of activity dictionaries
        """
        # Base query with joins for user information
        query = db.session.query(ActivityLog, User).join(
            User, ActivityLog.user_id == User.id
        ).filter(User.firm_id == firm_id)
        
        # Apply optional filters
        if user_id:
            query = query.filter(ActivityLog.user_id == user_id)
        if project_id:
            query = query.filter(ActivityLog.project_id == project_id)
        
        # Order by timestamp and limit
        activities = query.order_by(ActivityLog.timestamp.desc()).limit(limit).all()
        
        # Format results
        result = []
        for activity_log, user in activities:
            activity_dict = {
                'id': activity_log.id,
                'action': activity_log.action,
                'timestamp': activity_log.timestamp,
                'user_name': user.name,
                'user_id': user.id,
                'project_id': activity_log.project_id,
                'task_id': activity_log.task_id,
                'details': activity_log.details
            }
            result.append(activity_dict)
        
        return result
    
    def get_user_activity_summary(self, user_id: int, firm_id: int) -> Dict[str, Any]:
        """
        Get activity summary for a specific user
        
        Args:
            user_id: User ID to get summary for
            firm_id: Firm ID for security validation
            
        Returns:
            Dict with activity summary statistics
        """
        # Validate user belongs to firm
        user = User.query.filter_by(id=user_id, firm_id=firm_id).first()
        if not user:
            return {'error': 'User not found or access denied'}
        
        # Get activity counts
        total_activities = ActivityLog.query.filter_by(user_id=user_id).count()
        
        # Get activities by type (simplified categories)
        recent_count = ActivityLog.query.filter_by(user_id=user_id).filter(
            ActivityLog.timestamp >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        return {
            'user_name': user.name,
            'total_activities': total_activities,
            'activities_today': recent_count,
            'last_activity': ActivityLog.query.filter_by(user_id=user_id).order_by(
                ActivityLog.timestamp.desc()
            ).first()
        }


# Create singleton instance for global access
ActivityLoggingService = ActivityService