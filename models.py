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
    default_assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recurrence_rule = db.Column(db.String(100))
    template_id = db.Column(db.Integer, db.ForeignKey('template.id'), nullable=False)
    
    default_assignee = db.relationship('User', backref='default_template_tasks')
    spawned_tasks = db.relationship('Task', backref='template_task_origin', lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), default='Active', nullable=False)
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    firm_id = db.Column(db.Integer, db.ForeignKey('firm.id'), nullable=False)
    template_origin_id = db.Column(db.Integer, db.ForeignKey('template.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    tasks = db.relationship('Task', backref='project', lazy=True, cascade="all, delete-orphan")
    activity_logs = db.relationship('ActivityLog', backref='project', lazy=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='Not Started', nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    template_task_origin_id = db.Column(db.Integer, db.ForeignKey('template_task.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    activity_logs = db.relationship('ActivityLog', backref='task', lazy=True)
    
    @property
    def is_overdue(self):
        return self.due_date and self.due_date < date.today() and self.status != 'Completed'

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'))
    details = db.Column(db.Text)