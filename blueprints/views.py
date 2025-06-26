"""
Views and interface modes blueprint (Calendar, Kanban, Search, Reports)
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime, date, timedelta
from core import db
from models import Task, Project, User, WorkType, Template, TemplateTask, Client
from services.dashboard_service import DashboardService
from utils import get_session_firm_id

views_bp = Blueprint('views', __name__)


@views_bp.route('/calendar')
def calendar_view():
    firm_id = get_session_firm_id()
    
    # Get year and month from query parameters or use current date
    year = int(request.args.get('year', date.today().year))
    month = int(request.args.get('month', date.today().month))
    
    # Use DashboardService for business logic
    calendar_data = DashboardService.get_calendar_data(firm_id, year, month)
    
    # Prepare task data for JSON serialization
    serialized_calendar_data = {}
    for date_str, tasks in calendar_data['tasks_by_date'].items():
        serialized_calendar_data[date_str] = []
        for task in tasks:
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
            serialized_calendar_data[date_str].append(task_data)
    
    return render_template('admin/calendar.html', 
                         calendar_data=serialized_calendar_data,
                         current_date=calendar_data['current_date'],
                         year=calendar_data['year'],
                         month=calendar_data['month'])

@views_bp.route('/search')
def search():
    firm_id = get_session_firm_id()
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')
    
    # Prepare filters based on search type
    filters = {}
    if search_type != 'all':
        filters['search_type'] = search_type
    
    # Use DashboardService for business logic
    results = DashboardService.search_tasks_and_projects(firm_id, query, filters)
    
    # Add search type and clients if needed
    results['search_type'] = search_type
    
    # Handle client search separately since it's not in DashboardService
    if search_type in ['all', 'clients'] and query:
        client_filters = db.or_(
            Client.name.ilike(f'%{query}%'),
            Client.email.ilike(f'%{query}%'),
            Client.contact_person.ilike(f'%{query}%') if hasattr(Client, 'contact_person') else False
        )
        
        results['clients'] = Client.query.filter(
            Client.firm_id == firm_id
        ).filter(client_filters).limit(20).all()
    else:
        results['clients'] = []
    
    return render_template('admin/search.html', **results)


@views_bp.route('/reports/time-tracking')
def time_tracking_report():
    firm_id = get_session_firm_id()
    
    # Get filter parameters and convert to date objects if provided
    start_date = None
    end_date = None
    
    if request.args.get('start_date'):
        start_date = datetime.strptime(request.args.get('start_date'), '%Y-%m-%d').date()
    
    if request.args.get('end_date'):
        end_date = datetime.strptime(request.args.get('end_date'), '%Y-%m-%d').date()
    
    # Use DashboardService for business logic
    report_data = DashboardService.get_time_tracking_report(firm_id, start_date, end_date)
    
    # Handle additional filters that aren't in the service method
    user_id = request.args.get('user_id')
    project_id = request.args.get('project_id')
    
    tasks = report_data['tasks_with_time']
    
    # Apply additional filters if specified
    if user_id:
        tasks = [task for task in tasks if task.assignee_id == int(user_id)]
    
    if project_id:
        tasks = [task for task in tasks if task.project_id == int(project_id)]
    
    # Recalculate statistics for filtered results
    if user_id or project_id:
        total_hours = sum(task.actual_hours or 0 for task in tasks)
        billable_hours = sum(task.actual_hours or 0 for task in tasks if task.billable_rate and task.billable_rate > 0)
        total_revenue = sum((task.actual_hours or 0) * (task.billable_rate or 0) for task in tasks)
    else:
        total_hours = report_data['total_hours']
        billable_hours = report_data['billable_hours']
        total_revenue = report_data['total_revenue']
    
    # Get filter options
    users = User.query.filter_by(firm_id=firm_id).all()
    projects = Project.query.filter_by(firm_id=firm_id).all()
    
    return render_template('admin/time_tracking_report.html', 
                         tasks=tasks,
                         users=users,
                         projects=projects,
                         total_hours=total_hours,
                         billable_hours=billable_hours,
                         total_billable_amount=total_revenue)


@views_bp.route('/kanban')
def kanban_view():
    firm_id = get_session_firm_id()
    
    # Get filter parameters
    work_type_filter = request.args.get('work_type')
    priority_filter = request.args.get('priority')
    due_filter = request.args.get('due_filter')
    
    # Get work types for filtering
    work_types = WorkType.query.filter_by(firm_id=firm_id, is_active=True).all()
    
    # If no work type is selected and work types exist, redirect to the first one
    if not work_type_filter and work_types:
        return redirect(url_for('views.kanban_view', work_type=work_types[0].id))
    
    # Use DashboardService for basic kanban data
    kanban_data = DashboardService.get_kanban_data(firm_id)
    
    # Handle advanced filtering (work type, priority, due date)
    # This logic is specific to the views and not in the service
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
            else:
                # Use work type statuses as kanban columns
                kanban_columns = TaskStatus.query.filter_by(
                    work_type_id=current_work_type.id
                ).order_by(TaskStatus.position.asc()).all()
    
    # Apply additional filters to the projects from the service
    projects = []
    for column_projects in kanban_data['projects'].values():
        projects.extend(column_projects)
    
    # Apply work type filter
    if work_type_filter and current_work_type:
        projects = [p for p in projects if p.work_type_id == current_work_type.id]
    
    # Apply priority filter
    if priority_filter:
        projects = [p for p in projects if p.priority == priority_filter]
    
    # Apply due date filters
    today = date.today()
    if due_filter == 'overdue':
        projects = [p for p in projects if p.due_date and p.due_date < today]
    elif due_filter == 'today':
        projects = [p for p in projects if p.due_date == today]
    elif due_filter == 'this_week':
        week_end = today + timedelta(days=7)
        projects = [p for p in projects if p.due_date and today <= p.due_date <= week_end]
    
    # Use the service's kanban organization if no special columns are needed
    if not kanban_columns:
        projects_by_column = kanban_data['projects']
        project_counts = {k: len(v) for k, v in projects_by_column.items()}
    else:
        # Custom column organization for work type filtering
        projects_by_column = {}
        project_counts = {}
        
        # Initialize columns
        for column in kanban_columns:
            column_id = column.id if hasattr(column, 'id') else column.name
            projects_by_column[column_id] = []
            project_counts[column_id] = 0
        
        # Add completed column
        projects_by_column['completed'] = []
        project_counts['completed'] = 0
        
        # Assign filtered projects to columns
        for project in projects:
            if project.status == 'Completed' or project.progress_percentage == 100:
                projects_by_column['completed'].append(project)
                project_counts['completed'] += 1
            elif kanban_columns:
                # Place in first column as default
                first_column = kanban_columns[0]
                column_id = first_column.id if hasattr(first_column, 'id') else first_column.name
                projects_by_column[column_id].append(project)
                project_counts[column_id] += 1
    
    return render_template('projects/kanban_modern.html', 
                         projects_by_column=projects_by_column,
                         project_counts=project_counts,
                         kanban_columns=kanban_columns,
                         current_work_type=current_work_type,
                         work_types=work_types,
                         users=kanban_data['users'],
                         today=date.today())
