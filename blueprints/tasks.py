"""
Task management blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime, date, timedelta
import importlib.util
import os

# Import db from root core.py file
spec = importlib.util.spec_from_file_location("core", os.path.join(os.path.dirname(os.path.dirname(__file__)), "core.py"))
core_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core_module)
db = core_module.db
from models import Task, Project, User, Client, Template, ActivityLog, TaskComment, WorkType, TaskStatus
from utils import create_activity_log, get_session_firm_id, get_session_user_id
from services.task_service import TaskService

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')




@tasks_bp.route('/')
def list_tasks():
    from services.task_service import TaskService
    
    firm_id = get_session_firm_id()
    
    # Get filter parameters - support multiple values
    filters = {
        'status_filters': request.args.getlist('status'),
        'priority_filters': request.args.getlist('priority'),
        'assignee_filters': request.args.getlist('assignee'),
        'project_filters': request.args.getlist('project'),
        'overdue_filter': request.args.get('overdue'),
        'due_date_filter': request.args.get('due_date'),
        'show_completed': request.args.get('show_completed', 'false').lower() == 'true'
    }
    
    # Use optimized service method to get tasks with dependency info pre-calculated
    task_data_list = TaskService.get_tasks_with_dependency_info(firm_id, filters)
    tasks = [item['task'] for item in task_data_list]
    
    # Get filter options
    users = User.query.filter_by(firm_id=firm_id).all()
    projects = Project.query.filter_by(firm_id=firm_id).all()
    
    return render_template('tasks/tasks_modern.html', tasks=tasks, users=users, projects=projects, today=date.today())


@tasks_bp.route('/<int:id>/delete', methods=['POST'])
def delete_task(id):
    from services.task_service import TaskService
    
    firm_id = get_session_firm_id()
    result = TaskService.delete_task(id, firm_id)
    
    if result['success']:
        return jsonify({
            'success': True,
            'message': result['message']
        })
    else:
        status_code = 403 if 'access' in result['message'].lower() else 500
        return jsonify({
            'success': False,
            'message': result['message']
        }), status_code


@tasks_bp.route('/create', methods=['GET', 'POST'])
def create_task():
    if request.method == 'POST':
        firm_id = get_session_firm_id()
        user_id = get_session_user_id()
        
        # Use service layer for business logic
        result = TaskService.create_task_from_form(
            form_data=request.form,
            firm_id=firm_id,
            user_id=user_id
        )
        
        if result['success']:
            flash(result['message'], 'success')
            return redirect(url_for('tasks.list_tasks'))
        else:
            flash(result['message'], 'error')
            return redirect(url_for('tasks.create_task'))
    
    # GET request - show form
    firm_id = get_session_firm_id()
    projects = Project.query.filter_by(firm_id=firm_id, status='Active').all()
    users = User.query.filter_by(firm_id=firm_id).all()
    
    # Pre-select project if provided
    selected_project = request.args.get('project_id')
    
    # Pre-fill due date if provided (from calendar click)
    prefill_due_date = request.args.get('due_date')
    
    return render_template('tasks/create_task.html', projects=projects, users=users, selected_project=selected_project, prefill_due_date=prefill_due_date)


@tasks_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit_task(id):
    firm_id = get_session_firm_id()
    
    # Get task with access check using service layer
    task = TaskService.get_task_by_id_with_access_check(id, firm_id)
    if not task:
        flash('Task not found or access denied', 'error')
        return redirect(url_for('tasks.list_tasks'))
    
    if request.method == 'POST':
        user_id = get_session_user_id()
        
        # Use service layer for business logic
        result = TaskService.update_task_from_form(
            task_id=id,
            form_data=request.form,
            firm_id=firm_id,
            user_id=user_id
        )
        
        if result['success']:
            flash(result['message'], 'success')
            return redirect(url_for('tasks.view_task', id=id))
        else:
            flash(result['message'], 'error')
            return redirect(url_for('tasks.edit_task', id=id))
    
    # GET request - show form
    users = User.query.filter_by(firm_id=firm_id).all()
    
    # Get other tasks in the same project for dependency selection
    project_tasks = []
    if task.project_id:
        project_tasks = Task.query.filter_by(project_id=task.project_id).order_by(Task.title).all()
    
    return render_template('tasks/edit_task.html', task=task, users=users, project_tasks=project_tasks)


@tasks_bp.route('/<int:id>')
def view_task(id):
    firm_id = get_session_firm_id()
    
    # Get task with access check using service layer
    task = TaskService.get_task_by_id_with_access_check(id, firm_id)
    if not task:
        flash('Task not found or access denied', 'error')
        return redirect(url_for('tasks.list_tasks'))
    
    # Get task activity logs
    activity_logs = ActivityLog.query.filter_by(task_id=id).order_by(ActivityLog.timestamp.desc()).limit(10).all()
    
    # Get task comments
    comments = TaskComment.query.filter_by(task_id=id).order_by(TaskComment.created_at.desc()).all()
    
    return render_template('tasks/view_task.html', task=task, activity_logs=activity_logs, comments=comments)


@tasks_bp.route('/<int:id>/comments', methods=['POST'])
def add_task_comment(id):
    from services.task_service import TaskService
    
    firm_id = get_session_firm_id()
    user_id = get_session_user_id()
    comment_text = request.form.get('comment', '').strip()
    
    result = TaskService.add_task_comment(id, firm_id, comment_text, user_id)
    
    if result['success']:
        return jsonify({
            'success': True,
            'comment': result['comment']
        })
    else:
        status_code = 403 if 'access' in result['message'].lower() else 400
        return jsonify({
            'success': False,
            'message': result['message']
        }), status_code


@tasks_bp.route('/<int:id>/log-time', methods=['POST'])
def log_time(id):
    firm_id = get_session_firm_id()
    
    # Get task with access check using service layer
    task = TaskService.get_task_by_id_with_access_check(id, firm_id)
    if not task:
        return jsonify({'success': False, 'message': 'Task not found or access denied'}), 403
    
    try:
        data = request.get_json()
        hours = float(data.get('hours', 0))
        
        if hours <= 0:
            return jsonify({'success': False, 'message': 'Hours must be greater than 0'})
        
        # Add to existing actual hours
        task.actual_hours = (task.actual_hours or 0) + hours
        
        # Create activity log
        create_activity_log(
            f'Logged {hours}h on task "{task.title}" (Total: {task.actual_hours}h)',
            get_session_user_id(),
            task.project_id if task.project_id else None,
            task.id
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'total_hours': task.actual_hours,
            'logged_hours': hours
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@tasks_bp.route('/bulk-update', methods=['POST'])
def bulk_update_tasks():
    data = request.get_json()
    task_ids = data.get('task_ids', [])
    firm_id = get_session_firm_id()
    user_id = get_session_user_id()
    
    # Extract updates from request data
    updates = {}
    if 'status' in data:
        updates['status'] = data['status']
    if 'assignee_id' in data:
        updates['assignee_id'] = data['assignee_id']
    if 'priority' in data:
        updates['priority'] = data['priority']
    
    # Use service layer for bulk update business logic
    result = TaskService.bulk_update_tasks(
        task_ids=task_ids,
        updates=updates,
        firm_id=firm_id,
        user_id=user_id
    )
    
    return jsonify(result)


@tasks_bp.route('/bulk-delete', methods=['POST'])
def bulk_delete_tasks():
    data = request.get_json()
    task_ids = data.get('task_ids', [])
    firm_id = get_session_firm_id()
    user_id = get_session_user_id()
    
    # Use service layer for bulk delete business logic
    result = TaskService.bulk_delete_tasks(
        task_ids=task_ids,
        firm_id=firm_id,
        user_id=user_id
    )
    
    return jsonify(result)


@tasks_bp.route('/<int:id>/update', methods=['POST'])
def update_task(id):
    firm_id = get_session_firm_id()
    
    # Get task with access check using service layer
    task = TaskService.get_task_by_id_with_access_check(id, firm_id)
    if not task:
        return jsonify({'error': 'Task not found or access denied'}), 403
    
    old_status = task.status
    new_status = request.json.get('status')
    
    if new_status in ['Not Started', 'In Progress', 'Needs Review', 'Completed']:
        task.status = new_status
        
        # Handle sequential task dependencies
        TaskService._handle_sequential_dependencies(task, old_status, new_status)
        
        # Handle recurring task completion
        if new_status == 'Completed' and old_status != 'Completed':
            task.completed_at = datetime.utcnow()
            
            # If this is a recurring task, create next instance
            if task.is_recurring and task.is_recurring_master:
                task.last_completed = date.today()
                next_instance = task.create_next_instance()
                if next_instance:
                    db.session.add(next_instance)
                    create_activity_log(
                        f'Next instance of recurring task "{task.title}" created for {next_instance.due_date}',
                        get_session_user_id(),
                        task.project_id if task.project_id else None,
                        task.id
                    )
        
        db.session.commit()
        
        if old_status != new_status:
            create_activity_log(
                f'Task "{task.title}" status changed from "{old_status}" to "{new_status}"',
                get_session_user_id(),
                task.project_id if task.project_id else None,
                task.id
            )
        
        return jsonify({'success': True})
    
    return jsonify({'error': 'Invalid status'}), 400


@tasks_bp.route('/<int:id>/timer/start', methods=['POST'])
def start_timer(id):
    firm_id = get_session_firm_id()
    
    # Get task with access check using service layer
    task = TaskService.get_task_by_id_with_access_check(id, firm_id)
    if not task:
        return jsonify({'success': False, 'message': 'Task not found or access denied'}), 403
    
    if task.start_timer():
        db.session.commit()
        create_activity_log(f'Timer started for task "{task.title}"', get_session_user_id(), task.project_id, task.id)
        return jsonify({'success': True, 'message': 'Timer started'})
    else:
        return jsonify({'success': False, 'message': 'Timer already running'})


@tasks_bp.route('/<int:id>/timer/stop', methods=['POST'])
def stop_timer(id):
    firm_id = get_session_firm_id()
    
    # Get task with access check using service layer
    task = TaskService.get_task_by_id_with_access_check(id, firm_id)
    if not task:
        return jsonify({'success': False, 'message': 'Task not found or access denied'}), 403
    
    elapsed_hours = task.stop_timer()
    if elapsed_hours > 0:
        db.session.commit()
        create_activity_log(f'Timer stopped for task "{task.title}" - {elapsed_hours:.2f}h logged', get_session_user_id(), task.project_id, task.id)
        return jsonify({
            'success': True, 
            'message': f'Timer stopped - {elapsed_hours:.2f}h logged',
            'elapsed_hours': elapsed_hours,
            'total_hours': task.actual_hours
        })
    else:
        return jsonify({'success': False, 'message': 'No timer running'})


@tasks_bp.route('/<int:id>/timer/status', methods=['GET'])
def timer_status(id):
    firm_id = get_session_firm_id()
    
    # Get task with access check using service layer
    task = TaskService.get_task_by_id_with_access_check(id, firm_id)
    if not task:
        return jsonify({'success': False, 'message': 'Task not found or access denied'}), 403
    
    return jsonify({
        'timer_running': task.timer_running,
        'current_duration': task.current_timer_duration,
        'total_hours': task.actual_hours or 0,
        'billable_amount': task.billable_amount
    })
