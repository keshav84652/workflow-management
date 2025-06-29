"""
UserService: Handles all business logic for user operations.
"""

from core.db_import import db
from src.models import User, Firm
from services.activity_logging_service import ActivityLoggingService as ActivityService
from services.base import BaseService
from repositories.user_repository import UserRepository
from repositories.firm_repository import FirmRepository


class UserService(BaseService):
    def __init__(self):
        super().__init__()
        self.activity_logger = ActivityService()
        self.user_repository = UserRepository()
        self.firm_repository = FirmRepository()
    
    def get_users_for_firm(self, firm_id):
        """Get all users for a firm"""
        return self.user_repository.get_users_by_firm(firm_id)
    
    def get_user_by_id_and_firm(self, user_id, firm_id):
        """Get user by ID with firm access check"""
        user = self.user_repository.get_by_id(user_id)
        if user and user.firm_id == firm_id:
            return user
        return None
    
    def create_user(self, name, role, firm_id, created_by_user_id):
        """Create a new user"""
        try:
            if not name or not name.strip():
                return {'success': False, 'message': 'Name is required'}
            
            if not role:
                return {'success': False, 'message': 'Role is required'}
            
            # Check if firm exists
            firm = self.firm_repository.get_by_id(firm_id)
            if not firm:
                return {'success': False, 'message': 'Firm not found'}
            
            user = self.user_repository.create({
                'name': name.strip(),
                'role': role,
                'firm_id': firm_id
            })
            
            # Log activity
            ActivityService.log_entity_operation(
                entity_type='USER',
                operation='CREATE',
                entity_id=user.id,
                entity_name=user.name,
                details=f'User created with role: {role}',
                user_id=created_by_user_id
            )
            
            return {
                'success': True,
                'message': 'User created successfully',
                'user': {
                    'id': user.id,
                    'name': user.name,
                    'role': user.role,
                    'firm_id': user.firm_id
                }
            }
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    def get_users_by_firm(self, firm_id):
        """Get all users for a firm"""
        return self.user_repository.get_users_by_firm(firm_id)
    
    def update_user(self, user_id, name, role, firm_id, updated_by_user_id):
        """Update user information"""
        try:
            user = self.get_user_by_id_and_firm(user_id, firm_id)
            if not user:
                return {'success': False, 'message': 'User not found or access denied'}
            
            if not name or not name.strip():
                return {'success': False, 'message': 'Name is required'}
            
            user.name = name.strip()
            user.role = role
            
            db.session.commit()
            
            # Log activity
            ActivityService.log_entity_operation(
                entity_type='USER',
                operation='UPDATE',
                entity_id=user.id,
                entity_name=user.name,
                details=f'User updated - role: {role}',
                user_id=updated_by_user_id
            )
            
            return {
                'success': True,
                'message': 'User updated successfully',
                'user': {
                    'id': user.id,
                    'name': user.name,
                    'role': user.role,
                    'firm_id': user.firm_id
                }
            }
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
