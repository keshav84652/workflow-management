"""
Main dashboard blueprint
"""

from flask import Blueprint, render_template, session

from .aggregator_service import DashboardAggregatorService
from src.shared.utils.consolidated import get_session_firm_id, get_session_user_id
from .aggregator_service import DashboardAggregatorService

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
def main():
    """Main dashboard route - follows Gemini's thin blueprint pattern"""
    firm_id = get_session_firm_id()
    user_id = get_session_user_id()
    
    # The blueprint only knows about ONE service - the aggregator
    # This follows Gemini's Rule #3: "Blueprints Shall Be Thin and Unintelligent"
    aggregator = DashboardAggregatorService()
    dashboard_data = aggregator.get_dashboard_data(firm_id, user_id)
    
    # Pass the structured data to the template
    return render_template('admin/dashboard_modern.html', 
                         projects=dashboard_data['projects_list'], 
                         tasks=dashboard_data['filtered_tasks'],
                         active_tasks_count=dashboard_data['tasks']['active'],
                         active_projects_count=dashboard_data['projects']['active'],
                         overdue_tasks_count=dashboard_data['tasks']['overdue'],
                         users_count=dashboard_data['users']['count'],
                         recent_tasks=dashboard_data['recent_tasks'],
                         recent_projects=dashboard_data['recent_projects'],
                         # Legacy data for template compatibility
                         total_tasks=dashboard_data['tasks']['total'],
                         completed_tasks=dashboard_data['tasks']['completed'],
                         active_clients=dashboard_data['clients']['active'],
                         task_status_data=dashboard_data['task_status_data'],
                         work_type_status_data=dashboard_data['work_type_data'],
                         priority_data=dashboard_data['priority_data'],
                         user_workload=dashboard_data['user_workload'],
                         upcoming_tasks=dashboard_data['upcoming_tasks'],
                         today_tasks=dashboard_data['today_tasks_count'],
                         due_this_week=dashboard_data['tasks']['due_soon'])