"""
Core Utilities for CPA WorkflowPilot
Common utility functions for general usage.
"""

import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

def generate_access_code(length: int = 8) -> str:
    """Generate a random access code"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def create_activity_log(action: str, user_id: Optional[int] = None, 
                       project_id: Optional[int] = None, 
                       task_id: Optional[int] = None) -> None:
    """Create an activity log entry"""
    from core import db
    from models import ActivityLog
    
    log = ActivityLog(
        action=action,
        user_id=user_id,
        project_id=project_id,
        task_id=task_id,
        timestamp=datetime.utcnow()
    )
    db.session.add(log)
    try:
        db.session.commit()
    except Exception as e:
        print(f"Error creating activity log: {e}")
        db.session.rollback()

def process_recurring_tasks() -> Dict[str, Any]:
    """Process recurring tasks"""
    from core import db
    from models import Task, TemplateTask
    
    try:
        tasks_created = 0
        
        # Get all recurring tasks due for creation
        recurring_tasks = Task.query.filter(
            Task.is_recurring == True,
            Task.next_due_date <= datetime.utcnow().date()
        ).all()
        
        for task in recurring_tasks:
            # Calculate next instance date
            next_instance = task.create_next_instance()
            if next_instance:
                db.session.add(next_instance)
                tasks_created += 1
        
        # Process template-based recurring tasks
        template_tasks = TemplateTask.query.filter(
            TemplateTask.recurrence_rule.isnot(None)
        ).all()
        
        for template_task in template_tasks:
            last_generated = Task.query.filter_by(
                template_task_origin_id=template_task.id
            ).order_by(Task.due_date.desc()).first()
            
            if last_generated:
                next_due = calculate_next_due_date(
                    template_task.recurrence_rule, 
                    last_generated.due_date
                )
            else:
                next_due = calculate_next_due_date(template_task.recurrence_rule)
            
            if next_due and next_due <= datetime.utcnow().date():
                projects = Project.query.filter_by(
                    template_origin_id=template_task.template_id,
                    status='Active'
                ).all()
                
                for project in projects:
                    existing_task = Task.query.filter_by(
                        project_id=project.id,
                        template_task_origin_id=template_task.id,
                        due_date=next_due
                    ).first()
                    
                    if not existing_task:
                        task = Task(
                            title=template_task.title,
                            description=template_task.description,
                            due_date=next_due,
                            project_id=project.id,
                            assignee_id=template_task.default_assignee_id,
                            template_task_origin_id=template_task.id,
                            firm_id=project.firm_id
                        )
                        db.session.add(task)
                        tasks_created += 1
        
        db.session.commit()
        
        return {
            'success': True,
            'tasks_created': tasks_created,
            'message': f'Created {tasks_created} recurring tasks'
        }
        
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'error': f'Failed to process recurring tasks: {str(e)}'
        }

def calculate_next_due_date(recurrence_rule: str, 
                          base_date: Optional[datetime] = None) -> Optional[datetime]:
    """Calculate next due date based on recurrence rule"""
    if not recurrence_rule:
        return None
    
    if base_date is None:
        base_date = datetime.utcnow().date()
    
    parts = recurrence_rule.split(':')
    frequency = parts[0]
    
    if frequency == 'daily':
        return base_date + timedelta(days=1)
    
    elif frequency == 'weekly':
        return base_date + timedelta(weeks=1)
    
    elif frequency == 'monthly':
        if len(parts) > 1:
            day = parts[1]
            if day == 'last_day':
                next_month = base_date.replace(day=1) + timedelta(days=32)
                return next_month.replace(day=1) - timedelta(days=1)
            elif day == 'last_biz_day':
                next_month = base_date.replace(day=1) + timedelta(days=32)
                last_day = (next_month.replace(day=1) - timedelta(days=1))
                while last_day.weekday() > 4:  # Saturday = 5, Sunday = 6
                    last_day -= timedelta(days=1)
                return last_day
            else:
                try:
                    day_num = int(day)
                    next_month = base_date.replace(day=1) + timedelta(days=32)
                    next_month = next_month.replace(day=1)
                    max_day = (next_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                    actual_day = min(day_num, max_day.day)
                    return next_month.replace(day=actual_day)
                except ValueError:
                    pass
        return base_date + timedelta(days=30)
    
    elif frequency == 'quarterly':
        if len(parts) > 1 and parts[1] == 'last_biz_day':
            next_quarter = base_date.replace(day=1)
            while (next_quarter.month - 1) % 3 != 0:
                next_quarter += timedelta(days=32)
                next_quarter = next_quarter.replace(day=1)
            next_quarter = (next_quarter + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            while next_quarter.weekday() > 4:
                next_quarter -= timedelta(days=1)
            return next_quarter
        return base_date + timedelta(days=90)
    
    elif frequency == 'annually':
        return base_date + timedelta(days=365)
    
    return None

def calculate_task_due_date(project_start_date: datetime, 
                          template_task: 'TemplateTask') -> Optional[datetime]:
    """Calculate due date for a task based on project start and template settings"""
    if template_task.days_from_start:
        return project_start_date + timedelta(days=template_task.days_from_start)
    elif template_task.recurrence_rule:
        return calculate_next_due_date(template_task.recurrence_rule, project_start_date)
    return None


def find_or_create_client(name: str, email: str, firm_id: int) -> 'Client':
    """Find or create a client by name and email"""
    from core import db
    from models import Client
    
    # Try to find by exact email match first
    client = Client.query.filter_by(
        email=email,
        firm_id=firm_id
    ).first()
    
    if client:
        return client
    
    # Try to find by name
    client = Client.query.filter_by(
        name=name,
        firm_id=firm_id
    ).first()
    
    if client:
        return client
    
    # Create new client
    client = Client(
        name=name,
        email=email,
        firm_id=firm_id
    )
    db.session.add(client)
    db.session.commit()
    
    return client


def format_currency(amount: float) -> str:
    """Format currency amount to string with dollar sign and commas"""
    return f"${amount:,.2f}"


def format_date(date_obj: datetime) -> str:
    """Format datetime object to readable string"""
    if date_obj is None:
        return ""
    return date_obj.strftime("%Y-%m-%d")


def calculate_business_days(start_date: datetime, end_date: datetime) -> int:
    """Calculate number of business days between two dates"""
    from datetime import timedelta
    
    if start_date > end_date:
        return 0
    
    business_days = 0
    current_date = start_date
    
    while current_date <= end_date:
        # Monday = 0, Sunday = 6
        if current_date.weekday() < 5:  # Monday to Friday
            business_days += 1
        current_date += timedelta(days=1)
    
    return business_days
