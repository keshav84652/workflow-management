# Permission System
# Rights-based permission system inspired by Vikunja + OpenProject policy patterns

from functools import wraps
from flask import session, jsonify, request, redirect, url_for, abort
from enum import Enum

from app.core.models import Right


class EntityType(Enum):
    """Entity types for permission checking"""
    FIRM = 'firm'
    CLIENT = 'client'
    PROJECT = 'project'
    TASK = 'task'
    DOCUMENT = 'document'
    REPORT = 'report'
    USER = 'user'


class PermissionPolicy:
    """Base policy class inspired by OpenProject's policy system"""
    
    def __init__(self, user, entity):
        self.user = user
        self.entity = entity
    
    def can_read(self):
        """Check read permission"""
        return self.user and self.user.is_active
    
    def can_write(self):
        """Check write permission"""
        return self.can_read()
    
    def can_admin(self):
        """Check admin permission"""
        return self.user and self.user.role == 'Admin'


class FirmBasedPolicy(PermissionPolicy):
    """Policy for firm-based entities"""
    
    def can_read(self):
        """Check if user can read entity in same firm"""
        if not super().can_read():
            return False
        
        # Check firm membership
        if hasattr(self.entity, 'firm_id'):
            return self.user.firm_id == self.entity.firm_id
        
        return True
    
    def can_write(self):
        """Check if user can write to entity"""
        if not self.can_read():
            return False
        
        # Additional role-based checks can be added here
        return True
    
    def can_admin(self):
        """Check if user can administer entity"""
        return super().can_admin() and self.can_read()


def get_current_user():
    """Get current user from session"""
    from app.auth.models import User
    
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    return None


def requires_permission(entity_type: EntityType, right: Right = Right.READ):
    """Permission decorator inspired by Vikunja's permission system"""
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            
            if not user:
                if request.is_json:
                    return jsonify({'error': 'Authentication required'}), 401
                return redirect(url_for('auth.login'))
            
            # Get entity if ID is provided in route parameters
            entity = None
            entity_id = kwargs.get('id') or kwargs.get(f'{entity_type.value}_id')
            
            if entity_id:
                entity = get_entity_by_type_and_id(entity_type, entity_id)
                if not entity:
                    if request.is_json:
                        return jsonify({'error': 'Entity not found'}), 404
                    return abort(404)
            
            # Check permission using policy
            policy = get_policy_for_entity(user, entity)
            
            if right == Right.READ and not policy.can_read():
                return permission_denied_response()
            elif right == Right.WRITE and not policy.can_write():
                return permission_denied_response()
            elif right == Right.ADMIN and not policy.can_admin():
                return permission_denied_response()
            
            # Add user and entity to kwargs for use in route
            kwargs['current_user'] = user
            if entity:
                kwargs['entity'] = entity
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def permission_denied_response():
    """Return appropriate permission denied response"""
    if request.is_json:
        return jsonify({'error': 'Permission denied'}), 403
    from flask import abort
    abort(403)


def get_entity_by_type_and_id(entity_type: EntityType, entity_id: int):
    """Get entity by type and ID"""
    if entity_type == EntityType.CLIENT:
        from app.clients.models import Client
        return Client.query.get(entity_id)
    elif entity_type == EntityType.PROJECT:
        from app.projects.models import Project
        return Project.query.get(entity_id)
    elif entity_type == EntityType.TASK:
        from app.tasks.models import Task
        return Task.query.get(entity_id)
    elif entity_type == EntityType.DOCUMENT:
        from app.documents.models import Document
        return Document.query.get(entity_id)
    elif entity_type == EntityType.USER:
        from app.auth.models import User
        return User.query.get(entity_id)
    
    return None


def get_policy_for_entity(user, entity):
    """Get appropriate policy for entity"""
    if entity and hasattr(entity, 'firm_id'):
        return FirmBasedPolicy(user, entity)
    else:
        return PermissionPolicy(user, entity)


def firm_required(f):
    """Decorator to ensure user is in a firm context"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        
        if not user or not user.firm_id:
            if request.is_json:
                return jsonify({'error': 'Firm context required'}), 403
            return redirect(url_for('auth.select_firm'))
        
        kwargs['current_user'] = user
        kwargs['firm_id'] = user.firm_id
        
        return f(*args, **kwargs)
    
    return decorated_function