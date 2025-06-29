"""
Document-related models for CPA WorkflowPilot
"""

from datetime import datetime
from src.shared.database.db_import import db


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