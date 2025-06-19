"""
Miscellaneous models for various features
"""

from datetime import datetime
from core import db


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


class ClientChecklistAccess(db.Model):
    """Secure token-based access to client checklists for production"""
    __tablename__ = 'client_checklist_access'
    
    id = db.Column(db.Integer, primary_key=True)
    checklist_id = db.Column(db.Integer, db.ForeignKey('document_checklist.id'), nullable=False)
    access_token = db.Column(db.String(255), unique=True, nullable=False)  # Secure URL token
    client_email = db.Column(db.String(255), nullable=False)  # Client email for verification
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)  # Optional expiration
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # CPA who created the link
    
    # Access tracking
    access_count = db.Column(db.Integer, default=0, nullable=False)
    last_accessed = db.Column(db.DateTime)
    access_ip_addresses = db.Column(db.Text)  # JSON array of IPs that accessed
    
    # Security settings
    max_access_count = db.Column(db.Integer)  # Limit number of accesses
    ip_whitelist = db.Column(db.Text)  # JSON array of allowed IPs
    requires_email_verification = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    checklist = db.relationship('DocumentChecklist', backref='access_tokens')
    creator = db.relationship('User', backref='created_checklist_access')
    
    def generate_token(self):
        """Generate a secure access token"""
        import secrets
        import string
        # Generate a 32-character URL-safe token
        alphabet = string.ascii_letters + string.digits + '-_'
        self.access_token = ''.join(secrets.choice(alphabet) for _ in range(32))
        return self.access_token
    
    @property
    def is_expired(self):
        """Check if access token has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_access_limited(self):
        """Check if access is limited by count"""
        if not self.max_access_count:
            return False
        return self.access_count >= self.max_access_count
    
    @property
    def public_url(self):
        """Generate the public URL for this checklist"""
        # This will be used in production to generate URLs like:
        # https://your-app.replit.app/checklist/ABC123XYZ789...
        return f"/checklist/{self.access_token}"