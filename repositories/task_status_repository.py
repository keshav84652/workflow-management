"""
TaskStatus Repository for data access operations
"""

from typing import List, Optional
from repositories.base import SqlAlchemyRepository
from models import TaskStatus


class TaskStatusRepository(SqlAlchemyRepository[TaskStatus]):
    """Repository for TaskStatus entity"""
    
    def __init__(self):
        super().__init__(TaskStatus)
    
    def get_task_statuses_by_firm(self, firm_id: int, active_only: bool = True) -> List[TaskStatus]:
        """
        Get all task statuses for a specific firm
        
        Args:
            firm_id: The firm's ID
            active_only: Whether to return only active statuses
            
        Returns:
            List of TaskStatus objects
        """
        query = self.model.query.filter_by(firm_id=firm_id)
        
        if active_only:
            query = query.filter_by(is_active=True)
        
        return query.order_by(TaskStatus.sort_order).all()
    
    def get_task_statuses_by_work_type(self, work_type_id: int, firm_id: int) -> List[TaskStatus]:
        """
        Get task statuses for a specific work type
        
        Args:
            work_type_id: Work type ID
            firm_id: The firm's ID for access control
            
        Returns:
            List of TaskStatus objects
        """
        return self.model.query.filter_by(
            work_type_id=work_type_id,
            firm_id=firm_id,
            is_active=True
        ).order_by(TaskStatus.sort_order).all()
    
    def get_default_task_status(self, firm_id: int) -> Optional[TaskStatus]:
        """
        Get the default task status for a firm
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            Default TaskStatus object or None
        """
        return self.model.query.filter_by(
            firm_id=firm_id,
            is_default=True,
            is_active=True
        ).first()
    
    def get_task_status_by_name(self, name: str, firm_id: int) -> Optional[TaskStatus]:
        """
        Get task status by name and firm
        
        Args:
            name: Status name
            firm_id: The firm's ID
            
        Returns:
            TaskStatus object or None
        """
        return self.model.query.filter_by(
            name=name,
            firm_id=firm_id
        ).first()
    
    def create_task_status(self, name: str, firm_id: int, work_type_id: int = None,
                          color: str = None, sort_order: int = None, 
                          is_default: bool = False) -> TaskStatus:
        """
        Create a new task status
        
        Args:
            name: Status name
            firm_id: The firm's ID
            work_type_id: Associated work type ID (optional)
            color: Display color (optional)
            sort_order: Sort order (optional)
            is_default: Whether this is the default status
            
        Returns:
            Created TaskStatus object
        """
        # If no sort order specified, get the next available
        if sort_order is None:
            max_order = self.model.query.filter_by(firm_id=firm_id).count()
            sort_order = max_order + 1
        
        status_data = {
            'name': name,
            'firm_id': firm_id,
            'sort_order': sort_order,
            'is_active': True,
            'is_default': is_default
        }
        
        if work_type_id:
            status_data['work_type_id'] = work_type_id
        if color:
            status_data['color'] = color
            
        return self.create(status_data)
    
    def reorder_statuses(self, firm_id: int, status_order: List[int]) -> bool:
        """
        Reorder task statuses
        
        Args:
            firm_id: The firm's ID
            status_order: List of status IDs in desired order
            
        Returns:
            True if successful, False otherwise
        """
        try:
            for i, status_id in enumerate(status_order):
                status = self.model.query.filter_by(
                    id=status_id,
                    firm_id=firm_id
                ).first()
                
                if status:
                    status.sort_order = i + 1
            
            from core.db_import import db
            db.session.commit()
            return True
            
        except Exception:
            from core.db_import import db
            db.session.rollback()
            return False