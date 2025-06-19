# Authentication Models
# Enhanced user and role system inspired by OpenProject + current functionality

from datetime import datetime
from enum import Enum

from app.core.extensions import db
from app.core.models import BaseModel, AuditMixin, PermissionMixin


class UserRole(Enum):
    """Enhanced user roles inspired by OpenProject's role system"""
    STAFF = 'Staff'
    SENIOR = 'Senior'
    MANAGER = 'Manager'
    PARTNER = 'Partner'
    ADMIN = 'Admin'


class Firm(BaseModel):
    """Firm model - represents CPA firms"""
    __tablename__ = 'firm'
    
    name = db.Column(db.String(120), nullable=False)
    access_code = db.Column(db.String(255), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Subscription and billing info
    subscription_type = db.Column(db.String(50), default='basic')
    max_users = db.Column(db.Integer, default=10)
    
    # Settings
    settings = db.Column(db.JSON, default=dict)
    
    # Relationships
    users = db.relationship('User', backref='firm', lazy=True)
    
    def __repr__(self):
        return f'<Firm {self.name}>'
    
    @property
    def active_users_count(self):
        """Count of active users in firm"""
        return User.query.filter_by(firm_id=self.id, is_active=True).count()
    
    def can_add_user(self):
        """Check if firm can add more users"""
        return self.active_users_count < self.max_users


class User(BaseModel, AuditMixin, PermissionMixin):
    """Enhanced User model with role-based permissions"""
    __tablename__ = 'user'
    
    # Basic information
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True)  # Optional for now
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.STAFF)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Firm relationship
    firm_id = db.Column(db.Integer, db.ForeignKey('firm.id'), nullable=False)
    
    # Profile information
    title = db.Column(db.String(100))  # Job title
    department = db.Column(db.String(100))
    hire_date = db.Column(db.Date)
    
    # CPA-specific fields
    license_number = db.Column(db.String(50))
    license_state = db.Column(db.String(20))
    license_expiry = db.Column(db.Date)
    
    # Time tracking and billing
    hourly_rate = db.Column(db.Numeric(8, 2))  # Billing rate
    default_billable = db.Column(db.Boolean, default=True)
    
    # Activity tracking
    last_login = db.Column(db.DateTime)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    
    # User preferences
    preferences = db.Column(db.JSON, default=dict)
    
    def __repr__(self):
        return f'<User {self.name} ({self.role.value})>'
    
    @property
    def is_admin(self):
        """Check if user is admin"""
        return self.role in [UserRole.ADMIN, UserRole.PARTNER]
    
    @property
    def is_manager(self):
        """Check if user is manager or above"""
        return self.role in [UserRole.MANAGER, UserRole.PARTNER, UserRole.ADMIN]
    
    @property
    def can_manage_users(self):
        """Check if user can manage other users"""
        return self.role in [UserRole.ADMIN, UserRole.PARTNER]
    
    @property
    def can_manage_firm_settings(self):
        """Check if user can manage firm settings"""
        return self.role == UserRole.ADMIN
    
    def update_last_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
        db.session.commit()
    
    def check_permission(self, user, right):
        """Check permission against another user"""
        from app.core.models import Right
        
        # Users can always read their own profile
        if user.id == self.id and right == Right.READ:
            return True
        
        # Only managers and above can read other users
        if right == Right.READ:
            return user.is_manager
        
        # Only admins can modify users
        if right in [Right.WRITE, Right.ADMIN]:
            return user.role == UserRole.ADMIN
        
        return False
    
    def get_permissions_for_entity(self, entity_type):
        """Get user permissions for specific entity type"""
        permissions = []
        
        # Base permissions by role
        if self.role == UserRole.STAFF:
            permissions = ['read', 'create_own', 'edit_assigned']
        elif self.role == UserRole.SENIOR:
            permissions = ['read', 'create', 'edit', 'assign']
        elif self.role == UserRole.MANAGER:
            permissions = ['read', 'create', 'edit', 'delete', 'assign', 'manage_team']
        elif self.role in [UserRole.PARTNER, UserRole.ADMIN]:
            permissions = ['all']
        
        return permissions


class Permission(BaseModel):
    """Permission model for fine-grained access control"""
    __tablename__ = 'permission'
    
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # clients, projects, tasks, reports, admin
    
    def __repr__(self):
        return f'<Permission {self.name}>'


class RolePermission(BaseModel):
    """Many-to-many relationship between roles and permissions"""
    __tablename__ = 'role_permission'
    
    role = db.Column(db.Enum(UserRole), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id'), nullable=False)
    
    permission = db.relationship('Permission', backref='role_permissions')


class ActivityLog(BaseModel, AuditMixin):
    """Activity logging for audit trails"""
    __tablename__ = 'activity_log'
    
    action = db.Column(db.String(255), nullable=False)
    entity_type = db.Column(db.String(50))  # 'client', 'project', 'task', etc.
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.Text)
    
    # Firm context
    firm_id = db.Column(db.Integer, db.ForeignKey('firm.id'), nullable=False)
    
    def __repr__(self):
        return f'<ActivityLog {self.action} by {self.created_by_id}>'