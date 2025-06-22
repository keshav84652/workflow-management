"""
Task management models
"""

from datetime import datetime, date
from core import db


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
                    from .projects import TaskStatus
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