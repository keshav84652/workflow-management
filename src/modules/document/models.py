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


class DocumentChecklist(db.Model):
    """Document checklist created by CPAs for clients"""
    __tablename__ = 'document_checklist'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Client access token for public URL sharing
    access_token = db.Column(db.String(255), unique=True)  # Secure URL token for client access
    token_expires_at = db.Column(db.DateTime)  # Optional expiration
    client_email = db.Column(db.String(255))  # Client email for verification
    token_access_count = db.Column(db.Integer, default=0, nullable=False)  # Track access count
    token_last_accessed = db.Column(db.DateTime)  # Last access timestamp
    
    # AI Analysis fields
    ai_analysis_completed = db.Column(db.Boolean, default=False, nullable=False)
    ai_analysis_results = db.Column(db.Text)  # JSON string of AI analysis results
    ai_analysis_timestamp = db.Column(db.DateTime)
    ai_analysis_version = db.Column(db.String(50), default='1.0')  # Track AI model version
    
    # Relationships - using string references to avoid circular imports
    # client = db.relationship('Client', backref='document_checklists')
    # creator = db.relationship('User', backref='created_checklists')


class ChecklistItem(db.Model):
    """Individual items in a document checklist"""
    __tablename__ = 'checklist_item'
    
    id = db.Column(db.Integer, primary_key=True)
    checklist_id = db.Column(db.Integer, db.ForeignKey('document_checklist.id'), nullable=False)
    item_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    is_required = db.Column(db.Boolean, default=True, nullable=False)
    order_index = db.Column(db.Integer, default=0, nullable=False)
    
    # Relationships
    checklist = db.relationship('DocumentChecklist', backref='items')


class ClientDocument(db.Model):
    """Documents uploaded by clients for checklist items"""
    __tablename__ = 'client_document'
    
    id = db.Column(db.Integer, primary_key=True)
    checklist_item_id = db.Column(db.Integer, db.ForeignKey('checklist_item.id'), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)  # UUID-based filename
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # AI Analysis fields
    ai_analysis_completed = db.Column(db.Boolean, default=False, nullable=False)
    ai_document_type = db.Column(db.String(100))  # AI-detected document type
    ai_confidence_score = db.Column(db.Float)  # AI confidence (0.0-1.0)
    ai_extracted_data = db.Column(db.Text)  # JSON string of extracted data
    ai_analysis_timestamp = db.Column(db.DateTime)
    ai_analysis_error = db.Column(db.Text)  # Error message if analysis failed
    
    # Relationships
    checklist_item = db.relationship('ChecklistItem', backref='client_documents')


class Attachment(db.Model):
    """File attachments for tasks and projects"""
    __tablename__ = 'attachment'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)  # Unique filename on disk
    original_filename = db.Column(db.String(255), nullable=False)  # Original user filename
    file_path = db.Column(db.String(500), nullable=False)  # Full path to file
    file_size = db.Column(db.Integer, nullable=False)  # File size in bytes
    mime_type = db.Column(db.String(100))  # MIME type
    task_id = db.Column(db.Integer, db.ForeignKey('task.id', ondelete='CASCADE'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'))
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    firm_id = db.Column(db.Integer, db.ForeignKey('firm.id'), nullable=False)
    
    @property
    def file_size_formatted(self):
        """Return human-readable file size"""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        elif self.file_size < 1024 * 1024 * 1024:
            return f"{self.file_size / (1024 * 1024):.1f} MB"
        else:
            return f"{self.file_size / (1024 * 1024 * 1024):.1f} GB"


class DocumentTemplate(db.Model):
    """Templates for creating document checklists"""
    __tablename__ = 'document_template'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    firm_id = db.Column(db.Integer, db.ForeignKey('firm.id'), nullable=False)


class DocumentTemplateItem(db.Model):
    """Items in document templates"""
    __tablename__ = 'document_template_item'
    
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('document_template.id'), nullable=False)
    item_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    is_required = db.Column(db.Boolean, default=True, nullable=False)
    order_index = db.Column(db.Integer, default=0, nullable=False)
    
    # Relationships
    template = db.relationship('DocumentTemplate', backref='items')


class IncomeWorksheet(db.Model):
    """Income worksheet data extracted from documents"""
    __tablename__ = 'income_worksheet'
    
    id = db.Column(db.Integer, primary_key=True)
    client_document_id = db.Column(db.Integer, db.ForeignKey('client_document.id'), nullable=False)
    
    # Basic income data
    wages_salaries = db.Column(db.Numeric(15, 2))
    interest_income = db.Column(db.Numeric(15, 2))
    dividend_income = db.Column(db.Numeric(15, 2))
    business_income = db.Column(db.Numeric(15, 2))
    capital_gains = db.Column(db.Numeric(15, 2))
    other_income = db.Column(db.Numeric(15, 2))
    
    # Tax withholdings
    federal_withholding = db.Column(db.Numeric(15, 2))
    state_withholding = db.Column(db.Numeric(15, 2))
    social_security_withholding = db.Column(db.Numeric(15, 2))
    medicare_withholding = db.Column(db.Numeric(15, 2))
    
    # Metadata
    tax_year = db.Column(db.Integer)
    document_type = db.Column(db.String(50))  # W2, 1099, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # AI extraction metadata
    extraction_confidence = db.Column(db.Float)  # Overall confidence score
    extraction_method = db.Column(db.String(50))  # AI model used
    
    # Relationships
    client_document = db.relationship('ClientDocument', backref='income_worksheet')