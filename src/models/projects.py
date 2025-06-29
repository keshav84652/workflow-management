"""
Project and template management models
"""

from datetime import datetime, date
from src.shared.database.db_import import db


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


class Template(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    firm_id = db.Column(db.Integer, db.ForeignKey('firm.id'), nullable=False)
    work_type_id = db.Column(db.Integer, db.ForeignKey('work_type.id'), nullable=True)  # Link to work type
    auto_create_work_type = db.Column(db.Boolean, default=True)  # Whether to auto-create work type from template
    task_dependency_mode = db.Column(db.Boolean, default=True)  # If True, projects from this template will be sequential
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    template_tasks = db.relationship('TemplateTask', backref='template', lazy=True, cascade="all, delete-orphan")
    projects = db.relationship('Project', backref='template_origin', lazy=True)
    
    def create_work_type_from_template(self):
        """Create a work type and statuses from template tasks"""
        if not self.auto_create_work_type or self.work_type_id:
            return self.work_type_id
        
        # Create work type based on template name
        work_type = WorkType(
            firm_id=self.firm_id,
            name=self.name,
            description=f"Workflow for {self.name}",
            color='#3b82f6'  # Default blue
        )
        db.session.add(work_type)
        db.session.flush()  # Get the ID
        
        # Create statuses from template tasks
        for i, template_task in enumerate(sorted(self.template_tasks, key=lambda t: t.position)):
            status = TaskStatus(
                firm_id=self.firm_id,
                work_type_id=work_type.id,
                name=template_task.title,
                color='#6b7280' if i == 0 else '#3b82f6' if i < len(self.template_tasks) - 1 else '#10b981',
                position=i + 1,
                is_default=(i == 0),  # First task is default
                is_terminal=(i == len(self.template_tasks) - 1)  # Last task is terminal
            )
            db.session.add(status)
            
            # Link template task to its corresponding status
            template_task.default_status_id = status.id
        
        # Link template to work type
        self.work_type_id = work_type.id
        db.session.commit()
        
        return work_type.id


class TemplateTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    # TODO: ARCHITECTURAL IMPROVEMENT - Consolidated ordering field
    # Previously had both 'order' and 'workflow_order' fields which was confusing.
    # Now using single 'position' field for all ordering needs.
    position = db.Column(db.Integer, default=0)  # Position/order in template (replaces both order and workflow_order)
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
    current_status_id = db.Column(db.Integer, db.ForeignKey('task_status.id'), nullable=True)  # Current workflow status
    priority = db.Column(db.String(10), default='Medium', nullable=False)  # High, Medium, Low
    task_dependency_mode = db.Column(db.Boolean, default=True)  # If True, completing a task auto-completes all previous tasks
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    tasks = db.relationship('Task', backref='project', lazy=True, cascade="all, delete-orphan")
    activity_logs = db.relationship('ActivityLog', backref='project', lazy=True)
    current_status = db.relationship('TaskStatus', backref='projects_in_status')
    
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
    
    @property
    def current_workflow_status_name(self):
        """Get the current workflow status name"""
        if self.current_status:
            return self.current_status.name
        elif self.work_type_id:
            # Get default status for work type
            default_status = TaskStatus.query.filter_by(
                work_type_id=self.work_type_id,
                is_default=True
            ).first()
            return default_status.name if default_status else 'Not Started'
        return 'Not Started'
    
    @property
    def workflow_statuses(self):
        """Get all available workflow statuses for this project"""
        if self.work_type_id:
            return TaskStatus.query.filter_by(
                work_type_id=self.work_type_id
            ).order_by(TaskStatus.position.asc()).all()
        return []
    
    def advance_workflow(self):
        """Advance project to the next workflow status"""
        if not self.work_type_id:
            return False
        
        current_position = 0
        if self.current_status:
            current_position = self.current_status.position
        
        # Find next status
        next_status = TaskStatus.query.filter_by(
            work_type_id=self.work_type_id
        ).filter(TaskStatus.position > current_position).order_by(TaskStatus.position.asc()).first()
        
        if next_status:
            self.current_status_id = next_status.id
            return True
        
        return False
    
    def move_to_status(self, status_id):
        """Move project to a specific workflow status"""
        status = TaskStatus.query.filter_by(
            id=status_id,
            work_type_id=self.work_type_id
        ).first()
        
        if status:
            self.current_status_id = status_id
            return True
        
        return False
    
    @property
    def priority_color(self):
        """Get Bootstrap color class for priority"""
        return {'High': 'danger', 'Medium': 'warning', 'Low': 'success'}.get(self.priority, 'secondary')