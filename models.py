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
    auto_create_work_type = db.Column(db.Boolean, default=True)  # Whether to auto-create work type from template
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
        for i, template_task in enumerate(sorted(self.template_tasks, key=lambda t: t.workflow_order or t.order)):
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
    order = db.Column(db.Integer, default=0)
    estimated_hours = db.Column(db.Float)
    default_priority = db.Column(db.String(10), default='Medium')  # High, Medium, Low
    days_from_start = db.Column(db.Integer)  # Days from project start for auto due date
    default_assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recurrence_rule = db.Column(db.String(100))
    template_id = db.Column(db.Integer, db.ForeignKey('template.id'), nullable=False)
    default_status_id = db.Column(db.Integer, db.ForeignKey('task_status.id'), nullable=True)  # Maps to specific workflow status
    workflow_order = db.Column(db.Integer, default=0)  # Order in the kanban workflow (overrides 'order' for workflow)
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
    
    @property
    def contacts(self):
        """Get all contacts associated with this client"""
        return db.session.query(Contact).join(ClientContact).filter(
            ClientContact.client_id == self.id
        ).all()
    
    @property
    def primary_contact(self):
        """Get the primary contact for this client"""
        return db.session.query(Contact).join(ClientContact).filter(
            ClientContact.client_id == self.id,
            ClientContact.is_primary == True
        ).first()

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
    task_dependency_mode = db.Column(db.Boolean, default=False)  # If True, completing a task auto-completes all previous tasks
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

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    estimated_hours = db.Column(db.Float)
    actual_hours = db.Column(db.Float, default=0)
    hourly_rate = db.Column(db.Float)  # Billing rate for this task
    is_billable = db.Column(db.Boolean, default=True)  # Whether this task is billable
    timer_start = db.Column(db.DateTime)  # When timer was started
    timer_running = db.Column(db.Boolean, default=False)  # Whether timer is currently running
    status = db.Column(db.String(20), default='Not Started', nullable=False)  # Legacy field for migration
    status_id = db.Column(db.Integer, db.ForeignKey('task_status.id'), nullable=True)  # New status system
    priority = db.Column(db.String(10), default='Medium', nullable=False)  # High, Medium, Low
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firm.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    template_task_origin_id = db.Column(db.Integer, db.ForeignKey('template_task.id'))
    dependencies = db.Column(db.String(500))  # Comma-separated list of task IDs this depends on
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    parent_task_id = db.Column(db.Integer, db.ForeignKey('task.id', ondelete='CASCADE'), nullable=True)  # Parent task for subtasks
    subtask_order = db.Column(db.Integer, default=0)  # Order of subtasks within parent
    
    # Recurring task fields - integrated directly into Task model
    is_recurring = db.Column(db.Boolean, default=False, nullable=False)  # Whether this task repeats
    recurrence_rule = db.Column(db.String(100))  # e.g., "daily", "weekly", "monthly", "yearly"
    recurrence_interval = db.Column(db.Integer, default=1)  # Every X days/weeks/months/years
    next_due_date = db.Column(db.Date)  # When next instance should be created
    last_completed = db.Column(db.Date)  # Last time this recurring task was completed
    master_task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)  # Reference to master recurring task
    
    activity_logs = db.relationship('ActivityLog', backref='task', lazy=True)
    comments = db.relationship('TaskComment', backref='task', lazy=True, cascade="all, delete-orphan")
    
    # Subtask relationships
    subtasks = db.relationship('Task', 
                              foreign_keys=[parent_task_id],
                              backref=db.backref('parent_task', remote_side='Task.id'), 
                              lazy=True, cascade="all, delete-orphan", 
                              order_by='Task.subtask_order, Task.created_at')
    
    @property
    def current_status(self):
        """Get current status name, preferring new status system over legacy"""
        if self.status_id and self.task_status_ref:
            return self.task_status_ref.name
        return self.status
    
    @property
    def is_completed(self):
        """Check if task is completed using new or legacy status"""
        # Check legacy status first for backward compatibility
        if self.status == 'Completed':
            return True
        
        # Then check new status system
        if self.status_id and self.task_status_ref:
            return self.task_status_ref.is_terminal
        
        return False
    
    @property
    def is_overdue(self):
        # Task is not overdue if:
        # 1. No due date
        # 2. Task itself is completed
        # 3. Project is completed (if task belongs to a project)
        if not self.due_date or self.is_completed:
            return False
        
        # If task belongs to a project and project is completed, task is not overdue
        if self.project and self.project.status == 'Completed':
            return False
        
        return self.due_date < date.today()
    
    @property
    def is_due_soon(self):
        if not self.due_date or self.is_completed:
            return False
        
        # If task belongs to a project and project is completed, task is not due soon
        if self.project and self.project.status == 'Completed':
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
    
    @property
    def is_parent_task(self):
        """Check if this task has subtasks"""
        return len(self.subtasks) > 0
    
    @property
    def is_subtask(self):
        """Check if this task is a subtask"""
        return self.parent_task_id is not None
    
    @property
    def subtask_progress(self):
        """Calculate completion percentage of subtasks"""
        if not self.subtasks:
            return 0
        completed_subtasks = len([st for st in self.subtasks if st.is_completed])
        return round((completed_subtasks / len(self.subtasks)) * 100)
    
    @property
    def root_task(self):
        """Get the root parent task (for nested subtasks)"""
        current = self
        while current.parent_task:
            current = current.parent_task
        return current
    
    @property
    def task_hierarchy_level(self):
        """Get the nesting level of this task (0 = root, 1 = subtask, 2 = sub-subtask, etc.)"""
        level = 0
        current = self
        while current.parent_task:
            level += 1
            current = current.parent_task
        return level
    
    def get_all_subtasks_recursive(self):
        """Get all subtasks recursively (including sub-subtasks)"""
        all_subtasks = []
        for subtask in self.subtasks:
            all_subtasks.append(subtask)
            all_subtasks.extend(subtask.get_all_subtasks_recursive())
        return all_subtasks
    
    def update_parent_progress(self):
        """Update parent task progress when subtask status changes"""
        if self.parent_task:
            # Check if all subtasks are completed
            all_completed = all(st.is_completed for st in self.parent_task.subtasks)
            if all_completed and not self.parent_task.is_completed:
                # Auto-complete parent task if all subtasks are done
                if self.parent_task.status_id and self.parent_task.task_status_ref:
                    # Find a terminal status for the parent's work type
                    terminal_status = TaskStatus.query.filter_by(
                        work_type_id=self.parent_task.task_status_ref.work_type_id,
                        is_terminal=True
                    ).first()
                    if terminal_status:
                        self.parent_task.status_id = terminal_status.id
                else:
                    self.parent_task.status = 'Completed'
                self.parent_task.completed_at = datetime.utcnow()
    
    def calculate_next_due_date(self, from_date=None):
        """Calculate next due date based on recurrence rule - fixed intervals from original due date"""
        if not self.is_recurring or not self.recurrence_rule:
            return None
        
        if from_date is None:
            # Always use the original due date as the base, not completion date
            from_date = self.due_date or date.today()
        
        from datetime import timedelta
        
        if self.recurrence_rule == 'daily':
            return from_date + timedelta(days=self.recurrence_interval or 1)
        elif self.recurrence_rule == 'weekly':
            return from_date + timedelta(weeks=self.recurrence_interval or 1)
        elif self.recurrence_rule == 'monthly':
            # Add months (approximate with 30 days)
            return from_date + timedelta(days=30 * (self.recurrence_interval or 1))
        elif self.recurrence_rule == 'yearly':
            # Add years (approximate with 365 days)
            return from_date + timedelta(days=365 * (self.recurrence_interval or 1))
        
        return None
    
    def create_next_instance(self):
        """Create the next instance of this recurring task"""
        if not self.is_recurring:
            return None
        
        next_due = self.calculate_next_due_date()
        if not next_due:
            return None
        
        # Create new task instance
        new_task = Task(
            title=self.title,
            description=self.description,
            due_date=next_due,
            estimated_hours=self.estimated_hours,
            priority=self.priority,
            project_id=self.project_id,
            firm_id=self.firm_id,
            assignee_id=self.assignee_id,
            master_task_id=self.master_task_id or self.id,  # Reference to master
            is_recurring=False,  # Instances are not recurring themselves
            status_id=self.status_id
        )
        
        return new_task
    
    @property
    def is_recurring_master(self):
        """Check if this is a master recurring task"""
        return self.is_recurring and self.master_task_id is None
    
    @property
    def is_recurring_instance(self):
        """Check if this is an instance of a recurring task"""
        return self.master_task_id is not None
    
    def start_timer(self):
        """Start the timer for this task"""
        if not self.timer_running:
            self.timer_start = datetime.utcnow()
            self.timer_running = True
            return True
        return False
    
    def stop_timer(self):
        """Stop the timer and add elapsed time to actual_hours"""
        if self.timer_running and self.timer_start:
            elapsed = datetime.utcnow() - self.timer_start
            elapsed_hours = elapsed.total_seconds() / 3600
            self.actual_hours = (self.actual_hours or 0) + elapsed_hours
            self.timer_running = False
            self.timer_start = None
            return elapsed_hours
        return 0
    
    @property
    def current_timer_duration(self):
        """Get current timer duration in hours"""
        if self.timer_running and self.timer_start:
            elapsed = datetime.utcnow() - self.timer_start
            return elapsed.total_seconds() / 3600
        return 0
    
    @property
    def billable_amount(self):
        """Calculate billable amount for this task"""
        if not self.is_billable or not self.hourly_rate:
            return 0
        return (self.actual_hours or 0) * self.hourly_rate
    
    @property
    def time_variance(self):
        """Calculate variance between estimated and actual hours"""
        if not self.estimated_hours or not self.actual_hours:
            return None
        return self.actual_hours - self.estimated_hours
    
    @property
    def time_variance_percentage(self):
        """Calculate variance percentage"""
        if not self.estimated_hours or not self.actual_hours:
            return None
        return ((self.actual_hours - self.estimated_hours) / self.estimated_hours) * 100

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


# ====================================
# CLIENT PORTAL MODELS
# ====================================

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


