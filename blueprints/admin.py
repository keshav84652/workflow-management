"""
Administrative functions blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from core import db
from models import Firm, User, WorkType, TaskStatus, Template, TemplateTask

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
def login():
    return render_template('admin/admin_login.html')


@admin_bp.route('/authenticate', methods=['POST'])
def authenticate():
    password = request.form.get('password')
    # Simple admin authentication - in production use proper auth
    if password == 'admin123':  # This should be configurable
        session['admin_authenticated'] = True
        return redirect(url_for('admin.dashboard'))
    else:
        flash('Invalid admin password', 'error')
        return redirect(url_for('admin.login'))


@admin_bp.route('/dashboard')
def dashboard():
    if not session.get('admin_authenticated'):
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