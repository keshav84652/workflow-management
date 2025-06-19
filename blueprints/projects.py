"""
Project management blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
from core import db
from models import Project, Template, Task, Client, TaskStatus, TemplateTask, WorkType, User, ActivityLog
from utils import calculate_task_due_date, find_or_create_client, create_activity_log

projects_bp = Blueprint('projects', __name__, url_prefix='/projects')


@projects_bp.route('/')
def list_projects():
    firm_id = session['firm_id']
    projects = Project.query.filter_by(firm_id=firm_id).all()
    return render_template('projects/projects.html', projects=projects)


@projects_bp.route('/create', methods=['GET', 'POST'])
def create_project():
    if request.method == 'POST':
        firm_id = session['firm_id']
        template_id = request.form.get('template_id')
        client_name = request.form.get('client_name')
        project_name = request.form.get('project_name')
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        due_date = request.form.get('due_date')
        if due_date:
            due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
        priority = request.form.get('priority', 'Medium')
        task_dependency_mode = request.form.get('task_dependency_mode') == 'true'
        
        # Find or create client
        client = find_or_create_client(client_name, firm_id)
        
        # Check if this was a new client
        was_new_client = client.email is None
        
        # Get template to access work type
        template = Template.query.get(template_id)
        
        # Auto-create work type from template if needed
        work_type_id = template.create_work_type_from_template()
        
        # Get the default (first) status for the work type
        default_status = TaskStatus.query.filter_by(
            work_type_id=work_type_id,
            is_default=True
        ).first()
        
        # Inherit sequential flag from template
        inherited_task_dependency_mode = template.task_dependency_mode if template else task_dependency_mode
        
        project = Project(
            name=project_name or f"{client.name} - {template.name}",
            client_id=client.id,
            work_type_id=work_type_id,  # Use the work type from template
            current_status_id=default_status.id if default_status else None,  # Set initial workflow status
            start_date=start_date,
            due_date=due_date,
            priority=priority,
            task_dependency_mode=inherited_task_dependency_mode,  # Inherit from template
            firm_id=firm_id,
            template_origin_id=template_id
        )
        db.session.add(project)
        db.session.flush()
        
        # Create tasks from template
        for template_task in template.template_tasks:
            # Calculate due date
            task_due_date = calculate_task_due_date(start_date, template_task)
            
            # Determine status: use template status if available, otherwise work type default
            status_id = None
            if template_task.default_status_id:
                status_id = template_task.default_status_id
            elif template.work_type_id:
                # Get default status for this work type
                default_status = TaskStatus.query.filter_by(
                    work_type_id=template.work_type_id,
                    is_default=True
                ).first()
                if default_status:
                    status_id = default_status.id
            
            task = Task(
                title=template_task.title,
                description=template_task.description,
                due_date=task_due_date,
                priority=template_task.default_priority or 'Medium',
                estimated_hours=template_task.estimated_hours,
                project_id=project.id,
                assignee_id=template_task.default_assignee_id,
                template_task_origin_id=template_task.id,
                status_id=status_id,  # Use new status system
                dependencies=template_task.dependencies,  # Copy dependencies
                firm_id=firm_id
            )
            db.session.add(task)
        
        db.session.commit()
        
        # Activity log
        user_id = session.get('user_id')
        create_activity_log(f'Project "{project.name}" created', user_id, project.id)
        
        success_msg = 'Project created successfully!'
        if was_new_client:
            success_msg += f' New client "{client.name}" was added. Please complete their information in the Clients section.'
        
        flash(success_msg, 'success')
        return redirect(url_for('projects.view_project', id=project.id))
    
    firm_id = session['firm_id']
    templates = Template.query.filter_by(firm_id=firm_id).all()
    clients = Client.query.filter_by(firm_id=firm_id, is_active=True).all()
    return render_template('projects/create_project.html', templates=templates, clients=clients)


@projects_bp.route('/<int:id>')
def view_project(id):
    project = Project.query.get_or_404(id)
    if project.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('projects.list_projects'))
    
    tasks = Task.query.filter_by(project_id=id).order_by(Task.due_date.asc()).all()
    activity_logs = ActivityLog.query.filter_by(project_id=id).order_by(ActivityLog.timestamp.desc()).limit(10).all()
    
    return render_template('projects/view_project.html', project=project, tasks=tasks, activity_logs=activity_logs)


@projects_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit_project(id):
    project = Project.query.get_or_404(id)
    if project.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('projects.list_projects'))
    
    if request.method == 'POST':
        # Update project details
        project.name = request.form.get('name')
        project.priority = request.form.get('priority', 'Medium')
        project.status = request.form.get('status', 'Active')
        
        # Handle due date
        due_date = request.form.get('due_date')
        if due_date:
            project.due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
        else:
            project.due_date = None
        
        # Handle start date
        start_date = request.form.get('start_date')
        if start_date:
            project.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        
        db.session.commit()
        
        # Activity log
        create_activity_log(f'Project "{project.name}" updated', session['user_id'], project.id)
        
        flash('Project updated successfully!', 'success')
        return redirect(url_for('projects.view_project', id=project.id))
    
    # GET request - show form
    firm_id = session['firm_id']
    users = User.query.filter_by(firm_id=firm_id).all()
    return render_template('projects/edit_project.html', project=project, users=users)