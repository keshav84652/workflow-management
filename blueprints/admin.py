"""
Administrative functions blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
import os
from datetime import datetime

from core.db_import import db
from models import Firm, User, WorkType, TaskStatus, Template, TemplateTask, Task, Project
from utils.consolidated import generate_access_code

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
def login():
    return render_template('admin/admin_login.html')


@admin_bp.route('/authenticate', methods=['POST'])
def authenticate():
    from services.admin_service import AdminService
    
    password = request.form.get('password')
    admin_service = AdminService()
    result = admin_service.authenticate_admin(password)
    
    if result['success']:
        admin_service.set_admin_session()
        return redirect(url_for('admin.dashboard'))
    else:
        flash(result['message'], 'error')
        return redirect(url_for('admin.login'))


@admin_bp.route('/dashboard')
def dashboard():
    from services.admin_service import AdminService
    
    admin_service = AdminService()
    if not admin_service.is_admin_authenticated():
        return redirect(url_for('admin.login'))
    
    admin_service = AdminService()
    firms = admin_service.get_all_firms()
    stats = admin_service.get_firm_statistics()
    
    return render_template('admin/admin_dashboard.html', firms=firms, stats=stats)


@admin_bp.route('/dashboard/ultra-modern')
def dashboard_ultra_modern():
    """Ultra-modern dashboard with glassmorphism design"""
    from services.admin_service import AdminService
    
    admin_service = AdminService()
    if not admin_service.is_admin_authenticated():
        return redirect(url_for('admin.login'))
    
    try:
        # Get basic stats for the modern dashboard
        stats = admin_service.get_firm_statistics()
        
        # Mock data for demonstration - replace with real data
        context = {
            'active_tasks_count': stats.get('total_tasks', 0),
            'active_projects_count': stats.get('total_projects', 0), 
            'total_clients_count': stats.get('total_clients', 0),
            'overdue_tasks_count': stats.get('overdue_tasks', 0),
            'recent_activities': [],  # Add real activity data later
            'task_completion_rate': 75,
            'project_health_stats': {},
        }
        
        return render_template('admin/dashboard_ultra_modern.html', **context)
        
    except Exception as e:
        flash(f'Error loading ultra-modern dashboard: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))


# Template Management Routes
@admin_bp.route('/templates')
def templates():
    from services.template_service import TemplateService
    from utils.consolidated import get_session_firm_id
    
    firm_id = get_session_firm_id()
    template_service = TemplateService()
    templates = template_service.get_templates_by_firm(firm_id)
    return render_template('admin/templates.html', templates=templates)


@admin_bp.route('/templates/create', methods=['GET', 'POST'])
def create_template():
    if request.method == 'POST':
        from services.template_service import TemplateService
        from utils.consolidated import get_session_firm_id, get_session_user_id
        
        firm_id = get_session_firm_id()
        
        # Prepare tasks data
        tasks_data = []
        task_titles = request.form.getlist('tasks')
        task_descriptions = request.form.getlist('task_descriptions')
        recurrence_rules = request.form.getlist('recurrence_rules')
        
        for i, task_title in enumerate(task_titles):
            if task_title.strip():
                tasks_data.append({
                    'title': task_title.strip(),
                    'description': task_descriptions[i] if i < len(task_descriptions) else '',
                    'recurrence_rule': recurrence_rules[i] if i < len(recurrence_rules) else None
                })
        
        template_service = TemplateService()
        result = template_service.create_template(
            name=request.form.get('name'),
            description=request.form.get('description'),
            task_dependency_mode=request.form.get('task_dependency_mode') == 'true',
            firm_id=firm_id,
            tasks_data=tasks_data,
            user_id=get_session_user_id()
        )
        
        if result['success']:
            flash(result['message'], 'success')
        else:
            flash(result['message'], 'error')
        
        return redirect(url_for('admin.templates'))
    
    return render_template('admin/create_template.html')


@admin_bp.route('/templates/<int:id>/edit', methods=['GET', 'POST'])
def edit_template(id):
    from services.template_service import TemplateService
    from utils.consolidated import get_session_firm_id, get_session_user_id
    
    firm_id = get_session_firm_id()
    template_service = TemplateService()
    template = template_service.get_template_by_id(id, firm_id)
    if not template:
        flash('Template not found or access denied', 'error')
        return redirect(url_for('admin.templates'))
    
    if request.method == 'POST':
        # Prepare tasks data
        tasks_data = []
        task_titles = request.form.getlist('tasks')
        task_descriptions = request.form.getlist('task_descriptions')
        recurrence_rules = request.form.getlist('recurrence_rules')
        
        for i, task_title in enumerate(task_titles):
            if task_title.strip():
                tasks_data.append({
                    'title': task_title.strip(),
                    'description': task_descriptions[i] if i < len(task_descriptions) else '',
                    'recurrence_rule': recurrence_rules[i] if i < len(recurrence_rules) else None
                })
        
        template_service = TemplateService()
        result = template_service.update_template(
            template_id=id,
            name=request.form.get('name'),
            description=request.form.get('description'),
            task_dependency_mode=request.form.get('task_dependency_mode') == 'true',
            firm_id=firm_id,
            tasks_data=tasks_data,
            user_id=get_session_user_id()
        )
        
        if result['success']:
            flash(result['message'], 'success')
        else:
            flash(result['message'], 'error')
        
        return redirect(url_for('admin.templates'))
    
    return render_template('admin/edit_template.html', template=template)

@admin_bp.route('/generate-code', methods=['POST'])
def generate_access_code_route():
    from services.admin_service import AdminService
    
    admin_service = AdminService()
    if not admin_service.is_admin_authenticated():
        return redirect(url_for('admin.login'))
    
    firm_name = request.form.get('firm_name')
    admin_service = AdminService()
    result = admin_service.generate_firm_access_code(firm_name)
    
    if result['success']:
        flash(f'Access code generated: {result["firm"]["access_code"]}', 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/work_types', methods=['GET'])
def admin_work_types():
    from services.worktype_service import WorkTypeService
    from utils.consolidated import get_session_firm_id
    
    if session.get('user_role') != 'Admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard.main'))
    
    firm_id = get_session_firm_id()
    worktype_service = WorkTypeService()
    work_types_result = worktype_service.get_work_types_for_firm(firm_id)
    work_types = work_types_result.get('work_types', []) if work_types_result['success'] else []
    work_type_usage = worktype_service.get_work_type_usage_stats(firm_id)
    
    return render_template('admin/admin_work_types.html', 
                         work_types=work_types, 
                         work_type_usage=work_type_usage)


@admin_bp.route('/work_types/create', methods=['POST'])
def admin_create_work_type():
    from services.worktype_service import WorkTypeService
    from utils.consolidated import get_session_firm_id, get_session_user_id
    
    if session.get('user_role') != 'Admin':
        return jsonify({'error': 'Access denied'}), 403
    
    name = request.form.get('name')
    description = request.form.get('description')
    firm_id = get_session_firm_id()
    
    worktype_service = WorkTypeService()
    result = worktype_service.create_work_type(name, description, firm_id, get_session_user_id())
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('admin.admin_work_types'))


@admin_bp.route('/work_types/<int:work_type_id>/edit', methods=['POST'])
def admin_edit_work_type(work_type_id):
    from services.worktype_service import WorkTypeService
    from utils.consolidated import get_session_firm_id, get_session_user_id
    
    if session.get('user_role') != 'Admin':
        return jsonify({'error': 'Access denied'}), 403
    
    name = request.form.get('name')
    description = request.form.get('description')
    firm_id = get_session_firm_id()
    
    worktype_service = WorkTypeService()
    result = worktype_service.update_work_type(work_type_id, name, description, firm_id, get_session_user_id())
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('admin.admin_work_types'))


@admin_bp.route('/work_types/<int:work_type_id>/statuses/create', methods=['POST'])
def admin_create_status(work_type_id):
    from services.worktype_service import WorkTypeService
    from utils.consolidated import get_session_firm_id
    
    if session.get('user_role') != 'Admin':
        return jsonify({'error': 'Access denied'}), 403
    
    name = request.form.get('name')
    color = request.form.get('color', '#6b7280')
    firm_id = get_session_firm_id()
    
    worktype_service = WorkTypeService()
    result = worktype_service.create_task_status(work_type_id, name, color, firm_id)
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('admin.admin_work_types'))


@admin_bp.route('/statuses/<int:status_id>/edit', methods=['POST'])
def admin_edit_status(status_id):
    """Edit a task status"""
    from services.worktype_service import WorkTypeService
    from utils.consolidated import get_session_firm_id
    
    if session.get('user_role') != 'Admin':
        return jsonify({'error': 'Access denied'}), 403
    
    name = request.form.get('name')
    color = request.form.get('color')
    position = int(request.form.get('position', 1))
    is_default = request.form.get('is_default') == 'true'
    is_terminal = request.form.get('is_terminal') == 'true'
    firm_id = get_session_firm_id()
    
    worktype_service = WorkTypeService()
    result = worktype_service.update_task_status(
        status_id, name, color, position, is_default, is_terminal, firm_id
    )
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('admin.admin_work_types'))


@admin_bp.route('/process-recurring', methods=['POST'])
def admin_process_recurring():
    """Manual trigger for processing recurring tasks"""
    if session.get('user_role') != 'Admin':
        return jsonify({'error': 'Access denied'}), 403
    
    # TODO: Implement recurring task processing in appropriate service
    # This functionality was not implemented in the original utils
    return jsonify({'success': False, 'message': 'Recurring task processing not yet implemented'})
