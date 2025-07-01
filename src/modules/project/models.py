"""
Project and task management models
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
    # Legacy ordering fields - keeping both for backwards compatibility
    order = db.Column(db.Integer, default=0)  # Legacy field - still used in database
    workflow_order = db.Column(db.Integer, default=0)  # Legacy field - still used in database
    
    @property
    def position(self):
        """Unified position property that uses the order field"""
        return self.order
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
    # DOCUMENTED TECHNICAL DEBT: Dual source of truth for status
    # Legacy 'status' field maintained for backward compatibility.
    # Migration plan exists in /src/migrations/ to consolidate to status_id only.
    status = db.Column(db.String(20), default='Not Started', nullable=False)  # Legacy field - TO BE REMOVED
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
        # Fallback to legacy status (will be removed after migration)
        return getattr(self, 'status', 'Not Started')
    
    @property
    def is_completed(self):
        """Check if task is completed using new or legacy status"""
        # Prefer new status system
        if self.status_id and self.task_status_ref:
            return self.task_status_ref.is_terminal
        
        # Fallback to legacy status (will be removed after migration)
        legacy_status = getattr(self, 'status', None)
        if legacy_status:
            return legacy_status in ['Completed', 'Done', 'Cancelled']
        
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
    
    def update_status(self, new_status_id, user_id=None):
        """
        Update task status using the new system
        This method should be used instead of directly setting status fields
        """
        from src.modules.project.models import TaskStatus
        
        # Validate the new status exists and belongs to the right firm
        new_status = TaskStatus.query.filter_by(
            id=new_status_id,
            firm_id=self.firm_id
        ).first()
        
        if not new_status:
            raise ValueError(f"Invalid status_id {new_status_id} for firm {self.firm_id}")
        
        old_status_name = self.current_status
        self.status_id = new_status_id
        
        # Update completion timestamp if moving to terminal status
        if new_status.is_terminal and not self.completed_at:
            self.completed_at = datetime.utcnow()
        elif not new_status.is_terminal and self.completed_at:
            self.completed_at = None
        
        # Update parent task progress if this is a subtask
        if self.parent_task:
            self.update_parent_progress()
        
        return {
            'old_status': old_status_name,
            'new_status': new_status.name,
            'is_completed': new_status.is_terminal
        }
    
    @property
    def migration_status(self):
        """
        Get migration status for this task
        Used during the migration process to track progress
        """
        has_legacy = hasattr(self, 'status') and getattr(self, 'status') is not None
        has_new = self.status_id is not None
        
        if has_new and not has_legacy:
            return 'migrated'
        elif has_new and has_legacy:
            return 'dual_system'
        elif not has_new and has_legacy:
            return 'legacy_only'
        else:
            return 'no_status'

class TaskComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.Text, nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='task_comments')
