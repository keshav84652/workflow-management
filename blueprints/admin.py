"""
Administrative functions blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
import os
from datetime import datetime
from core import db
from models import Firm, User, WorkType, TaskStatus, Template, TemplateTask, Task, Project
from utils import generate_access_code

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
def login():
    return render_template('admin/admin_login.html')


@admin_bp.route('/authenticate', methods=['POST'])
def authenticate():
    password = request.form.get('password')
    # Simple admin authentication - in production use proper auth
    if password == os.environ.get('ADMIN_PASSWORD', 'admin123'):  # This should be configurable
        session['admin'] = True
        return redirect(url_for('admin.dashboard'))
    else:
        flash('Invalid admin password', 'error')
        return redirect(url_for('admin.login'))


@admin_bp.route('/dashboard')
def dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin.login'))
    
    # Basic admin dashboard functionality would go here
    firms = Firm.query.all()
    return render_template('admin/admin_dashboard.html', firms=firms)


# Template Management Routes
@admin_bp.route('/templates')
def templates():
    firm_id = session['firm_id']
    templates = Template.query.filter_by(firm_id=firm_id).all()
    return render_template('admin/templates.html', templates=templates)


@admin_bp.route('/templates/create', methods=['GET', 'POST'])
def create_template():
    if request.method == 'POST':
        firm_id = session['firm_id']
        
        template = Template(
            name=request.form.get('name'),
            description=request.form.get('description'),
            task_dependency_mode=request.form.get('task_dependency_mode') == 'true',
            firm_id=firm_id
        )
        db.session.add(template)
        db.session.flush()
        
        tasks_data = request.form.getlist('tasks')
        for i, task_title in enumerate(tasks_data):
            if task_title.strip():
                template_task = TemplateTask(
                    title=task_title.strip(),
                    description=request.form.getlist('task_descriptions')[i] if i < len(request.form.getlist('task_descriptions')) else '',
                    recurrence_rule=request.form.getlist('recurrence_rules')[i] if i < len(request.form.getlist('recurrence_rules')) else None,
                    order=i,
                    template_id=template.id
                )
                db.session.add(template_task)
        
        db.session.commit()
        
        # Auto-create work type from template
        try:
            template.create_work_type_from_template()
            flash('Template and workflow created successfully!', 'success')
        except Exception as e:
            flash(f'Template created, but workflow creation failed: {str(e)}', 'warning')
        
        return redirect(url_for('admin.templates'))
    
    return render_template('admin/create_template.html')


@admin_bp.route('/templates/<int:id>/edit', methods=['GET', 'POST'])
def edit_template(id):
    template = Template.query.get_or_404(id)
    if template.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('admin.templates'))
    
    if request.method == 'POST':
        template.name = request.form.get('name')
        template.description = request.form.get('description')
        template.task_dependency_mode = request.form.get('task_dependency_mode') == 'true'
        
        TemplateTask.query.filter_by(template_id=template.id).delete()
        
        tasks_data = request.form.getlist('tasks')
        for i, task_title in enumerate(tasks_data):
            if task_title.strip():
                template_task = TemplateTask(
                    title=task_title.strip(),
                    description=request.form.getlist('task_descriptions')[i] if i < len(request.form.getlist('task_descriptions')) else '',
                    recurrence_rule=request.form.getlist('recurrence_rules')[i] if i < len(request.form.getlist('recurrence_rules')) else None,
                    order=i,
                    template_id=template.id
                )
                db.session.add(template_task)
        
        db.session.commit()
        
        # Update work type from template if auto-creation is enabled
        try:
            if template.auto_create_work_type:
                # If work type already exists, we need to update the statuses
                if template.work_type_id:
                    # Delete existing statuses for this work type
                    TaskStatus.query.filter_by(work_type_id=template.work_type_id).delete()
                    
                    # Recreate statuses from updated template tasks
                    for i, template_task in enumerate(sorted(template.template_tasks, key=lambda t: t.workflow_order or t.order)):
                        status = TaskStatus(
                            firm_id=template.firm_id,
                            work_type_id=template.work_type_id,
                            name=template_task.title,
                            color='#6b7280' if i == 0 else '#3b82f6' if i < len(template.template_tasks) - 1 else '#10b981',
                            position=i + 1,
                            is_default=(i == 0),
                            is_terminal=(i == len(template.template_tasks) - 1)
                        )
                        db.session.add(status)
                        
                        # Link template task to its corresponding status
                        template_task.default_status_id = status.id
                    
                    # Update work type name to match template
                    work_type = WorkType.query.get(template.work_type_id)
                    if work_type:
                        work_type.name = template.name
                        work_type.description = f"Workflow for {template.name}"
                else:
                    # Create new work type if none exists
                    template.create_work_type_from_template()
                
                db.session.commit()
            
            flash('Template and workflow updated successfully!', 'success')
        except Exception as e:
            flash(f'Template updated, but workflow sync failed: {str(e)}', 'warning')
        
        return redirect(url_for('admin.templates'))
    
    return render_template('admin/edit_template.html', template=template)

@admin_bp.route('/generate-code', methods=['POST'])
def generate_access_code_route():
    if not session.get('admin'):
        return redirect(url_for('admin.login'))
    
    firm_name = request.form.get('firm_name')
    access_code = generate_access_code()
    
    firm = Firm(name=firm_name, access_code=access_code)
    db.session.add(firm)
    db.session.commit()
    
    flash(f'Access code generated: {access_code}', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/work_types', methods=['GET'])
def admin_work_types():
    if session.get('user_role') != 'Admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard.main'))
    
    work_types = WorkType.query.filter_by(firm_id=session['firm_id']).all()
    
    # Get task count by work type (through project relationship)
    work_type_usage = {}
    for wt in work_types:
        task_count = Task.query.join(Project).filter(
            Task.firm_id == session['firm_id'],
            Project.work_type_id == wt.id
        ).count()
        work_type_usage[wt.id] = task_count
    
    return render_template('admin/admin_work_types.html', 
                         work_types=work_types, 
                         work_type_usage=work_type_usage)


@admin_bp.route('/work_types/create', methods=['POST'])
def admin_create_work_type():
    if session.get('user_role') != 'Admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        name = request.form.get('name')
        description = request.form.get('description')
        
        work_type = WorkType(
            name=name,
            description=description,
            firm_id=session['firm_id']
        )
        db.session.add(work_type)
        db.session.flush()
        
        # Create default statuses
        default_statuses = [
            {'name': 'Not Started', 'color': '#6b7280', 'position': 1, 'is_default': True},
            {'name': 'In Progress', 'color': '#3b82f6', 'position': 2},
            {'name': 'Review', 'color': '#f59e0b', 'position': 3},
            {'name': 'Completed', 'color': '#10b981', 'position': 4, 'is_terminal': True}
        ]
        
        for status_data in default_statuses:
            status = TaskStatus(
                firm_id=session['firm_id'],
                work_type_id=work_type.id,
                **status_data
            )
            db.session.add(status)
        
        db.session.commit()
        
        flash(f'Work type "{name}" created successfully with default statuses!', 'success')
        return redirect(url_for('admin.admin_work_types'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating work type: {str(e)}', 'error')
        return redirect(url_for('admin.admin_work_types'))

@admin_bp.route('/work_types/<int:work_type_id>/edit', methods=['POST'])
def admin_edit_work_type(work_type_id):
    if session.get('user_role') != 'Admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        work_type = WorkType.query.filter_by(id=work_type_id, firm_id=session['firm_id']).first_or_404()
        
        work_type.name = request.form.get('name')
        work_type.description = request.form.get('description')
        
        db.session.commit()
        
        flash(f'Work type "{work_type.name}" updated successfully!', 'success')
        return redirect(url_for('admin.admin_work_types'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating work type: {str(e)}', 'error')
        return redirect(url_for('admin.admin_work_types'))


@admin_bp.route('/work_types/<int:work_type_id>/statuses/create', methods=['POST'])
def admin_create_status(work_type_id):
    if session.get('user_role') != 'Admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        work_type = WorkType.query.filter_by(id=work_type_id, firm_id=session['firm_id']).first_or_404()
        
        # Get next position
        max_position = db.session.query(db.func.max(TaskStatus.position)).filter_by(work_type_id=work_type_id).scalar() or 0
        
        status = TaskStatus(
            firm_id=session['firm_id'],
            work_type_id=work_type_id,
            name=request.form.get('name'),
            color=request.form.get('color', '#6b7280'),
            position=max_position + 1
        )
        
        db.session.add(status)
        db.session.commit()
        
        flash(f'Status "{status.name}" created successfully!', 'success')
        return redirect(url_for('admin.admin_work_types'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating status: {str(e)}', 'error')
        return redirect(url_for('admin.admin_work_types'))


@admin_bp.route('/statuses/<int:status_id>/edit', methods=['POST'])
def admin_edit_status(status_id):
    """Edit a task status"""
    if session.get('user_role') != 'Admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        status = TaskStatus.query.filter_by(id=status_id, firm_id=session['firm_id']).first_or_404()
        
        status.name = request.form.get('name')
        status.color = request.form.get('color')
        status.position = int(request.form.get('position', status.position))
        status.is_default = request.form.get('is_default') == 'true'
        status.is_terminal = request.form.get('is_terminal') == 'true'
        
        db.session.commit()
        
        flash(f'Status "{status.name}" updated successfully!', 'success')
        return redirect(url_for('admin.admin_work_types'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating status: {str(e)}', 'error')
        return redirect(url_for('admin.admin_work_types'))


@admin_bp.route('/process-recurring', methods=['POST'])
def admin_process_recurring():
    """Manual trigger for processing recurring tasks"""
    if session.get('user_role') != 'Admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        from utils import process_recurring_tasks
        process_recurring_tasks()
        return jsonify({'success': True, 'message': 'Recurring tasks processed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
