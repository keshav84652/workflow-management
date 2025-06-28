"""
Views and interface modes blueprint (Calendar, Kanban, Search, Reports)
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime, date, timedelta

from models import Task, Project, User, WorkType, Template, TemplateTask, Client, TaskStatus
from services.dashboard_aggregator_service import DashboardAggregatorService
from services.client_service import ClientService
from services.user_service import UserService
from services.project_service import ProjectService
from services.views_service import ViewsService
from services.worktype_service import WorkTypeService
from utils.consolidated import get_session_firm_id

views_bp = Blueprint('views', __name__)


@views_bp.route('/calendar')
def calendar_view():
    firm_id = get_session_firm_id()
    
    # Get year and month from query parameters or use current date
    year = int(request.args.get('year', date.today().year))
    month = int(request.args.get('month', date.today().month))
    
    # Use DashboardAggregatorService for business logic
    dashboard_service = DashboardAggregatorService()
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
    
    # Use DashboardAggregatorService for business logic
    dashboard_service = DashboardAggregatorService()
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
    
    # Get additional filters
    user_id = request.args.get('user_id')
    project_id = request.args.get('project_id')
    
    # Use ViewsService for time tracking data
    tracking_result = ViewsService.get_time_tracking_data(
        firm_id=firm_id,
        start_date=start_date,
        end_date=end_date,
        user_id=user_id,
        project_id=project_id
    )
    
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
    
    # Use ViewsService for kanban data
    kanban_result = ViewsService.get_kanban_data(
        firm_id=firm_id,
        work_type_filter=work_type_filter,
        priority_filter=priority_filter,
        due_filter=due_filter
    )
    
    if not kanban_result['success']:
        flash(f'Error loading kanban data: {kanban_result["message"]}', 'error')
        return redirect(url_for('dashboard.main'))
    
    work_types = kanban_result['work_types']
    current_work_type = kanban_result['current_work_type']
    kanban_columns = kanban_result['kanban_columns']
    projects = kanban_result['projects']
    
    # If no work type is selected and work types exist, redirect to the first one
    if not work_type_filter and work_types:
        return redirect(url_for('views.kanban_view', work_type=work_types[0].id))
    
    # Organize projects by kanban columns
    if kanban_columns:
        organize_result = ViewsService.organize_projects_by_kanban_columns(projects, kanban_columns)
        if organize_result['success']:
            projects_by_column = organize_result['projects_by_column']
            project_counts = organize_result['project_counts']
            kanban_columns = organize_result['kanban_columns']
        else:
            flash(f'Error organizing kanban: {organize_result["message"]}', 'error')
            projects_by_column = {'all': projects}
            project_counts = {'all': len(projects)}
            kanban_columns = []
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
