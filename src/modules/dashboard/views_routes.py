"""
Views and interface modes blueprint (Calendar, Kanban, Search, Reports)
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime, date, timedelta

from src.modules.project.models import Task, Project, WorkType, Template, TemplateTask, TaskStatus
from src.modules.client.models import Client
from src.models.auth import User
# Removed obsolete SharedUserService import
# ViewsService has been deprecated - functionality moved to individual services
# from src.shared.services import ViewsService
from src.shared.utils.consolidated import get_session_firm_id

views_bp = Blueprint('views', __name__)


@views_bp.route('/calendar')
def calendar_view():
    firm_id = get_session_firm_id()
    
    # Get year and month from query parameters or use current date
    year = int(request.args.get('year', date.today().year))
    month = int(request.args.get('month', date.today().month))
    
    # Get calendar data through task service using direct instantiation
    from src.modules.project.task_service import TaskService
    from src.modules.project.task_repository import TaskRepository
    task_service = TaskService(TaskRepository())
    
    calendar_result = task_service.get_tasks_for_calendar(firm_id, year, month)
    tasks_by_date = calendar_result.get('tasks_by_date', {}) if calendar_result.get('success') else {}
    
    # Prepare task data for JSON serialization
    serialized_calendar_data = {}
    for date_str, tasks in tasks_by_date.items():
        serialized_calendar_data[date_str] = []
        for task in tasks:
            task_data = {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'priority': task.priority,
                'is_overdue': getattr(task, 'is_overdue', False),
                'is_due_soon': getattr(task, 'is_due_soon', False),
                'project_name': task.project.name if task.project else None,
                'assignee_name': task.assignee.name if task.assignee else None
            }
            serialized_calendar_data[date_str].append(task_data)
    
    return render_template('admin/calendar.html', 
                         calendar_data=serialized_calendar_data,
                         current_date=date(year, month, 1),
                         year=year,
                         month=month)

@views_bp.route('/search')
def search():
    firm_id = get_session_firm_id()
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')
    
    # Prepare filters based on search type
    filters = {}
    if search_type != 'all':
        filters['search_type'] = search_type
    
    # Coordinate search across modules at route level using interfaces
    if query:
        from src.modules.project.task_service import TaskService
        from src.modules.project.task_repository import TaskRepository
        from src.modules.project.service import ProjectService
        from src.modules.project.repository import ProjectRepository
        from src.modules.client.service import ClientService
        from src.modules.client.repository import ClientRepository
        
        task_service = TaskService(TaskRepository())
        project_service = ProjectService(ProjectRepository())
        client_service = ClientService(ClientRepository())
        
        # Search each module's data
        tasks_result = task_service.search_tasks(firm_id, query, limit=20)
        projects_result = project_service.search_projects(firm_id, query, limit=20)
        clients_result = client_service.search_clients(firm_id, query, limit=20)
        
        # Aggregate results
        tasks = tasks_result.get('tasks', []) if tasks_result.get('success') else []
        projects = projects_result.get('projects', []) if projects_result.get('success') else []
        clients = clients_result.get('clients', []) if clients_result.get('success') else []
        
        results = {
            'tasks': tasks,
            'projects': projects,
            'clients': clients,
            'total_results': len(tasks) + len(projects) + len(clients),
            'search_type': search_type
        }
    else:
        results = {
            'tasks': [],
            'projects': [],
            'clients': [],
            'total_results': 0,
            'search_type': search_type
        }
    
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
    
    # Get additional filters
    user_id = request.args.get('user_id')
    project_id = request.args.get('project_id')
    
    # TEMPORARY: ViewsService deprecated - using placeholder data
    tracking_result = {
        'success': True,
        'tasks': [],
        'users': [],
        'projects': [],
        'total_hours': 0,
        'billable_hours': 0,
        'total_revenue': 0
    }
    
    if not tracking_result['success']:
        flash(f'Error loading time tracking data: {tracking_result["message"]}', 'error')
        return redirect(url_for('dashboard.main'))
    
    return render_template('admin/time_tracking_report.html', 
                         tasks=tracking_result['tasks'],
                         users=tracking_result['users'],
                         projects=tracking_result['projects'],
                         total_hours=tracking_result['total_hours'],
                         billable_hours=tracking_result['billable_hours'],
                         total_billable_amount=tracking_result['total_revenue'])


@views_bp.route('/kanban')
def kanban_view():
    firm_id = get_session_firm_id()
    
    # Get filter parameters
    work_type_filter = request.args.get('work_type')
    priority_filter = request.args.get('priority')
    due_filter = request.args.get('due_filter')
    
    # Get kanban data using ProjectService
    from src.modules.project.service import ProjectService
    from src.modules.project.repository import ProjectRepository
    project_service = ProjectService(ProjectRepository())
    
    kanban_result = project_service.get_kanban_view_data(firm_id)
    # kanban_result = ViewsService.get_kanban_data(
    #     firm_id=firm_id,
    #     work_type_filter=work_type_filter,
    #     priority_filter=priority_filter,
    #     due_filter=due_filter
    # )
    
    if not kanban_result.get('success', False):
        flash(f'Error loading kanban data: {kanban_result.get("message", "Unknown error")}', 'error')
        return redirect(url_for('dashboard.main'))
    
    # The service already returns organized data
    kanban_columns_data = kanban_result.get('columns', {})
    total_projects = kanban_result.get('total_projects', 0)
    
    # Convert to expected format for template
    projects_by_column = {}
    project_counts = {}
    kanban_columns = []
    
    for column_key, column_data in kanban_columns_data.items():
        projects_by_column[column_key] = column_data.get('projects', [])
        project_counts[column_key] = len(column_data.get('projects', []))
        
        # Create column object for template
        from collections import namedtuple
        Column = namedtuple('Column', ['id', 'title', 'order'])
        kanban_columns.append(Column(
            id=column_data.get('id', column_key),
            title=column_data.get('title', column_key),
            order=column_data.get('position', 0)
        ))
    
    # Get work types for filter dropdown
    from src.modules.project.models import WorkType
    work_types = WorkType.query.filter_by(firm_id=firm_id).all()
    current_work_type = None
    
    return render_template('projects/kanban_modern.html', 
                         projects_by_column=projects_by_column,
                         project_counts=project_counts,
                         kanban_columns=kanban_columns,
                         current_work_type=current_work_type,
                         work_types=work_types,
                         users=[],  # Users populated by client-side if needed for filtering
                         today=date.today())
