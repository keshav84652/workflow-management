"""
Admin Repository for CPA WorkflowPilot
Provides data access layer for administrative operations.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import func

from src.shared.database.db_import import db
from src.models import Firm, User, Project, Task, WorkType, TaskStatus
from src.shared.repositories import BaseRepository


class AdminRepository(BaseRepository[User]):
    """Repository for administrative data operations"""
    
    def __init__(self):
        super().__init__(User)
    
    def get_system_statistics(self) -> Dict[str, int]:
        """
        Get system-wide statistics for admin dashboard
        
        Returns:
            Dictionary containing system-wide counts
        """
        try:
            # Get total counts using efficient queries
            total_projects = db.session.query(func.count(Project.id)).scalar() or 0
            total_tasks = db.session.query(func.count(Task.id)).scalar() or 0
            total_users = db.session.query(func.count(User.id)).scalar() or 0
            total_firms = db.session.query(func.count(Firm.id)).scalar() or 0
            active_firms = db.session.query(func.count(Firm.id)).filter(Firm.is_active == True).scalar() or 0
            
            return {
                'total_projects': total_projects,
                'total_tasks': total_tasks,
                'total_users': total_users,
                'total_firms': total_firms,
                'active_firms': active_firms,
                'inactive_firms': total_firms - active_firms
            }
            
        except Exception as e:
            # Return empty statistics on error
            return {
                'total_projects': 0,
                'total_tasks': 0,
                'total_users': 0,
                'total_firms': 0,
                'active_firms': 0,
                'inactive_firms': 0
            }
    
    def get_work_types(self) -> List[WorkType]:
        """Get all work types"""
        return WorkType.query.order_by(WorkType.name.asc()).all()
    
    def get_task_statuses(self) -> List[TaskStatus]:
        """Get all task statuses"""
        return TaskStatus.query.order_by(TaskStatus.order.asc()).all()
    
    def create_work_type(self, name: str, description: str = None, 
                        color: str = None, is_active: bool = True) -> WorkType:
        """
        Create a new work type
        
        Args:
            name: Work type name
            description: Optional description
            color: Optional color code
            is_active: Whether the work type is active
            
        Returns:
            Created WorkType object
        """
        work_type = WorkType(
            name=name.strip(),
            description=description.strip() if description else None,
            color=color,
            is_active=is_active
        )
        db.session.add(work_type)
        return work_type
    
    def create_task_status(self, name: str, order: int, color: str = None, 
                          is_active: bool = True) -> TaskStatus:
        """
        Create a new task status
        
        Args:
            name: Status name
            order: Display order
            color: Optional color code
            is_active: Whether the status is active
            
        Returns:
            Created TaskStatus object
        """
        task_status = TaskStatus(
            name=name.strip(),
            order=order,
            color=color,
            is_active=is_active
        )
        db.session.add(task_status)
        return task_status
    
    def update_work_type(self, work_type_id: int, **kwargs) -> Optional[WorkType]:
        """
        Update a work type
        
        Args:
            work_type_id: ID of work type to update
            **kwargs: Fields to update
            
        Returns:
            Updated WorkType object or None if not found
        """
        work_type = WorkType.query.get(work_type_id)
        if work_type:
            return self.update(work_type, **kwargs)
        return None
    
    def update_task_status(self, status_id: int, **kwargs) -> Optional[TaskStatus]:
        """
        Update a task status
        
        Args:
            status_id: ID of status to update
            **kwargs: Fields to update
            
        Returns:
            Updated TaskStatus object or None if not found
        """
        task_status = TaskStatus.query.get(status_id)
        if task_status:
            return self.update(task_status, **kwargs)
        return None
    
    def delete_work_type(self, work_type_id: int) -> bool:
        """
        Delete a work type (soft delete by setting is_active=False)
        
        Args:
            work_type_id: ID of work type to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        work_type = WorkType.query.get(work_type_id)
        if work_type:
            work_type.is_active = False
            return True
        return False
    
    def delete_task_status(self, status_id: int) -> bool:
        """
        Delete a task status (soft delete by setting is_active=False)
        
        Args:
            status_id: ID of status to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        task_status = TaskStatus.query.get(status_id)
        if task_status:
            task_status.is_active = False
            return True
        return False