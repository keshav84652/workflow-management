"""
Main dashboard blueprint
"""

from flask import Blueprint, render_template, session
from datetime import datetime, date, timedelta
from core import db
from models import Project, Task, Client, User, WorkType, TaskStatus

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
def main():
    firm_id = session['firm_id']
    projects = Project.query.filter_by(firm_id=firm_id, status='Active').all()
    
    # Basic counts - include both project tasks and independent tasks
    total_tasks = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        )
    ).count()
    
    # Count completed tasks using new status system
    completed_tasks = Task.query.outerjoin(Project).outerjoin(TaskStatus).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        ),
        db.or_(
            TaskStatus.is_terminal == True,  # New status system
            db.and_(Task.status_id.is_(None), Task.status == 'Completed')  # Legacy fallback
        )
    ).count()
    
    # Count overdue tasks (exclude completed)
    overdue_tasks = Task.query.outerjoin(Project).outerjoin(TaskStatus).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        ),
        Task.due_date < date.today(),
        db.or_(
            TaskStatus.is_terminal == False,  # New status system
            db.and_(Task.status_id.is_(None), Task.status != 'Completed')  # Legacy fallback
        )
    ).count()
    
    active_clients = Client.query.filter_by(firm_id=firm_id, is_active=True).count()
    
    # Get work types for enhanced dashboard
    work_types = WorkType.query.filter_by(firm_id=firm_id, is_active=True).all()
    
    # Task status distribution by work type
    work_type_status_data = {}
    for work_type in work_types:
        work_type_data = {
            'name': work_type.name,
            'color': work_type.color,
            'statuses': {}
        }
        
        for status in work_type.task_statuses:
            # Count tasks with this specific status
            count = Task.query.join(Project).filter(
                Project.firm_id == firm_id,
                Project.work_type_id == work_type.id,
                Task.status_id == status.id
            ).count()
            work_type_data['statuses'][status.name] = {
                'count': count,
                'color': status.color,
                'is_terminal': status.is_terminal
            }
        
        work_type_status_data[work_type.name] = work_type_data
    
    # Legacy status distribution for backward compatibility
    task_status_data = {}
    for status in ['Not Started', 'In Progress', 'Needs Review', 'Completed']:
        count = Task.query.outerjoin(Project).filter(
            db.or_(
                Project.firm_id == firm_id,
                db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            ),
            Task.status == status
        ).count()
        task_status_data[status] = count
    
    # Priority distribution (exclude completed tasks)
    priority_data = {}
    for priority in ['High', 'Medium', 'Low']:
        count = Task.query.outerjoin(Project).outerjoin(TaskStatus).filter(
            db.or_(
                Project.firm_id == firm_id,
                db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            ),
            Task.priority == priority,
            db.or_(
                TaskStatus.is_terminal == False,  # New status system
                db.and_(Task.status_id.is_(None), Task.status != 'Completed')  # Legacy fallback
            )
        ).count()
        priority_data[priority] = count
    
    # Recent activity (last 7 days)
    week_ago = datetime.now() - timedelta(days=7)
    recent_tasks = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        ),
        Task.created_at >= week_ago
    ).count()
    
    # Workload by user - include both project tasks and independent tasks
    user_workload = {}
    users = User.query.filter_by(firm_id=firm_id).all()
    for user in users:
        active_tasks = Task.query.outerjoin(Project).outerjoin(TaskStatus).filter(
            db.or_(
                Project.firm_id == firm_id,
                db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            ),
            Task.assignee_id == user.id,
            db.or_(
                TaskStatus.is_terminal == False,  # New status system
                db.and_(Task.status_id.is_(None), Task.status.in_(['Not Started', 'In Progress', 'Needs Review']))  # Legacy fallback
            )
        ).count()
        user_workload[user.name] = active_tasks
    
    # Upcoming deadlines (next 7 days) - include both project tasks and independent tasks
    next_week = date.today() + timedelta(days=7)
    upcoming_tasks = Task.query.outerjoin(Project).outerjoin(TaskStatus).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        ),
        Task.due_date.between(date.today(), next_week),
        db.or_(
            TaskStatus.is_terminal == False,  # New status system
            db.and_(Task.status_id.is_(None), Task.status != 'Completed')  # Legacy fallback
        )
    ).order_by(Task.due_date.asc()).limit(5).all()
    
    # Critical notifications - overdue and due today
    today_tasks = Task.query.outerjoin(Project).outerjoin(TaskStatus).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        ),
        Task.due_date == date.today(),
        db.or_(
            TaskStatus.is_terminal == False,  # New status system
            db.and_(Task.status_id.is_(None), Task.status != 'Completed')  # Legacy fallback
        )
    ).count()
    
    # Due this week count
    due_this_week = Task.query.outerjoin(Project).outerjoin(TaskStatus).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        ),
        Task.due_date.between(date.today(), next_week),
        db.or_(
            TaskStatus.is_terminal == False,  # New status system
            db.and_(Task.status_id.is_(None), Task.status != 'Completed')  # Legacy fallback
        )
    ).count()
    
    # Get recent tasks and projects for the modern dashboard
    recent_tasks_list = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        )
    ).order_by(Task.created_at.desc()).limit(10).all()
    
    recent_projects_list = Project.query.filter_by(firm_id=firm_id).order_by(Project.created_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard_modern.html', 
                         projects=projects, 
                         active_tasks_count=total_tasks - completed_tasks,
                         active_projects_count=len(projects),
                         overdue_tasks_count=overdue_tasks,
                         users_count=len(users),
                         recent_tasks=recent_tasks_list,
                         recent_projects=recent_projects_list,
                         # Legacy data for fallback
                         total_tasks=total_tasks,
                         completed_tasks=completed_tasks,
                         active_clients=active_clients,
                         task_status_data=task_status_data,
                         work_type_status_data=work_type_status_data,
                         work_types=work_types,
                         priority_data=priority_data,
                         user_workload=user_workload,
                         upcoming_tasks=upcoming_tasks,
                         today_tasks=today_tasks,
                         due_this_week=due_this_week)