# Authentication Services
# Service layer for authentication and user management following OpenProject patterns

from typing import Dict, Optional
from datetime import datetime

from app.auth.models import Firm, User, UserRole, ActivityLog
from app.core.services import BaseService, ServiceResult, CreateService, UpdateService
from app.core.extensions import db


class AuthService(BaseService):
    """Authentication service for firm and user management"""
    
    def authenticate_firm(self, access_code: str) -> ServiceResult:
        """Authenticate firm by access code"""
        if not access_code:
            return ServiceResult.error_result({'access_code': 'Access code is required'})
        
        firm = Firm.query.filter_by(access_code=access_code, is_active=True).first()
        
        if not firm:
            return ServiceResult.error_result({'access_code': 'Invalid access code'})
        
        return ServiceResult.success_result(firm)
    
    def authenticate_user(self, user_id: int, firm_id: int) -> ServiceResult:
        """Authenticate user within firm context"""
        user = User.query.filter_by(
            id=user_id, 
            firm_id=firm_id, 
            is_active=True
        ).first()
        
        if not user:
            return ServiceResult.error_result({'user': 'Invalid user selection'})
        
        return ServiceResult.success_result(user)


class UserService(BaseService):
    """User management service following OpenProject patterns"""
    
    def create_user(self, name: str, firm_id: int, role: UserRole = UserRole.STAFF, 
                   email: Optional[str] = None, **kwargs) -> ServiceResult:
        """Create new user in firm"""
        
        # Validation
        validation_result = self._validate_user_data(name, email, role, firm_id)
        if validation_result.is_failure():
            return validation_result
        
        # Check firm user limit
        firm = Firm.query.get(firm_id)
        if not firm or not firm.can_add_user():
            return ServiceResult.error_result({'firm': 'User limit reached for this firm'})
        
        # Authorization check
        if not self._can_create_user(role):
            return ServiceResult.error_result({'permission': 'Insufficient permissions to create user'})
        
        try:
            # Create user
            user = User(
                name=name,
                email=email,
                role=role,
                firm_id=firm_id,
                created_by_id=self.user.id if self.user else None,
                **kwargs
            )
            
            db.session.add(user)
            db.session.commit()
            
            # Log activity
            self._log_user_activity(
                action='User Created',
                entity_id=user.id,
                firm_id=firm_id,
                details=f'Created user: {name} with role: {role.value}'
            )
            
            return ServiceResult.success_result(user)
            
        except Exception as e:
            db.session.rollback()
            return ServiceResult.error_result({'database': str(e)})
    
    def update_user(self, user: User, **kwargs) -> ServiceResult:
        """Update existing user"""
        
        # Authorization check
        if not self._can_modify_user(user):
            return ServiceResult.error_result({'permission': 'Cannot modify this user'})
        
        # Validation
        if 'email' in kwargs and kwargs['email']:
            existing_user = User.query.filter_by(email=kwargs['email']).first()
            if existing_user and existing_user.id != user.id:
                return ServiceResult.error_result({'email': 'Email already in use'})
        
        try:
            # Track changes for audit
            changes = []
            
            for field, value in kwargs.items():
                if hasattr(user, field) and value is not None:
                    old_value = getattr(user, field)
                    if old_value != value:
                        changes.append(f'{field}: {old_value} -> {value}')
                        setattr(user, field, value)
            
            user.updated_by_id = self.user.id if self.user else None
            db.session.commit()
            
            # Log activity
            if changes:
                self._log_user_activity(
                    action='User Updated',
                    entity_id=user.id,
                    firm_id=user.firm_id,
                    details=f'Updated: {", ".join(changes)}'
                )
            
            return ServiceResult.success_result(user)
            
        except Exception as e:
            db.session.rollback()
            return ServiceResult.error_result({'database': str(e)})
    
    def toggle_user_status(self, user: User) -> ServiceResult:
        """Toggle user active status"""
        
        # Authorization check
        if not self._can_modify_user(user):
            return ServiceResult.error_result({'permission': 'Cannot modify this user'})
        
        # Prevent self-deactivation
        if self.user and self.user.id == user.id and user.is_active:
            return ServiceResult.error_result({'user': 'Cannot deactivate yourself'})
        
        try:
            old_status = user.is_active
            user.is_active = not user.is_active
            user.updated_by_id = self.user.id if self.user else None
            
            db.session.commit()
            
            # Log activity
            action = 'User Deactivated' if old_status else 'User Activated'
            self._log_user_activity(
                action=action,
                entity_id=user.id,
                firm_id=user.firm_id,
                details=f'Changed status from {old_status} to {user.is_active}'
            )
            
            return ServiceResult.success_result(user)
            
        except Exception as e:
            db.session.rollback()
            return ServiceResult.error_result({'database': str(e)})
    
    def update_profile(self, user: User, **kwargs) -> ServiceResult:
        """Update user's own profile"""
        
        # Users can only update their own profile
        if self.user.id != user.id:
            return ServiceResult.error_result({'permission': 'Can only update own profile'})
        
        # Remove sensitive fields that users shouldn't modify themselves
        restricted_fields = ['role', 'firm_id', 'is_active', 'hourly_rate']
        filtered_kwargs = {k: v for k, v in kwargs.items() if k not in restricted_fields}
        
        return self.update_user(user, **filtered_kwargs)
    
    def _validate_user_data(self, name: str, email: Optional[str], role: UserRole, firm_id: int) -> ServiceResult:
        """Validate user data"""
        errors = {}
        
        if not name or len(name.strip()) < 2:
            errors['name'] = 'Name must be at least 2 characters long'
        
        if email:
            if '@' not in email:
                errors['email'] = 'Invalid email format'
            elif User.query.filter_by(email=email).first():
                errors['email'] = 'Email already in use'
        
        if not isinstance(role, UserRole):
            errors['role'] = 'Invalid role specified'
        
        if not Firm.query.get(firm_id):
            errors['firm'] = 'Invalid firm specified'
        
        if errors:
            return ServiceResult.error_result(errors)
        
        return ServiceResult.success_result()
    
    def _can_create_user(self, role: UserRole) -> bool:
        """Check if current user can create user with specified role"""
        if not self.user:
            return False
        
        # Only admins and partners can create users
        if not self.user.can_manage_users:
            return False
        
        # Only admins can create other admins
        if role == UserRole.ADMIN and self.user.role != UserRole.ADMIN:
            return False
        
        return True
    
    def _can_modify_user(self, target_user: User) -> bool:
        """Check if current user can modify target user"""
        if not self.user:
            return False
        
        # Must be in same firm
        if self.user.firm_id != target_user.firm_id:
            return False
        
        # Admins can modify anyone
        if self.user.role == UserRole.ADMIN:
            return True
        
        # Partners can modify non-admins
        if self.user.role == UserRole.PARTNER and target_user.role != UserRole.ADMIN:
            return True
        
        # Users can modify themselves (limited)
        if self.user.id == target_user.id:
            return True
        
        return False
    
    def _log_user_activity(self, action: str, entity_id: int, firm_id: int, details: str = None):
        """Log user-related activity"""
        activity = ActivityLog(
            action=action,
            entity_type='user',
            entity_id=entity_id,
            firm_id=firm_id,
            details=details,
            created_by_id=self.user.id if self.user else None
        )
        db.session.add(activity)


class FirmService(BaseService):
    """Firm management service"""
    
    def call(self, **kwargs) -> ServiceResult:
        """Abstract method implementation"""
        return ServiceResult.success_result()
    
    def create_firm(self, name: str, access_code: str, admin_user_name: str) -> ServiceResult:
        """Create new firm with admin user"""
        
        # Validation
        if not name or not access_code or not admin_user_name:
            return ServiceResult.error_result({
                'required': 'Firm name, access code, and admin name are required'
            })
        
        if Firm.query.filter_by(access_code=access_code).first():
            return ServiceResult.error_result({'access_code': 'Access code already in use'})
        
        try:
            # Create firm
            firm = Firm(name=name, access_code=access_code)
            db.session.add(firm)
            db.session.flush()  # Get firm ID
            
            # Create admin user
            admin_user = User(
                name=admin_user_name,
                role=UserRole.ADMIN,
                firm_id=firm.id
            )
            db.session.add(admin_user)
            db.session.commit()
            
            return ServiceResult.success_result({
                'firm': firm,
                'admin_user': admin_user
            })
            
        except Exception as e:
            db.session.rollback()
            return ServiceResult.error_result({'database': str(e)})