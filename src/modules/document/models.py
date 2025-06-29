"""
Document and checklist management models
"""

from datetime import datetime
from core.db_import import db


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
    
    # Relationships
    task = db.relationship('Task', backref='attachments')
    project = db.relationship('Project', backref='attachments')
    uploader = db.relationship('User', backref='uploaded_attachments')
    firm = db.relationship('Firm', backref='attachments')
    
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
    
    @property
    def is_image(self):
        """Check if attachment is an image"""
        if not self.mime_type:
            return False
        return self.mime_type.startswith('image/')
    
    @property
    def is_document(self):
        """Check if attachment is a document"""
        if not self.mime_type:
            return False
        document_types = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                         'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         'text/plain', 'text/csv']
        return self.mime_type in document_types


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
    
    # Relationships
    client = db.relationship('Client', backref='document_checklists')
    creator = db.relationship('User', backref='created_checklists')
    
    @property
    def progress_percentage(self):
        """Calculate progress percentage of checklist"""
        if not self.items:
            return 0
        completed_items = len([item for item in self.items if item.status != 'pending'])
        return round((completed_items / len(self.items)) * 100)
    
    @property
    def completion_percentage(self):
        """Alias for progress_percentage"""
        return self.progress_percentage
    
    @property
    def pending_items_count(self):
        """Count of pending items"""
        return len([item for item in self.items if item.status == 'pending'])
    
    @property
    def completed_items_count(self):
        """Count of completed items (any status except pending)"""
        return len([item for item in self.items if item.status != 'pending'])
    
    @property
    def uploaded_items_count(self):
        """Count of uploaded items"""
        return len([item for item in self.items if item.status == 'uploaded'])
    
    def needs_ai_analysis(self):
        """Check if checklist needs AI analysis"""
        if self.ai_analysis_completed:
            return False
        # Check if any documents have been uploaded since last analysis
        for item in self.items:
            if item.client_documents and any(not doc.ai_analysis_completed for doc in item.client_documents):
                return True
        return False
    
    def get_ai_analysis_summary(self):
        """Get summary of AI analysis results for this checklist"""
        if not self.ai_analysis_completed or not self.ai_analysis_results:
            return None
        try:
            import json
            return json.loads(self.ai_analysis_results)
        except (json.JSONDecodeError, AttributeError):
            return None
    
    def generate_access_token(self):
        """Generate a secure access token for client access"""
        import secrets
        import string
        # Generate a 32-character URL-safe token
        alphabet = string.ascii_letters + string.digits + '-_'
        self.access_token = ''.join(secrets.choice(alphabet) for _ in range(32))
        return self.access_token
    
    @property
    def public_url(self):
        """Generate the public URL for this checklist"""
        if not self.access_token:
            return None
        return f"/checklist/{self.access_token}"
    
    @property
    def is_token_expired(self):
        """Check if access token has expired"""
        if not self.token_expires_at:
            return False
        return datetime.utcnow() > self.token_expires_at
    
    def record_token_access(self):
        """Record an access to this checklist via token"""
        self.token_access_count += 1
        self.token_last_accessed = datetime.utcnow()
    
    def revoke_token(self):
        """Revoke the access token"""
        self.access_token = None
        self.token_expires_at = None
    
    def extend_token_expiration(self, days=30):
        """Extend token expiration by specified days"""
        from datetime import timedelta
        if self.token_expires_at:
            self.token_expires_at += timedelta(days=days)
        else:
            self.token_expires_at = datetime.utcnow() + timedelta(days=days)


class ChecklistItem(db.Model):
    """Individual items in a document checklist"""
    __tablename__ = 'checklist_item'
    
    id = db.Column(db.Integer, primary_key=True)
    checklist_id = db.Column(db.Integer, db.ForeignKey('document_checklist.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    is_required = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, uploaded, already_provided, not_applicable
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    checklist = db.relationship('DocumentChecklist', backref='items')
    
    def update_status(self, new_status):
        """Update item status with timestamp"""
        self.status = new_status
        self.updated_at = datetime.utcnow()
    
    @property
    def status_display(self):
        """Human-readable status"""
        status_map = {
            'pending': 'Pending Upload',
            'uploaded': 'Uploaded',
            'already_provided': 'Already Provided',
            'not_applicable': 'Doesn\'t Apply'
        }
        return status_map.get(self.status, 'Unknown')
    
    @property
    def status_icon(self):
        """Bootstrap icon for status"""
        icon_map = {
            'pending': 'bi-clock text-orange-500',
            'uploaded': 'bi-check-circle text-green-500',
            'already_provided': 'bi-check-square text-blue-500',
            'not_applicable': 'bi-x-circle text-gray-500'
        }
        return icon_map.get(self.status, 'bi-question-circle')


class ClientDocument(db.Model):
    """Documents uploaded by clients"""
    __tablename__ = 'client_document'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    checklist_item_id = db.Column(db.Integer, db.ForeignKey('checklist_item.id'), nullable=True)
    filename = db.Column(db.String(255), nullable=False)  # Unique filename on disk
    original_filename = db.Column(db.String(255), nullable=False)  # Original user filename
    file_path = db.Column(db.String(500), nullable=False)  # Full path to file
    file_size = db.Column(db.Integer, nullable=False)  # File size in bytes
    mime_type = db.Column(db.String(100))  # MIME type
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by_client = db.Column(db.Boolean, default=True, nullable=False)
    
    # AI Analysis fields
    ai_analysis_completed = db.Column(db.Boolean, default=False, nullable=False)
    ai_analysis_results = db.Column(db.Text)  # JSON string of AI analysis results
    ai_analysis_timestamp = db.Column(db.DateTime)
    ai_document_type = db.Column(db.String(100))  # Detected document type (W-2, 1099, etc.)
    ai_confidence_score = db.Column(db.Float)  # AI confidence level (0.0 to 1.0)
    
    # Relationships
    client = db.relationship('Client', backref='uploaded_documents')
    checklist_item = db.relationship('ChecklistItem', backref='client_documents')
    
    @property
    def file_size_formatted(self):
        """Human-readable file size"""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"
    
    @property
    def is_image(self):
        """Check if document is an image"""
        if not self.mime_type:
            return False
        return self.mime_type.startswith('image/')
    
    @property
    def is_pdf(self):
        """Check if document is a PDF"""
        return self.mime_type == 'application/pdf'


class DocumentTemplate(db.Model):
    """Reusable document checklist templates"""
    __tablename__ = 'document_template'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    template_type = db.Column(db.String(50), nullable=False)  # 'individual_tax', 'business_tax', 'audit', etc.
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    creator = db.relationship('User', backref='created_templates')


class DocumentTemplateItem(db.Model):
    """Items in document checklist templates"""
    __tablename__ = 'document_template_item'
    
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('document_template.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    is_required = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    
    # Relationships
    template = db.relationship('DocumentTemplate', backref='template_items')


class IncomeWorksheet(db.Model):
    """Saved income worksheets generated from checklist documents"""
    __tablename__ = 'income_worksheet'
    
    id = db.Column(db.Integer, primary_key=True)
    checklist_id = db.Column(db.Integer, db.ForeignKey('document_checklist.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    csv_content = db.Column(db.Text, nullable=False)
    document_count = db.Column(db.Integer, nullable=False, default=0)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    generated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Validation and metadata
    validation_results = db.Column(db.Text)  # JSON string of validation data
    ai_analysis_version = db.Column(db.String(50), default='1.0')
    
    # Relationships
    checklist = db.relationship('DocumentChecklist', backref='income_worksheets')
    generator = db.relationship('User', backref='generated_worksheets')
    
    @property
    def file_size_formatted(self):
        """Human-readable file size"""
        size = len(self.csv_content.encode('utf-8'))
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
    
    @property
    def is_recent(self):
        """Check if worksheet was generated recently (within 1 hour)"""
        if not self.generated_at:
            return False
        time_diff = datetime.utcnow() - self.generated_at
        return time_diff.total_seconds() < 3600  # 1 hour
    
    def get_validation_data(self):
        """Get validation results as dictionary"""
        if not self.validation_results:
            return {}
        try:
            import json
            return json.loads(self.validation_results)
        except:
            return {}