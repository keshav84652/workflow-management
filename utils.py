import secrets
import string
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from models import db, ActivityLog, TemplateTask, Task, Project

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
                        template_task_origin_id=template_task.id
                    )
                    db.session.add(task)
    
    db.session.commit()