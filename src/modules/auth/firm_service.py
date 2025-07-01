"""
FirmService: Handles all business logic for firm management operations.

This service implements the IFirmService interface and provides controlled access
to firm data through the module boundary.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from src.shared.database.db_import import db
from src.models import Firm
from src.shared.base import BaseService, transactional
from src.shared.utils.consolidated import generate_access_code
from .interface import IFirmService
from .firm_repository import FirmRepository


class FirmService(BaseService, IFirmService):
    """Service class for firm management operations"""
    
    def __init__(self):
        super().__init__()
        self.firm_repository = FirmRepository()
    
    def get_firm_by_id(self, firm_id: int) -> Optional[Dict[str, Any]]:
        """
        Get firm by ID
        
        Args:
            firm_id: Firm ID
            
        Returns:
            Firm data dictionary or None if not found
        """
        try:
            firm = self.firm_repository.get_by_id(firm_id)
            if not firm:
                return None
                
            return {
                'id': firm.id,
                'name': firm.name,
                'access_code': firm.access_code,
                'is_active': firm.is_active,
                'created_at': firm.created_at.isoformat() if firm.created_at else None
            }
        except Exception:
            return None
    
    def get_firm_by_access_code(self, access_code: str) -> Optional[Dict[str, Any]]:
        """
        Get firm by access code
        
        Args:
            access_code: Firm's access code
            
        Returns:
            Firm data dictionary or None if not found
        """
        try:
            firm = self.firm_repository.get_by_access_code(access_code, active_only=False)
            if not firm:
                return None
                
            return {
                'id': firm.id,
                'name': firm.name,
                'access_code': firm.access_code,
                'is_active': firm.is_active,
                'created_at': firm.created_at.isoformat() if firm.created_at else None
            }
        except Exception:
            return None
    
    @transactional
    def create_firm(self, firm_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new firm
        
        Args:
            firm_data: Firm information (must include 'name')
            
        Returns:
            Result dictionary with success status and firm data
        """
        try:
            name = firm_data.get('name', '').strip()
            if not name:
                return {
                    'success': False,
                    'message': 'Firm name is required',
                    'firm': None
                }
            
            # Generate unique access code
            access_code = generate_access_code()
            while self.firm_repository.get_by_access_code(access_code, active_only=False):
                access_code = generate_access_code()
            
            # Create new firm
            firm = Firm(
                name=name,
                access_code=access_code,
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            db.session.add(firm)
            
            return {
                'success': True,
                'message': f'Firm "{name}" created successfully',
                'firm': {
                    'id': firm.id,
                    'name': firm.name,
                    'access_code': firm.access_code,
                    'is_active': firm.is_active
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error creating firm: {str(e)}',
                'firm': None
            }
    
    @transactional
    def update_firm(self, firm_id: int, firm_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing firm
        
        Args:
            firm_id: Firm ID
            firm_data: Updated firm information
            
        Returns:
            Result dictionary with success status
        """
        try:
            firm = self.firm_repository.get_by_id(firm_id)
            if not firm:
                return {
                    'success': False,
                    'message': 'Firm not found'
                }
            
            # Update allowed fields
            if 'name' in firm_data and firm_data['name'].strip():
                firm.name = firm_data['name'].strip()
            
            if 'is_active' in firm_data:
                firm.is_active = bool(firm_data['is_active'])
            
            return {
                'success': True,
                'message': f'Firm "{firm.name}" updated successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error updating firm: {str(e)}'
            }
    
    def get_all_firms(self) -> List[Dict[str, Any]]:
        """
        Get all firms in the system (admin only)
        
        Returns:
            List of firm data dictionaries
        """
        try:
            firms = self.firm_repository.get_all()
            
            return [{
                'id': firm.id,
                'name': firm.name,
                'access_code': firm.access_code,
                'is_active': firm.is_active,
                'created_at': firm.created_at.isoformat() if firm.created_at else None
            } for firm in firms]
            
        except Exception:
            return []
    
    @transactional
    def toggle_firm_status(self, firm_id: int) -> Dict[str, Any]:
        """
        Toggle a firm's active status (admin only)
        
        Args:
            firm_id: Firm ID
            
        Returns:
            Result dictionary with success status
        """
        try:
            firm = self.firm_repository.get_by_id(firm_id)
            if not firm:
                return {
                    'success': False,
                    'message': 'Firm not found'
                }
            
            firm.is_active = not firm.is_active
            
            status = 'activated' if firm.is_active else 'deactivated'
            return {
                'success': True,
                'message': f'Firm "{firm.name}" {status} successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error updating firm status: {str(e)}'
            }