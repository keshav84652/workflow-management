# Core Service Layer
# Service-oriented architecture inspired by OpenProject's service patterns

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.core.extensions import db


class ServiceResult:
    """Service result wrapper for consistent return values"""
    
    def __init__(self, success: bool = True, data: Any = None, errors: Optional[Dict] = None):
        self.success = success
        self.data = data
        self.errors = errors or {}
        
    @classmethod
    def success_result(cls, data: Any = None):
        """Create successful result"""
        return cls(success=True, data=data)
    
    @classmethod
    def error_result(cls, errors: Dict):
        """Create error result"""
        return cls(success=False, errors=errors)
    
    def is_success(self):
        return self.success
    
    def is_failure(self):
        return not self.success


class BaseService(ABC):
    """Base service class following OpenProject's service architecture"""
    
    def __init__(self, user=None):
        self.user = user
        self.model = None
    
    @abstractmethod
    def call(self, **kwargs) -> ServiceResult:
        """Main service method - to be implemented by subclasses"""
        pass
    
    def validate(self, data: Dict) -> ServiceResult:
        """Validate input data - can be overridden by subclasses"""
        return ServiceResult.success_result()
    
    def authorize(self, **kwargs) -> ServiceResult:
        """Check authorization - can be overridden by subclasses"""
        return ServiceResult.success_result()
    
    def persist(self, instance):
        """Persist changes to database"""
        try:
            db.session.add(instance)
            db.session.commit()
            return ServiceResult.success_result(instance)
        except Exception as e:
            db.session.rollback()
            return ServiceResult.error_result({'database': str(e)})


class CreateService(BaseService):
    """Generic create service following OpenProject patterns"""
    
    def __init__(self, model_class, user=None):
        super().__init__(user)
        self.model_class = model_class
    
    def call(self, **kwargs) -> ServiceResult:
        """Create new instance"""
        # Authorization check
        auth_result = self.authorize(**kwargs)
        if auth_result.is_failure():
            return auth_result
        
        # Validation
        validation_result = self.validate(kwargs)
        if validation_result.is_failure():
            return validation_result
        
        # Create instance
        instance = self.model_class(**kwargs)
        
        # Set user context if available
        if hasattr(instance, 'created_by_id') and self.user:
            instance.created_by_id = self.user.id
        
        # Persist to database
        return self.persist(instance)


class UpdateService(BaseService):
    """Generic update service following OpenProject patterns"""
    
    def __init__(self, instance, user=None):
        super().__init__(user)
        self.instance = instance
    
    def call(self, **kwargs) -> ServiceResult:
        """Update existing instance"""
        # Authorization check
        auth_result = self.authorize(instance=self.instance, **kwargs)
        if auth_result.is_failure():
            return auth_result
        
        # Validation
        validation_result = self.validate(kwargs)
        if validation_result.is_failure():
            return validation_result
        
        # Update instance
        for key, value in kwargs.items():
            if hasattr(self.instance, key):
                setattr(self.instance, key, value)
        
        # Set update context if available
        if hasattr(self.instance, 'updated_by_id') and self.user:
            self.instance.updated_by_id = self.user.id
        
        # Persist to database
        return self.persist(self.instance)


class DeleteService(BaseService):
    """Generic delete service following OpenProject patterns"""
    
    def __init__(self, instance, user=None):
        super().__init__(user)
        self.instance = instance
    
    def call(self, **kwargs) -> ServiceResult:
        """Delete existing instance"""
        # Authorization check
        auth_result = self.authorize(instance=self.instance, **kwargs)
        if auth_result.is_failure():
            return auth_result
        
        # Delete instance
        try:
            db.session.delete(self.instance)
            db.session.commit()
            return ServiceResult.success_result()
        except Exception as e:
            db.session.rollback()
            return ServiceResult.error_result({'database': str(e)})