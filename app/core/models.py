# Core Models and Mixins
# Base model patterns inspired by OpenProject's domain modeling

from datetime import datetime
from enum import Enum

from app.core.extensions import db


class BaseModel(db.Model):
    """Base model with common fields and functionality"""
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convert model to dictionary for API serialization"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
    def save(self):
        """Save instance to database"""
        db.session.add(self)
        db.session.commit()
        return self
    
    def delete(self):
        """Delete instance from database"""
        db.session.delete(self)
        db.session.commit()


class AuditMixin:
    """Audit trail mixin for tracking changes"""
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    @property
    def created_by(self):
        from app.auth.models import User
        return User.query.get(self.created_by_id) if self.created_by_id else None
    
    @property
    def updated_by(self):
        from app.auth.models import User
        return User.query.get(self.updated_by_id) if self.updated_by_id else None


class Right(Enum):
    """Permission rights inspired by Vikunja's rights system"""
    READ = 1
    WRITE = 2
    ADMIN = 3


class PermissionMixin:
    """Permission checking mixin inspired by Vikunja's web.Rights"""
    
    def can_read(self, user):
        """Check if user can read this entity"""
        return self.check_permission(user, Right.READ)
    
    def can_write(self, user):
        """Check if user can write to this entity"""
        return self.check_permission(user, Right.WRITE)
    
    def can_admin(self, user):
        """Check if user can administer this entity"""
        return self.check_permission(user, Right.ADMIN)
    
    def check_permission(self, user, right):
        """Check specific permission - to be implemented by subclasses"""
        # Default implementation - override in specific models
        return user and user.is_active


class FirmMixin:
    """Multi-tenancy mixin for firm-based isolation"""
    firm_id = db.Column(db.Integer, db.ForeignKey('firm.id'), nullable=False)
    
    @property
    def firm(self):
        from app.auth.models import Firm
        return Firm.query.get(self.firm_id)
    
    @classmethod
    def for_firm(cls, firm_id):
        """Filter query by firm"""
        return cls.query.filter_by(firm_id=firm_id)