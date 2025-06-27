"""
Views and interface modes blueprint (Calendar, Kanban, Search, Reports)
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime, date, timedelta

from models import Task, Project, User, WorkType, Template, TemplateTask, Client, TaskStatus
from services.dashboard_service import DashboardService
from services.client_service import ClientService
from services.user_service import UserService
from services.project_service import ProjectService
from utils.session_helpers import get_session_firm_id

views_bp = Blueprint('views', __name__)


@views_bp.route('/calendar')
def calendar_view():
    firm_id = get_session_firm_id()
    
    # Get year and month from query parameters or use current date
    year = int(request.args.get('year', date.today().year))
    month = int(request.args.get('month', date.today().month))
    
    # Use DashboardService for business logic
    dashboard_service = DashboardService()
    calendar_data = dashboard_service.get_calendar_data(firm_id, year, month)
    
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
    dashboard_service = DashboardService()
    results = dashboard_service.search_tasks_and_projects(firm_id, query, filters)
    
    # Add search type and clients if needed
    results['search_type'] = search_type
    
    # Use ClientService instead of direct database access - ARCHITECTURAL FIX
    if search_type in ['all', 'clients'] and query:
        results['clients'] = ClientService.search_clients(firm_id, query, limit=20)
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
    dashboard_service = DashboardService()
    report_data = dashboard_service.get_time_tracking_report(firm_id, start_date, end_date)
    
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
    
    # Get filter options using services - ARCHITECTURAL FIX
    users = UserService.get_users_by_firm(firm_id)
    projects = ProjectService.get_projects_by_firm(firm_id)
    
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
    
    # TODO: Create WorkTypeService to replace direct queries
    # For now, using direct query with TODO to fix later
    work_types = WorkType.query.filter_by(firm_id=firm_id, is_active=True).all()
    
    # If no work type is selected and work types exist, redirect to the first one
    if not work_type_filter and work_types:
        return redirect(url_for('views.kanban_view', work_type=work_types[0].id))
    
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
            
            # Use work type statuses as kanban columns 
            # (These are created from template tasks and have the same names like "Awaiting Documents")
            kanban_columns = TaskStatus.query.filter_by(
                work_type_id=current_work_type.id
            ).order_by(TaskStatus.position.asc()).all()
    
    # Get all projects for the firm
    projects = Project.query.filter_by(firm_id=firm_id).order_by(Project.created_at.desc()).all()
    
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
    
    # Organize projects by kanban columns based on the column type
    projects_by_column = {}
    project_counts = {}
    
    if kanban_columns:
        # Create wrapper objects so template can access with expected field names
        from collections import namedtuple
        Column = namedtuple('Column', ['id', 'title', 'order'])
        
        # Convert TaskStatus objects to Column objects for template compatibility
        wrapped_columns = []
        for status in kanban_columns:
            wrapped_columns.append(Column(status.id, status.name, status.position))
        kanban_columns = wrapped_columns
        
        # Initialize columns
        for column in kanban_columns:
            projects_by_column[column.id] = []
            project_counts[column.id] = 0
        
        # Add completed column for any completed projects
        projects_by_column['completed'] = []
        project_counts['completed'] = 0
        
        # Organize projects into columns
        for project in projects:
            # Check if project is completed first
            if project.status == 'Completed':
                projects_by_column['completed'].append(project)
                project_counts['completed'] += 1
            elif project.current_status_id:
                # Map project's current_status_id to the corresponding TaskStatus column
                column_found = False
                for column in kanban_columns:
                    if project.current_status_id == column.id:
                        projects_by_column[column.id].append(project)
                        project_counts[column.id] += 1
                        column_found = True
                        break
                
                # If no specific column found, put in first column
                if not column_found and kanban_columns:
                    first_column = kanban_columns[0]
                    projects_by_column[first_column.id].append(project)
                    project_counts[first_column.id] += 1
            else:
                # No current status - put in first column (default status)
                if kanban_columns:
                    first_column = kanban_columns[0]
                    projects_by_column[first_column.id].append(project)
                    project_counts[first_column.id] += 1
    else:
        # No kanban columns available - use basic organization
        projects_by_column = {'all': projects}
        project_counts = {'all': len(projects)}
        
        # Create a basic column structure
        from collections import namedtuple
        Column = namedtuple('Column', ['id', 'title', 'order'])
        kanban_columns = [Column('all', 'All Projects', 0)]
    
    return render_template('projects/kanban_modern.html', 
                         projects_by_column=projects_by_column,
                         project_counts=project_counts,
                         kanban_columns=kanban_columns,
                         current_work_type=current_work_type,
                         work_types=work_types,
                         users=[],  # TODO: Add users if needed
                         today=date.today())
