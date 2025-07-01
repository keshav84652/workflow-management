"""
UserService: Handles all business logic for user operations.
"""

from src.shared.database.db_import import db
from src.models import User, Firm
from src.shared.services import ActivityLoggingService as ActivityService
from src.shared.base import BaseService, transactional
from src.shared.di_container import get_service
from src.modules.auth.interface import IAuthService, IFirmService


class UserService(BaseService):
    def __init__(self):
        super().__init__()
        # Use dependency injection to get auth services
        try:
            self.auth_service = get_service(IAuthService)
            self.firm_service = get_service(IFirmService)
        except ValueError:
            # Fallback to direct instantiation if DI not set up
            from src.modules.auth.service import AuthService
            from src.modules.auth.firm_service import FirmService
            self.auth_service = AuthService()
            self.firm_service = FirmService()
    
    def get_users_for_firm(self, firm_id):
        """Get all users for a firm"""
        return self.auth_service.get_users_for_firm(firm_id)
    
    def get_user_by_id_and_firm(self, user_id, firm_id):
        """Get user by ID with firm access check"""
        return self.auth_service.get_user_by_id(user_id, firm_id)
    
    @transactional
    def create_user(self, name, role, firm_id, created_by_user_id):
        """Create a new user"""
        if not name or not name.strip():
            return {'success': False, 'message': 'Name is required'}
        
        if not role:
            return {'success': False, 'message': 'Role is required'}
        
        # Check if firm exists
        firm = self.firm_service.get_firm_by_id(firm_id)
        if not firm:
            return {'success': False, 'message': 'Firm not found'}
        
        # Create user through auth service
        result = self.auth_service.create_user({
            'name': name.strip(),
            'role': role,
            'firm_id': firm_id
        }, firm_id)
        
        if not result['success']:
            return result
        
        user = result['user']
        
        # Log activity
        ActivityService.log_entity_operation(
            entity_type='USER',
            operation='CREATE',
            entity_id=user['id'],
            entity_name=user['name'],
            details=f'User created with role: {role}',
            user_id=created_by_user_id
        )
        
        return {
            'success': True,
            'message': 'User created successfully',
            'user': user
        }
    
    def get_users_by_firm(self, firm_id):
        """Get all users for a firm"""
        return self.auth_service.get_users_for_firm(firm_id)
    
    @transactional
    def update_user(self, user_id, name, role, firm_id, updated_by_user_id):
        """Update user information"""
        if not name or not name.strip():
            return {'success': False, 'message': 'Name is required'}
        
        # Update user through auth service
        result = self.auth_service.update_user(user_id, {
            'name': name.strip(),
            'role': role
        }, firm_id)
        
        if not result['success']:
            return result
        
        user = result['user']
        
        # Log activity
        ActivityService.log_entity_operation(
            entity_type='USER',
            operation='UPDATE',
            entity_id=user['id'],
            entity_name=user['name'],
            details=f'User updated - role: {role}',
            user_id=updated_by_user_id
        )
        
        return {
            'success': True,
            'message': 'User updated successfully',
            'user': user
        }
