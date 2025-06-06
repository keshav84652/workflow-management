from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

db = SQLAlchemy()

class Firm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    access_code = db.Column(db.String(255), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    users = db.relationship('User', backref='firm', lazy=True)
    templates = db.relationship('Template', backref='firm', lazy=True)
    projects = db.relationship('Project', backref='firm', lazy=True)
    clients = db.relationship('Client', backref='firm', lazy=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Member')
    firm_id = db.Column(db.Integer, db.ForeignKey('firm.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    tasks = db.relationship('Task', backref='assignee', lazy=True)
    activity_logs = db.relationship('ActivityLog', backref='user', lazy=True)

class Template(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    firm_id = db.Column(db.Integer, db.ForeignKey('firm.id'), nullable=False)
    work_type_id = db.Column(db.Integer, db.ForeignKey('work_type.id'), nullable=True)  # Link to work type
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    template_tasks = db.relationship('TemplateTask', backref='template', lazy=True, cascade="all, delete-orphan")
    projects = db.relationship('Project', backref='template_origin', lazy=True)

class TemplateTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    order = db.Column(db.Integer, default=0)
    estimated_hours = db.Column(db.Float)
    default_priority = db.Column(db.String(10), default='Medium')  # High, Medium, Low
    days_from_start = db.Column(db.Integer)  # Days from project start for auto due date
    default_assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recurrence_rule = db.Column(db.String(100))
    template_id = db.Column(db.Integer, db.ForeignKey('template.id'), nullable=False)
    default_status_id = db.Column(db.Integer, db.ForeignKey('task_status.id'), nullable=True)  # Maps to specific workflow status
    dependencies = db.Column(db.String(500))  # Comma-separated list of template task IDs this depends on
    
    default_assignee = db.relationship('User', backref='default_template_tasks')
    default_status = db.relationship('TaskStatus', backref='template_tasks')
    spawned_tasks = db.relationship('Task', backref='template_task_origin', lazy=True)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    contact_person = db.Column(db.String(100))
    entity_type = db.Column(db.String(50))  # Individual, Corp, LLC, Partnership, etc.
    tax_id = db.Column(db.String(20))  # EIN or SSN
    notes = db.Column(db.Text)
    firm_id = db.Column(db.Integer, db.ForeignKey('firm.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    projects = db.relationship('Project', backref='client', lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)  # Project name (e.g., "2024 Tax Return", "Q1 Bookkeeping")
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    work_type_id = db.Column(db.Integer, db.ForeignKey('work_type.id'), nullable=True)  # Link to work type
    status = db.Column(db.String(20), default='Active', nullable=False)
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date)
    completion_date = db.Column(db.Date)
    firm_id = db.Column(db.Integer, db.ForeignKey('firm.id'), nullable=False)
    template_origin_id = db.Column(db.Integer, db.ForeignKey('template.id'))
    priority = db.Column(db.String(10), default='Medium', nullable=False)  # High, Medium, Low
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    tasks = db.relationship('Task', backref='project', lazy=True, cascade="all, delete-orphan")
    activity_logs = db.relationship('ActivityLog', backref='project', lazy=True)
    
    @property
    def progress_percentage(self):
        if not self.tasks:
            return 0
        completed_tasks = len([t for t in self.tasks if t.status == 'Completed'])
        return round((completed_tasks / len(self.tasks)) * 100)
    
    @property
    def client_name(self):
        return self.client.name if self.client else 'Unknown Client'
    
    @property
    def is_overdue(self):
        return self.due_date and self.due_date < date.today() and self.status != 'Completed'

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    estimated_hours = db.Column(db.Float)
    actual_hours = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='Not Started', nullable=False)  # Legacy field for migration
    status_id = db.Column(db.Integer, db.ForeignKey('task_status.id'), nullable=True)  # New status system
    priority = db.Column(db.String(10), default='Medium', nullable=False)  # High, Medium, Low
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firm.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    template_task_origin_id = db.Column(db.Integer, db.ForeignKey('template_task.id'))
    recurring_task_origin_id = db.Column(db.Integer, db.ForeignKey('recurring_task.id'))  # For standalone recurring tasks
    dependencies = db.Column(db.String(500))  # Comma-separated list of task IDs this depends on
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    activity_logs = db.relationship('ActivityLog', backref='task', lazy=True)
    comments = db.relationship('TaskComment', backref='task', lazy=True, cascade="all, delete-orphan")
    
    @property
    def current_status(self):
        """Get current status name, preferring new status system over legacy"""
        if self.status_id and self.task_status_ref:
            return self.task_status_ref.name
        return self.status
    
    @property
    def is_completed(self):
        """Check if task is completed using new or legacy status"""
        if self.status_id and self.task_status_ref:
            return self.task_status_ref.is_terminal
        return self.status == 'Completed'
    
    @property
    def is_overdue(self):
        return self.due_date and self.due_date < date.today() and not self.is_completed
    
    @property
    def is_due_soon(self):
        if not self.due_date or self.is_completed:
            return False
        days_until_due = (self.due_date - date.today()).days
        return 0 <= days_until_due <= 3
    
    @property
    def priority_color(self):
        return {'High': 'danger', 'Medium': 'warning', 'Low': 'success'}.get(self.priority, 'secondary')
    
    @property
    def status_color(self):
        """Get status color from new system or default colors"""
        if self.status_id and self.task_status_ref:
            return self.task_status_ref.color
        # Default colors for legacy statuses
        colors = {
            'Not Started': '#6b7280',
            'In Progress': '#3b82f6', 
            'Needs Review': '#f59e0b',
            'Completed': '#10b981'
        }
        return colors.get(self.status, '#6b7280')
    
    @property
    def dependency_list(self):
        """Get list of task IDs this task depends on"""
        if not self.dependencies:
            return []
        return [int(id.strip()) for id in self.dependencies.split(',') if id.strip()]
    
    @property
    def is_blocked(self):
        """Check if task is blocked by incomplete dependencies"""
        if not self.dependency_list:
            return False
        from sqlalchemy import and_
        blocked_dependencies = Task.query.filter(
            and_(
                Task.id.in_(self.dependency_list),
                Task.firm_id == self.firm_id
            )
        ).all()
        return any(not dep.is_completed for dep in blocked_dependencies)
    
    @property
    def blocking_tasks(self):
        """Get tasks that are blocked by this task"""
        if self.is_completed:
            return []
        return Task.query.filter(
            Task.dependencies.like(f'%{self.id}%'),
            Task.firm_id == self.firm_id
        ).all()

class TaskComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.Text, nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='task_comments')

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'))
    details = db.Column(db.Text)

class WorkType(db.Model):
    """Work types for CPA services (Tax, Bookkeeping, Payroll, Advisory)"""
    __tablename__ = 'work_type'
    
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firm.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    color = db.Column(db.String(7), nullable=False, default='#3b82f6')  # Default blue
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    position = db.Column(db.Integer, default=0)  # Order for display
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    firm = db.relationship('Firm', backref='work_types')
    task_statuses = db.relationship('TaskStatus', backref='work_type', lazy=True, cascade="all, delete-orphan")
    templates = db.relationship('Template', backref='work_type', lazy=True)
    projects = db.relationship('Project', backref='work_type', lazy=True)

class TaskStatus(db.Model):
    """Custom task statuses per work type"""
    __tablename__ = 'task_status'
    
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firm.id'), nullable=False)
    work_type_id = db.Column(db.Integer, db.ForeignKey('work_type.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(7), nullable=False, default='#6b7280')  # Default gray
    position = db.Column(db.Integer, default=0, nullable=False)
    is_terminal = db.Column(db.Boolean, default=False, nullable=False)  # Marks completion
    is_default = db.Column(db.Boolean, default=False, nullable=False)   # Default for new tasks
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    firm = db.relationship('Firm', backref='task_statuses')
    tasks = db.relationship('Task', backref='task_status_ref', lazy=True)

class RecurringTask(db.Model):
    """Standalone recurring tasks for regular CPA workflows"""
    __tablename__ = 'recurring_task'
    
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firm.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    recurrence_rule = db.Column(db.String(100), nullable=False)  # e.g., "monthly:15", "quarterly:last_biz_day"
    priority = db.Column(db.String(10), default='Medium', nullable=False)
    estimated_hours = db.Column(db.Float)
    default_assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=True)  # Optional client association
    status_id = db.Column(db.Integer, db.ForeignKey('task_status.id'), nullable=True)  # Default status for generated tasks
    work_type_id = db.Column(db.Integer, db.ForeignKey('work_type.id'), nullable=True)  # Associated work type
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    next_due_date = db.Column(db.Date, nullable=False)  # When next task should be created
    last_generated = db.Column(db.Date)  # Last time a task was generated
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    firm = db.relationship('Firm', backref='recurring_tasks')
    default_assignee = db.relationship('User', backref='assigned_recurring_tasks')
    client = db.relationship('Client', backref='recurring_tasks')
    default_status = db.relationship('TaskStatus', backref='recurring_tasks')
    work_type = db.relationship('WorkType', backref='recurring_tasks')
    generated_tasks = db.relationship('Task', backref='recurring_task_origin', lazy=True)

class Contact(db.Model):
    """Individual contacts that can be associated with multiple clients"""
    __tablename__ = 'contact'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    title = db.Column(db.String(100))  # Job title/role
    company = db.Column(db.String(200))  # Company name
    address = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships (many-to-many with clients)
    client_contacts = db.relationship('ClientContact', backref='contact', lazy=True)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class ClientContact(db.Model):
    """Many-to-many relationship between clients and contacts"""
    __tablename__ = 'client_contact'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=False)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)
    relationship_type = db.Column(db.String(50))  # 'Owner', 'Accountant', 'Bookkeeper', etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    client = db.relationship('Client', backref='client_contacts')
    
    # Ensure unique client-contact pairs
    __table_args__ = (db.UniqueConstraint('client_id', 'contact_id', name='unique_client_contact'),)