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


@views_bp.route('/reports/time-tracking')
def time_tracking_report():
    firm_id = session['firm_id']
    
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    user_id = request.args.get('user_id')
    project_id = request.args.get('project_id')
    
    # Base query for tasks with time logged
    query = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        ),
        Task.actual_hours > 0
    )
    
    # Apply filters
    if start_date:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        query = query.filter(Task.updated_at >= start_date_obj)
    
    if end_date:
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        query = query.filter(Task.updated_at <= end_date_obj)
    
    if user_id:
        query = query.filter(Task.assignee_id == user_id)
    
    if project_id:
        query = query.filter(Task.project_id == project_id)
    
    tasks = query.order_by(Task.updated_at.desc()).all()
    
    # Calculate summary statistics
    total_hours = sum(task.actual_hours or 0 for task in tasks)
    billable_hours = sum(task.actual_hours or 0 for task in tasks if task.is_billable)
    total_billable_amount = sum(task.billable_amount for task in tasks)
    
    # Get filter options
    users = User.query.filter_by(firm_id=firm_id).all()
    projects = Project.query.filter_by(firm_id=firm_id).all()
    
    return render_template('admin/time_tracking_report.html', 
                         tasks=tasks,
                         users=users,
                         projects=projects,
                         total_hours=total_hours,
                         billable_hours=billable_hours,
                         total_billable_amount=total_billable_amount)


@views_bp.route('/kanban')
def kanban_view():
    firm_id = session['firm_id']
    
    # Get filter parameters
    work_type_filter = request.args.get('work_type')
    priority_filter = request.args.get('priority')
    due_filter = request.args.get('due_filter')
    
    # Get work types for filtering
    work_types = WorkType.query.filter_by(firm_id=firm_id, is_active=True).all()
    
    # If no work type is selected and work types exist, redirect to the first one
    if not work_type_filter and work_types:
        return redirect(url_for('views.kanban_view', work_type=work_types[0].id))
    
    current_work_type = None
    kanban_columns = []
    
    if work_type_filter:
        current_work_type = WorkType.query.filter_by(id=work_type_filter, firm_id=firm_id).first()
        if current_work_type:
            # Get the template associated with this work type
            template = Template.query.filter_by(
                work_type_id=current_work_type.id,
                firm_id=firm_id
            ).first()
            
            if template:
                # Use template tasks as Kanban columns
                kanban_columns = TemplateTask.query.filter_by(
                    template_id=template.id
                ).order_by(TemplateTask.order.asc()).all()
    
    # Base query for projects (not individual tasks)
    query = Project.query.filter_by(firm_id=firm_id, status='Active')
    
    # Apply work type filter
    if work_type_filter and current_work_type:
        query = query.filter(Project.work_type_id == current_work_type.id)
    
    # Apply priority filter
    if priority_filter:
        query = query.filter(Project.priority == priority_filter)
    
    # Apply due date filters
    today = date.today()
    if due_filter == 'overdue':
        query = query.filter(Project.due_date < today)
    elif due_filter == 'today':
        query = query.filter(Project.due_date == today)
    elif due_filter == 'this_week':
        week_end = today + timedelta(days=7)
        query = query.filter(Project.due_date.between(today, week_end))
    
    # Get all projects
    projects = query.order_by(Project.created_at.desc()).all()
    
    # Organize projects by current task progress (simplified version)
    projects_by_column = {}
    project_counts = {}
    
    if kanban_columns:
        # Initialize columns
        for column in kanban_columns:
            projects_by_column[column.id] = []
            project_counts[column.id] = 0
        
        # Add a "Completed" column for finished projects
        projects_by_column['completed'] = []
        project_counts['completed'] = 0
        
        # Assign projects to columns based on their current status
        for project in projects:
            if project.status == 'Completed':
                # Completed projects go to a special completed column
                projects_by_column['completed'].append(project)
                project_counts['completed'] += 1
            elif project.current_status_id:
                # Project has a workflow status - find matching column
                status_found = False
                for column in kanban_columns:
                    if column.default_status_id == project.current_status_id:
                        projects_by_column[column.id].append(project)
                        project_counts[column.id] += 1
                        status_found = True
                        break
                
                # If no matching column found, put in first column
                if not status_found and len(kanban_columns) > 0:
                    projects_by_column[kanban_columns[0].id].append(project)
                    project_counts[kanban_columns[0].id] += 1
            else:
                # Project has no current status - put in first column (default)
                if len(kanban_columns) > 0:
                    projects_by_column[kanban_columns[0].id].append(project)
                    project_counts[kanban_columns[0].id] += 1
    else:
        projects_by_column = {}
        project_counts = {}
    
    # Get filter options
    users = User.query.filter_by(firm_id=firm_id).all()
    
    return render_template('projects/kanban_modern.html', 
                         projects_by_column=projects_by_column,
                         project_counts=project_counts,
                         kanban_columns=kanban_columns,
                         current_work_type=current_work_type,
                         work_types=work_types,
                         users=users,
                         today=date.today())
