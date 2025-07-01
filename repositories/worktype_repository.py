"""
WorkType Repository for data access operations
"""

from typing import List, Optional
from repositories.base import SqlAlchemyRepository
from models import WorkType


class WorkTypeRepository(SqlAlchemyRepository[WorkType]):
    """Repository for WorkType entity"""
    
    def __init__(self):
        super().__init__(WorkType)
    
    def get_work_types_by_firm(self, firm_id: int, active_only: bool = True) -> List[WorkType]:
        """
        Get all work types for a specific firm
        
        Args:
            firm_id: The firm's ID
            active_only: Whether to return only active work types
            
        Returns:
            List of WorkType objects
        """
        query = self.model.query.filter_by(firm_id=firm_id)
        
        if active_only:
            query = query.filter_by(is_active=True)
        
        return query.all()
    
    def get_active_work_types_by_firm(self, firm_id: int) -> List[WorkType]:
        """
        Get active work types for a firm
        
        Args:
            firm_id: The firm's ID
            
        Returns:
            List of active WorkType objects
        """
        return self.get_work_types_by_firm(firm_id, active_only=True)
    
    def get_work_type_by_name_and_firm(self, name: str, firm_id: int) -> Optional[WorkType]:
        """
        Get work type by name and firm
        
        Args:
            name: Work type name
            firm_id: The firm's ID
            
        Returns:
            WorkType object or None
        """
        return self.model.query.filter_by(
            name=name,
            firm_id=firm_id
        ).first()
    
    def create_work_type(self, name: str, firm_id: int, color: str = None, 
                        description: str = None) -> WorkType:
        """
        Create a new work type
        
        Args:
            name: Work type name
            firm_id: The firm's ID
            color: Display color (optional)
            description: Description (optional)
            
        Returns:
            Created WorkType object
        """
        work_type_data = {
            'name': name,
            'firm_id': firm_id,
            'is_active': True
        }
        
        if color:
            work_type_data['color'] = color
        if description:
            work_type_data['description'] = description
            
        return self.create(work_type_data)
    
    def deactivate_work_type(self, work_type_id: int, firm_id: int) -> bool:
        """
        Deactivate a work type (soft delete)
        
        Args:
            work_type_id: Work type ID
            firm_id: The firm's ID for access control
            
        Returns:
            True if successful, False otherwise
        """
        work_type = self.model.query.filter_by(
            id=work_type_id,
            firm_id=firm_id
        ).first()
        
        if work_type:
            return self.update(work_type_id, {'is_active': False}) is not None
        
        return False