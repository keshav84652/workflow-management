"""
Main dashboard blueprint
"""

from flask import Blueprint, render_template, session

from services.dashboard_service import DashboardService
from utils.session_helpers import get_session_firm_id, get_session_user_id

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
def main():
    """Main dashboard route - now uses DashboardService exclusively"""
    firm_id = get_session_firm_id()
    
    # Use service layer instead of direct database access
    dashboard_service = DashboardService()
    dashboard_data = dashboard_service.get_dashboard_data(firm_id)
    
    # All data now comes from the service layer - no direct database access!
    projects = dashboard_data['projects_list']
    tasks_data = dashboard_data['tasks']
    clients_data = dashboard_data['clients']
    work_type_status_data = dashboard_data['work_type_data']
    recent_tasks = dashboard_data['recent_tasks']
    recent_projects = dashboard_data['recent_projects']
    filtered_tasks = dashboard_data['filtered_tasks']  # Correctly filtered task list
    
    # Extract task statistics from service
    total_tasks = tasks_data['total']
    completed_tasks = tasks_data['completed']
    overdue_tasks = tasks_data['overdue']
    active_clients = clients_data['active']
    
    # All complex calculations should be moved to the service layer
    # For now, using simple data from service with TODO to enhance service
    
    # Legacy data for backward compatibility with existing templates
    task_status_data = {
        'Not Started': tasks_data['total'] - tasks_data['in_progress'] - tasks_data['completed'],
        'In Progress': tasks_data['in_progress'],
        'Needs Review': 0,  # TODO: Calculate in service if needed
        'Completed': tasks_data['completed']
    }
    
    # TODO: Move these calculations to DashboardService for proper architecture
    # For now, provide basic data to avoid template errors
    priority_data = {'High': 0, 'Medium': 0, 'Low': 0}  # TODO: Calculate in service
    user_workload = {}  # TODO: Get from service
    upcoming_tasks_list = recent_tasks[:5]  # Use recent tasks as placeholder
    today_tasks = 0  # TODO: Calculate in service
    due_this_week = tasks_data.get('due_soon', 0)  # Use due_soon from service
    users_count = dashboard_data['users']['count']
    
    # All data now comes from service - no more direct database queries!
    return render_template('admin/dashboard_modern.html', 
                         projects=projects, 
                         tasks=filtered_tasks,  # Pass correctly filtered tasks
                         active_tasks_count=tasks_data['active'],
                         active_projects_count=dashboard_data['projects']['active'],
                         overdue_tasks_count=overdue_tasks,
                         users_count=users_count,
                         recent_tasks=recent_tasks,
                         recent_projects=recent_projects,
                         # Legacy data for fallback
                         total_tasks=total_tasks,
                         completed_tasks=completed_tasks,
                         active_clients=active_clients,
                         task_status_data=task_status_data,
                         work_type_status_data=work_type_status_data,
                         priority_data=priority_data,
                         user_workload=user_workload,
                         upcoming_tasks=upcoming_tasks_list,
                         today_tasks=today_tasks,
                         due_this_week=due_this_week)