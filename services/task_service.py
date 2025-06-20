"""
Task service layer for business logic
"""

from typing import Optional, List, Dict, Any
from flask import session
from core import db
from models import Task, Project, User, ActivityLog
from utils import create_activity_log


class TaskService:
    """Service class for task-related business operations"""
    
    @staticmethod
    def get_tasks_for_firm(firm_id: int) -> List[Task]:
        """Get all tasks for a firm"""
        return Task.query.filter_by(firm_id=firm_id).all()
    
    @staticmethod
    def get_task_by_id(task_id: int, firm_id: int) -> Optional[Task]:
        """Get a task by ID, ensuring it belongs to the firm"""
        return Task.query.filter_by(id=task_id, firm_id=firm_id).first()
    
    @staticmethod
    def update_task_status(task_id: int, status: str, firm_id: Optional[int] = None) -> Dict[str, Any]:
        """Update task status"""
        if firm_id is None:
            firm_id = session['firm_id']
        
        try:
            task = TaskService.get_task_by_id(task_id, firm_id)
            if not task:
                return {'success': False, 'message': 'Task not found'}
            
            old_status = task.status
            task.status = status
            db.session.commit()
            
            # Create activity log
            create_activity_log(
                user_id=session.get('user_id'),
                firm_id=firm_id,
                action='update',
                details=f'Updated task "{task.title}" status from {old_status} to {status}'
            )
            
            return {'success': True, 'message': f'Task status updated to {status}'}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'Error updating task: {str(e)}'}
    
    @staticmethod
    def get_task_statistics(firm_id: Optional[int] = None) -> Dict[str, Any]:
        """Get task statistics for dashboard"""
        if firm_id is None:
            firm_id = session['firm_id']
        
        tasks = TaskService.get_tasks_for_firm(firm_id)
        
        stats = {
            'total': len(tasks),
            'not_started': len([t for t in tasks if t.status == 'Not Started']),
            'in_progress': len([t for t in tasks if t.status == 'In Progress']),
            'completed': len([t for t in tasks if t.status == 'Completed']),
            'overdue': len([t for t in tasks if t.is_overdue]),
        }
        
        return stats