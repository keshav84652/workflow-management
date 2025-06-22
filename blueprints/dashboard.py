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
    
    # Get all tasks first - include both project tasks and independent tasks
    # Order by due date and priority to match tasks page logic
    all_tasks = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        )
    ).order_by(
        Task.due_date.asc().nullslast(),
        db.case(
            (Task.priority == 'High', 1),
            (Task.priority == 'Medium', 2),
            (Task.priority == 'Low', 3),
            else_=4
        )
    ).all()
    
    # Filter to show only current active task per interdependent project (matching tasks page logic)
    filtered_tasks = []
    seen_projects = set()
    
    for task in all_tasks:
        if task.project and task.project.task_dependency_mode:
            # For interdependent projects, only count the first active task per project
            if task.project_id not in seen_projects and not task.is_completed:
                filtered_tasks.append(task)
                seen_projects.add(task.project_id)
        else:
            # For independent tasks or non-interdependent projects, count all tasks
            filtered_tasks.append(task)
    
    # Basic counts using filtered tasks
    total_tasks = len(filtered_tasks)
    completed_tasks = len([task for task in filtered_tasks if task.is_completed])
    
    # Count overdue tasks from filtered tasks (exclude completed)
    overdue_tasks = len([task for task in filtered_tasks if task.is_overdue and not task.is_completed])
    
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
    
    # Priority distribution from filtered tasks (exclude completed tasks)
    priority_data = {}
    for priority in ['High', 'Medium', 'Low']:
        count = len([task for task in filtered_tasks if task.priority == priority and not task.is_completed])
        priority_data[priority] = count
    
    # Recent activity (last 7 days) from filtered tasks
    week_ago = datetime.now() - timedelta(days=7)
    recent_tasks = len([task for task in filtered_tasks if task.created_at >= week_ago])
    
    # Workload by user from filtered tasks
    user_workload = {}
    users = User.query.filter_by(firm_id=firm_id).all()
    for user in users:
        active_tasks = len([task for task in filtered_tasks if task.assignee_id == user.id and not task.is_completed])
        user_workload[user.name] = active_tasks
    
    # Upcoming deadlines (next 7 days) from filtered tasks
    next_week = date.today() + timedelta(days=7)
    upcoming_tasks = [task for task in filtered_tasks 
                     if task.due_date and not task.is_completed 
                     and date.today() <= task.due_date <= next_week]
    upcoming_tasks = sorted(upcoming_tasks, key=lambda t: t.due_date)[:5]
    
    # Critical notifications - overdue and due today from filtered tasks
    today_tasks = len([task for task in filtered_tasks 
                      if task.due_date and task.due_date == date.today() and not task.is_completed])
    
    # Due this week count from filtered tasks
    due_this_week = len([task for task in filtered_tasks 
                        if task.due_date and not task.is_completed 
                        and date.today() <= task.due_date <= next_week])
    
    # Get recent tasks from filtered tasks for the modern dashboard
    recent_tasks_list = sorted(filtered_tasks, key=lambda t: t.created_at, reverse=True)[:10]
    
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