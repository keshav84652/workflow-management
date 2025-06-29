"""
Authentication-related models for CPA WorkflowPilot
"""

from datetime import datetime
from src.shared.database.db_import import db


class ClientUser(db.Model):
    """Client portal user authentication"""
    __tablename__ = 'client_user'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    access_code = db.Column(db.String(20), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    client = db.relationship('Client', backref='client_users')
    
    def generate_access_code(self):
        """Generate a unique 8-character access code"""
        import string
        import random
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not ClientUser.query.filter_by(access_code=code).first():
                self.access_code = code
                break
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()


class DemoAccessRequest(db.Model):
    """Track demo access requests with email collection"""
    __tablename__ = 'demo_access_request'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False)
    firm_access_code = db.Column(db.String(255), nullable=False)  # The demo firm code they tried to access
    ip_address = db.Column(db.String(50))  # Track IP for security
    user_agent = db.Column(db.Text)  # Track browser/device info
    granted = db.Column(db.Boolean, default=False, nullable=False)  # Whether access was granted
    granted_at = db.Column(db.DateTime)  # When access was granted
    granted_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # Admin who granted access
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)  # Admin notes about the request
    
    # Session tracking
    session_id = db.Column(db.String(255))  # Track demo session
    last_activity = db.Column(db.DateTime)  # Last activity in demo
    
    # Relationships
    granter = db.relationship('User', backref='granted_demo_access')
    
    @property
    def is_recent_request(self):
        """Check if request was made recently (within 24 hours)"""
        if not self.created_at:
            return False
        time_diff = datetime.utcnow() - self.created_at
        return time_diff.total_seconds() < 86400  # 24 hours
    
    def grant_access(self, admin_user_id, notes=None):
        """Grant demo access to this email"""
        self.granted = True
        self.granted_at = datetime.utcnow()
        self.granted_by = admin_user_id
        if notes:
            self.notes = notes
    
    def update_activity(self, session_id=None):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
        if session_id:
            self.session_id = session_id