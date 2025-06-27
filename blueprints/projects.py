"""
Project management blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime

from core.db_import import db
from models import Project, Template, Task, Client, TaskStatus, TemplateTask, WorkType, User, ActivityLog, TaskComment, Attachment
from services.project_service import ProjectService
from services.task_service import TaskService
from services.client_service import ClientService
from services.template_service import TemplateService
from services.user_service import UserService
from services.activity_logging_service import ActivityLoggingService as ActivityService
from utils.consolidated import get_session_firm_id, get_session_user_id

projects_bp = Blueprint('projects', __name__, url_prefix='/projects')


@projects_bp.route('/')
def list_projects():
    firm_id = get_session_firm_id()
    projects = ProjectService.get_projects_for_firm(firm_id)
    return render_template('projects/projects.html', projects=projects)


@projects_bp.route('/create', methods=['GET', 'POST'])
def create_project():
    if request.method == 'POST':
        template_id = request.form.get('template_id')
        client_name = request.form.get('client_name')
        project_name = request.form.get('project_name')
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        due_date = request.form.get('due_date')
        if due_date:
            due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
        priority = request.form.get('priority', 'Medium')
        task_dependency_mode = request.form.get('task_dependency_mode') == 'true'
        
        # Use service layer for project creation
        result = ProjectService.create_project_from_template(
            template_id=template_id,
            client_name=client_name,
            project_name=project_name,
            start_date=start_date,
            due_date=due_date,
            priority=priority,
            task_dependency_mode=task_dependency_mode
        )
        
        if result['success']:
            success_msg = result['message']
            if result.get('new_client'):
                success_msg += f' New client was added. Please complete their information in the Clients section.'
            
            flash(success_msg, 'success')
            return redirect(url_for('projects.view_project', id=result['project_id']))
        else:
            flash(result['message'], 'error')
            return redirect(url_for('projects.create_project'))
    
    firm_id = get_session_firm_id()
    templates = TemplateService.get_templates_by_firm(firm_id)
    clients = ClientService.get_active_clients_by_firm(firm_id)
    return render_template('projects/create_project.html', templates=templates, clients=clients)


@projects_bp.route('/<int:id>')
def view_project(id):
    firm_id = get_session_firm_id()
    
    # Use service layer to get project
    project = ProjectService.get_project_by_id(id, firm_id)
    if not project:
        flash('Project not found or access denied', 'error')
        return redirect(url_for('projects.list_projects'))
    
    tasks = TemplateService.get_tasks_by_project(id)
    activity_logs = TemplateService.get_activity_logs_for_project(id, limit=10)
    
    return render_template('projects/view_project.html', project=project, tasks=tasks, activity_logs=activity_logs)


@projects_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit_project(id):
    firm_id = get_session_firm_id()
    
    # Use service layer to get project
    project = ProjectService.get_project_by_id(id, firm_id)
    if not project:
        flash('Project not found or access denied', 'error')
        return redirect(url_for('projects.list_projects'))
    
    if request.method == 'POST':
        # Prepare update data
        update_data = {
            'name': request.form.get('name'),
            'priority': request.form.get('priority', 'Medium'),
            'status': request.form.get('status', 'Active'),
            'due_date': None,
            'start_date': None
        }
        
        # Handle due date
        due_date = request.form.get('due_date')
        if due_date:
            try:
                update_data['due_date'] = datetime.strptime(due_date, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid due date format', 'error')
                return redirect(url_for('projects.edit_project', id=id))
        
        # Handle start date
        start_date = request.form.get('start_date')
        if start_date:
            try:
                update_data['start_date'] = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid start date format', 'error')
                return redirect(url_for('projects.edit_project', id=id))
        
        # Use service layer to update project
        result = ProjectService.update_project(id, firm_id, **update_data)
        
        if result['success']:
            flash(result['message'], 'success')
            return redirect(url_for('projects.view_project', id=id))
        else:
            flash(result['message'], 'error')
            return redirect(url_for('projects.edit_project', id=id))
    
    # GET request - show form
    users = UserService.get_users_by_firm(firm_id)
    return render_template('projects/edit_project.html', project=project, users=users)

@projects_bp.route('/<int:id>/delete', methods=['POST'])
def delete_project(id):
    firm_id = get_session_firm_id()
    
    # Use service layer to delete project
    result = ProjectService.delete_project(id, firm_id)
    
    if result['success']:
        return jsonify({
            'success': True,
            'message': result['message'],
            'redirect': url_for('projects.list_projects')
        })
    else:
        status_code = 403 if 'access' in result['message'].lower() else 500
        return jsonify({
            'success': False,
            'message': result['message']
        }), status_code


@projects_bp.route('/<int:id>/move-status', methods=['POST'])
def move_project_status(id):
    """Move project to different status for Kanban board"""
    from services.auth_service import AuthService
    
    # Check authentication
    auth_redirect = AuthService.require_authentication()
    if auth_redirect:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    
    firm_id = get_session_firm_id()
    user_id = get_session_user_id()
    data = request.get_json()
    status_id = data.get('status_id')
    
    result = ProjectService.move_project_status(id, status_id, firm_id, user_id)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify({'success': False, 'message': result['message']}), 500
