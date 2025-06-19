"""
Views and interface modes blueprint (Calendar, Kanban, Search, Reports)
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime, date, timedelta
from core import db
from models import Task, Project, User, WorkType, Template, TemplateTask, Client

views_bp = Blueprint('views', __name__)


@views_bp.route('/calendar')
def calendar_view():
    firm_id = session['firm_id']
    
    # Get year and month from query parameters or use current date
    year = int(request.args.get('year', date.today().year))
    month = int(request.args.get('month', date.today().month))
    
    # Create date object for the requested month
    current_date = date(year, month, 1)
    
    # Get start and end dates for the calendar view (include previous/next month days)
    start_of_month = date(year, month, 1)
    
    # Get the first day of the week for the month
    first_weekday = start_of_month.weekday()
    # Adjust for Sunday start (weekday() returns 0=Monday, we want 0=Sunday)
    days_back = (first_weekday + 1) % 7
    calendar_start = start_of_month - timedelta(days=days_back)
    
    # Get end of month
    if month == 12:
        end_of_month = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_of_month = date(year, month + 1, 1) - timedelta(days=1)
    
    # Calculate days forward to complete the calendar grid (6 weeks * 7 days = 42 days)
    days_shown = (end_of_month - calendar_start).days + 1
    days_needed = 42 - days_shown
    calendar_end = end_of_month + timedelta(days=days_needed)
    
    # Query tasks for the calendar period - include both project and independent tasks
    tasks = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        ),
        Task.due_date.between(calendar_start, calendar_end)
    ).order_by(Task.due_date.asc()).all()
    
    # Organize tasks by date
    calendar_data = {}
    for task in tasks:
        if task.due_date:
            date_str = task.due_date.strftime('%Y-%m-%d')
            if date_str not in calendar_data:
                calendar_data[date_str] = []
            
            # Prepare task data for JSON serialization
            task_data = {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'priority': task.priority,
                'is_overdue': task.is_overdue,
                'is_due_soon': task.is_due_soon,
                'project_name': task.project.client_name if task.project else None,
                'assignee_name': task.assignee.name if task.assignee else None
            }
            calendar_data[date_str].append(task_data)
    
    return render_template('admin/calendar.html', 
                         calendar_data=calendar_data,
                         current_date=current_date,
                         year=year,
                         month=month)

@views_bp.route('/search')
def search():
    firm_id = session['firm_id']
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')
    
    results = {
        'tasks': [],
        'projects': [],
        'clients': [],
        'query': query,
        'search_type': search_type
    }
    
    if not query:
        return render_template('admin/search.html', **results)
    
    # Search tasks
    if search_type in ['all', 'tasks']:
        task_query = Task.query.outerjoin(Project).filter(
            db.or_(
                Project.firm_id == firm_id,
                db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            )
        )
        
        # Search in task title, description, and comments
        task_filters = db.or_(
            Task.title.ilike(f'%{query}%'),
            Task.description.ilike(f'%{query}%')
        )
        
        results['tasks'] = task_query.filter(task_filters).limit(20).all()
    
    # Search projects
    if search_type in ['all', 'projects']:
        project_filters = db.or_(
            Project.name.ilike(f'%{query}%'),
            Project.description.ilike(f'%{query}%') if hasattr(Project, 'description') else False
        )
        
        results['projects'] = Project.query.filter(
            Project.firm_id == firm_id
        ).filter(project_filters).limit(20).all()
    
    # Search clients
    if search_type in ['all', 'clients']:
        client_filters = db.or_(
            Client.name.ilike(f'%{query}%'),
            Client.email.ilike(f'%{query}%'),
            Client.contact_person.ilike(f'%{query}%') if hasattr(Client, 'contact_person') else False
        )
        
        results['clients'] = Client.query.filter(
            Client.firm_id == firm_id
        ).filter(client_filters).limit(20).all()
    
    return render_template('admin/search.html', **results)
EOF < /dev/null