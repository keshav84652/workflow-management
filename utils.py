import secrets
import string
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from core import db
from models import ActivityLog, TemplateTask, Task, Project, Client

def generate_access_code(length=12):
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def create_activity_log(action, user_id, project_id=None, task_id=None, details=None):
    log = ActivityLog(
        action=action,
        user_id=user_id,
        project_id=project_id,
        task_id=task_id,
        details=details
    )
    db.session.add(log)
    db.session.commit()

def calculate_task_due_date(project_start_date, template_task):
    """Calculate due date for a task based on project start and template settings"""
    if template_task.days_from_start:
        return project_start_date + timedelta(days=template_task.days_from_start)
    elif template_task.recurrence_rule:
        return calculate_next_due_date(template_task.recurrence_rule, project_start_date)
    return None

def find_or_create_client(client_name, firm_id):
    """Find existing client or create a new one with minimal info"""
    # Check if client already exists
    client = Client.query.filter_by(name=client_name.strip(), firm_id=firm_id).first()
    
    if not client:
        # Create new client with basic info
        client = Client(
            name=client_name.strip(),
            firm_id=firm_id,
            entity_type='Individual'  # Default
        )
        db.session.add(client)
        db.session.flush()  # Get the ID
    
    return client

def calculate_next_due_date(recurrence_rule, base_date=None):
    if not recurrence_rule:
        return None
    
    if base_date is None:
        base_date = date.today()
    
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
                next_month = base_date.replace(day=1) + relativedelta(months=1)
                return next_month.replace(day=calendar.monthrange(next_month.year, next_month.month)[1])
            elif day == 'last_biz_day':
                next_month = base_date.replace(day=1) + relativedelta(months=1)
                last_day = next_month.replace(day=calendar.monthrange(next_month.year, next_month.month)[1])
                while last_day.weekday() > 4:  # Saturday = 5, Sunday = 6
                    last_day -= timedelta(days=1)
                return last_day
            else:
                try:
                    day_num = int(day)
                    next_month = base_date.replace(day=1) + relativedelta(months=1)
                    max_day = calendar.monthrange(next_month.year, next_month.month)[1]
                    actual_day = min(day_num, max_day)
                    return next_month.replace(day=actual_day)
                except ValueError:
                    pass
        return base_date + relativedelta(months=1)
    
    elif frequency == 'quarterly':
        if len(parts) > 1 and parts[1] == 'last_biz_day':
            next_quarter_start = base_date.replace(day=1) + relativedelta(months=3)
            quarter_end_month = ((next_quarter_start.month - 1) // 3 + 1) * 3
            quarter_end = next_quarter_start.replace(month=quarter_end_month)
            quarter_end = quarter_end.replace(day=calendar.monthrange(quarter_end.year, quarter_end.month)[1])
            while quarter_end.weekday() > 4:
                quarter_end -= timedelta(days=1)
            return quarter_end
        return base_date + relativedelta(months=3)
    
    elif frequency == 'annually':
        return base_date + relativedelta(years=1)
    
    return None

def process_recurring_tasks():
    """Process both template-based and standalone recurring tasks"""
    
    # Process template-based recurring tasks
    template_tasks = TemplateTask.query.filter(TemplateTask.recurrence_rule.isnot(None)).all()
    
    for template_task in template_tasks:
        last_generated = Task.query.filter_by(
            template_task_origin_id=template_task.id
        ).order_by(Task.due_date.desc()).first()
        
        if last_generated:
            next_due = calculate_next_due_date(template_task.recurrence_rule, last_generated.due_date)
        else:
            next_due = calculate_next_due_date(template_task.recurrence_rule)
        
        if next_due and next_due <= date.today():
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
    
    # Process standalone recurring tasks
    recurring_tasks = RecurringTask.query.filter_by(is_active=True).all()
    
    for recurring_task in recurring_tasks:
        # Check if it's time to generate the next task
        if recurring_task.next_due_date <= date.today():
            # Check if task already exists for this due date
            existing_task = Task.query.filter_by(
                recurring_task_origin_id=recurring_task.id,
                due_date=recurring_task.next_due_date
            ).first()
            
            if not existing_task:
                # Create new task from recurring template
                task = Task(
                    title=recurring_task.title,
                    description=recurring_task.description,
                    due_date=recurring_task.next_due_date,
                    priority=recurring_task.priority,
                    estimated_hours=recurring_task.estimated_hours,
                    assignee_id=recurring_task.default_assignee_id,
                    status_id=recurring_task.status_id,
                    recurring_task_origin_id=recurring_task.id,
                    firm_id=recurring_task.firm_id
                )
                
                # If associated with a client, try to find an active project or make it independent
                if recurring_task.client_id:
                    # Find the most recent active project for this client and work type
                    project = Project.query.filter_by(
                        client_id=recurring_task.client_id,
                        work_type_id=recurring_task.work_type_id,
                        status='Active'
                    ).order_by(Project.created_at.desc()).first()
                    
                    if project:
                        task.project_id = project.id
                
                db.session.add(task)
                
                # Update recurring task's next due date and last generated
                recurring_task.last_generated = recurring_task.next_due_date
                recurring_task.next_due_date = calculate_next_due_date(
                    recurring_task.recurrence_rule, 
                    recurring_task.next_due_date
                )
                
                # Log the activity
                create_activity_log(
                    f'Recurring task "{recurring_task.title}" generated for {recurring_task.last_generated}',
                    recurring_task.default_assignee_id or 1,  # Fallback to admin user
                    task.project_id if hasattr(task, 'project_id') else None,
                    None  # Will be set after commit
                )
    
    db.session.commit()