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
    
    default_assignee = db.relationship('User', backref='default_template_tasks')
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
    status = db.Column(db.String(20), default='Not Started', nullable=False)
    priority = db.Column(db.String(10), default='Medium', nullable=False)  # High, Medium, Low
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firm.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    template_task_origin_id = db.Column(db.Integer, db.ForeignKey('template_task.id'))
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    activity_logs = db.relationship('ActivityLog', backref='task', lazy=True)
    comments = db.relationship('TaskComment', backref='task', lazy=True, cascade="all, delete-orphan")
    
    @property
    def is_overdue(self):
        return self.due_date and self.due_date < date.today() and self.status != 'Completed'
    
    @property
    def is_due_soon(self):
        if not self.due_date or self.status == 'Completed':
            return False
        days_until_due = (self.due_date - date.today()).days
        return 0 <= days_until_due <= 3
    
    @property
    def priority_color(self):
        return {'High': 'danger', 'Medium': 'warning', 'Low': 'success'}.get(self.priority, 'secondary')

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