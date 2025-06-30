"""
Project management blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime

# All data access through services - no direct model imports
from .service import ProjectService
from .task_service import TaskService
from .repository import ProjectRepository
from .task_repository import TaskRepository
from src.shared.services import ActivityLoggingService as ActivityService
from src.shared.utils.consolidated import get_session_firm_id, get_session_user_id

projects_bp = Blueprint('projects', __name__, url_prefix='/projects')


@projects_bp.route('/')
def list_projects():
    firm_id = get_session_firm_id()
    project_service = ProjectService(ProjectRepository())
    projects = project_service.get_projects_for_firm(firm_id)
    return render_template('projects/projects.html', projects=projects)


@projects_bp.route('/create', methods=['GET', 'POST'])
def create_project():
    if request.method == 'POST':
        try:
            # Get form data
            project_name = request.form.get('project_name')
            client_id = request.form.get('client_id')  # Updated to use client_id instead of client_name
            work_type_id = request.form.get('work_type_id')
            description = request.form.get('description')
            
            firm_id = get_session_firm_id()
            user_id = get_session_user_id()
            
            # Use new exception-based service method
            project_service = ProjectService(ProjectRepository())
            project_data = project_service.create_project(
                name=project_name,
                description=description,
                client_id=int(client_id) if client_id else None,
                work_type_id=int(work_type_id) if work_type_id else None,
                firm_id=firm_id,
                user_id=user_id
            )
            
            # Success - project_data contains the created project DTO
            flash(f'Project "{project_data["name"]}" created successfully!', 'success')
            return redirect(url_for('projects.view_project', id=project_data['id']))
            
        except Exception as e:
            # The global error handler will catch ValidationError, NotFoundError, etc.
            # and handle them appropriately (flash message + redirect)
            # For now, let it bubble up to be handled by the global error handler
            raise
    
    firm_id = get_session_firm_id()
    
    # Coordinate between modules at the route level (acceptable pattern)
    # Get templates from admin module
    from src.modules.admin.template_service import TemplateService
    template_service = TemplateService()
    templates = template_service.get_templates_by_firm(firm_id)
    
    # Get clients from client module using interface
    from src.shared.di_container import get_service
    from src.modules.client.interface import IClientService
    client_service = get_service(IClientService)
    clients = client_service.get_active_clients_by_firm(firm_id)
    
    return render_template('projects/create_project.html', 
                         templates=templates, 
                         clients=clients)


@projects_bp.route('/<int:id>')
def view_project(id):
    firm_id = get_session_firm_id()
    
    # Use service layer to get project
    project_service = ProjectService(ProjectRepository())
    project = project_service.get_project_by_id(id, firm_id)
    if not project:
        flash('Project not found or access denied', 'error')
        return redirect(url_for('projects.list_projects'))
    
    # Get tasks and activity logs using proper domain services
    tasks = project_service.get_tasks_by_project(id)
    activity_logs = project_service.get_activity_logs_for_project(id, limit=10)
    
    return render_template('projects/view_project.html', project=project, tasks=tasks, activity_logs=activity_logs)


@projects_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit_project(id):
    firm_id = get_session_firm_id()
    
    # Use service layer to get project
    project_service = ProjectService(ProjectRepository())
    project = project_service.get_project_by_id(id, firm_id)
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
        result = project_service.update_project(id, firm_id, **update_data)
        
        if result['success']:
            flash(result['message'], 'success')
            return redirect(url_for('projects.view_project', id=id))
        else:
            flash(result['message'], 'error')
            return redirect(url_for('projects.edit_project', id=id))
    
    # GET request - show form
    auth_service = get_service(IAuthService)
    users = auth_service.get_users_by_firm(firm_id)
    return render_template('projects/edit_project.html', project=project, users=users)

@projects_bp.route('/<int:id>/delete', methods=['POST'])
def delete_project(id):
    firm_id = get_session_firm_id()
    
    # Use service layer to delete project
    project_service = ProjectService(ProjectRepository())
    result = project_service.delete_project(id, firm_id)
    
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
    from src.modules.auth.session_service import SessionService
    
    # Check authentication
    auth_redirect = SessionService.require_authentication()
    if auth_redirect:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    
    firm_id = get_session_firm_id()
    user_id = get_session_user_id()
    data = request.get_json()
    status_id = data.get('status_id')
    
    project_service = ProjectService(ProjectRepository())
    result = project_service.move_project_status(id, status_id, firm_id, user_id)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify({'success': False, 'message': result['message']}), 500
