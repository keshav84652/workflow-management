"""
Task management blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime, date, timedelta
from core import db
from models import Task, Project, User, Client, Template, ActivityLog, TaskComment, WorkType, TaskStatus
from utils import create_activity_log

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')


def handle_sequential_task_dependencies(task, old_status, new_status):
    """Handle sequential task dependencies when task status changes"""
    if not task.project_id or not task.project:
        return
    
    # Check if project has task dependency mode enabled
    if not task.project.task_dependency_mode:
        return
    
    # Get all tasks in the project ordered by creation/position
    project_tasks = Task.query.filter_by(project_id=task.project_id).order_by(Task.id.asc()).all()
    
    # Find current task position
    current_task_index = None
    for i, t in enumerate(project_tasks):
        if t.id == task.id:
            current_task_index = i
            break
    
    if current_task_index is None:
        return
    
    # If task is marked as completed
    if new_status == 'Completed' and old_status != 'Completed':
        # Mark all previous tasks as completed
        for i in range(current_task_index):
            prev_task = project_tasks[i]
            if prev_task.status != 'Completed':
                prev_task.status = 'Completed'
                create_activity_log(
                    f'Task "{prev_task.title}" auto-completed due to sequential dependency',
                    session.get('user_id', 1),
                    task.project_id,
                    prev_task.id
                )
    
    # If task is marked as not started or in progress
    elif new_status in ['Not Started', 'In Progress'] and old_status == 'Completed':
        # Mark all subsequent tasks as not started
        for i in range(current_task_index + 1, len(project_tasks)):
            next_task = project_tasks[i]
            if next_task.status == 'Completed':
                next_task.status = 'Not Started'
                create_activity_log(
                    f'Task "{next_task.title}" reset due to sequential dependency',
                    session.get('user_id', 1),
                    task.project_id,
                    next_task.id
                )


@tasks_bp.route('/')
def list_tasks():
    from services.task_service import TaskService
    
    firm_id = session['firm_id']
    
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
    
    firm_id = session['firm_id']
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
        firm_id = session['firm_id']
        
        # Get form data
        title = request.form.get('title')
        description = request.form.get('description')
        project_id = request.form.get('project_id')
        assignee_id = request.form.get('assignee_id')
        priority = request.form.get('priority', 'Medium')
        due_date = request.form.get('due_date')
        estimated_hours = request.form.get('estimated_hours')
        
        # Recurring task options
        is_recurring = request.form.get('is_recurring') == 'on'
        recurrence_rule = request.form.get('recurrence_rule')
        recurrence_interval = request.form.get('recurrence_interval')
        
        # Convert due_date
        due_date_obj = None
        if due_date:
            due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
        
        # Convert estimated_hours
        estimated_hours_float = None
        if estimated_hours:
            try:
                estimated_hours_float = float(estimated_hours)
            except ValueError:
                pass
        
        # Verify project belongs to firm (if project selected)
        if project_id:
            project = Project.query.filter_by(id=project_id, firm_id=firm_id).first()
            if not project:
                flash('Invalid project selected', 'error')
                return redirect(url_for('tasks.create_task'))
        
        # Convert recurrence interval
        recurrence_interval_int = None
        if is_recurring and recurrence_interval:
            try:
                recurrence_interval_int = int(recurrence_interval)
            except ValueError:
                recurrence_interval_int = 1
        
        # Create task
        task = Task(
            title=title,
            description=description,
            due_date=due_date_obj,
            priority=priority,
            estimated_hours=estimated_hours_float,
            project_id=project_id if project_id else None,
            firm_id=firm_id,
            assignee_id=assignee_id if assignee_id else None,
            is_recurring=is_recurring,
            recurrence_rule=recurrence_rule if is_recurring else None,
            recurrence_interval=recurrence_interval_int if is_recurring else None
        )
        
        # Calculate next due date for recurring tasks after object creation
        if is_recurring:
            task.next_due_date = task.calculate_next_due_date()
            
            # Create the first upcoming instance immediately
            next_instance = task.create_next_instance()
            if next_instance:
                db.session.add(next_instance)
        
        db.session.add(task)
        db.session.commit()
        
        # Activity log
        if project_id:
            create_activity_log(f'Task "{task.title}" created', session['user_id'], project_id, task.id)
        else:
            create_activity_log(f'Independent task "{task.title}" created', session['user_id'], None, task.id)
        
        flash('Task created successfully!', 'success')
        return redirect(url_for('tasks.list_tasks'))
    
    # GET request - show form
    firm_id = session['firm_id']
    projects = Project.query.filter_by(firm_id=firm_id, status='Active').all()
    users = User.query.filter_by(firm_id=firm_id).all()
    
    # Pre-select project if provided
    selected_project = request.args.get('project_id')
    
    # Pre-fill due date if provided (from calendar click)
    prefill_due_date = request.args.get('due_date')
    
    return render_template('tasks/create_task.html', projects=projects, users=users, selected_project=selected_project, prefill_due_date=prefill_due_date)


@tasks_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit_task(id):
    task = Task.query.get_or_404(id)
    # Check access for both project tasks and independent tasks
    if task.project and task.project.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('tasks.list_tasks'))
    elif not task.project and task.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('tasks.list_tasks'))
    
    if request.method == 'POST':
        # Track original values for change detection
        original_assignee_id = task.assignee_id
        original_assignee_name = task.assignee.name if task.assignee else 'Unassigned'
        original_status = task.status
        
        # Get form data
        task.title = request.form.get('title')
        task.description = request.form.get('description')
        assignee_id = request.form.get('assignee_id')
        new_assignee_id = assignee_id if assignee_id else None
        task.assignee_id = new_assignee_id
        task.priority = request.form.get('priority', 'Medium')
        new_status = request.form.get('status', task.status)
        task.status = new_status
        
        # Handle sequential task dependencies before committing
        handle_sequential_task_dependencies(task, original_status, new_status)
        
        # Handle due date
        due_date = request.form.get('due_date')
        if due_date:
            task.due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
        else:
            task.due_date = None
        
        # Handle estimated hours
        estimated_hours = request.form.get('estimated_hours')
        if estimated_hours:
            try:
                task.estimated_hours = float(estimated_hours)
            except ValueError:
                task.estimated_hours = None
        else:
            task.estimated_hours = None
        
        # Handle comments
        comments = request.form.get('comments')
        if comments:
            task.comments = comments
        
        # Handle dependencies (only for project tasks)
        if task.project_id:
            dependencies = request.form.getlist('dependencies')
            if dependencies:
                # Validate dependencies - ensure no circular dependencies
                valid_dependencies = []
                for dep_id in dependencies:
                    try:
                        dep_id = int(dep_id)
                        dep_task = Task.query.filter_by(id=dep_id, project_id=task.project_id).first()
                        if dep_task and dep_id != task.id:
                            # Check for circular dependency - simple check for now
                            valid_dependencies.append(str(dep_id))
                    except ValueError:
                        pass
                task.dependencies = ','.join(valid_dependencies) if valid_dependencies else None
            else:
                task.dependencies = None
        
        db.session.commit()
        
        # Log assignee change if it occurred
        if original_assignee_id != new_assignee_id:
            new_assignee_name = task.assignee.name if task.assignee else 'Unassigned'
            assignee_log_msg = f'Task "{task.title}" assignee changed from "{original_assignee_name}" to "{new_assignee_name}"'
            if task.project_id:
                create_activity_log(assignee_log_msg, session['user_id'], task.project_id, task.id)
            else:
                create_activity_log(assignee_log_msg, session['user_id'], None, task.id)
        
        # General activity log
        if task.project_id:
            create_activity_log(f'Task "{task.title}" updated', session['user_id'], task.project_id, task.id)
        else:
            create_activity_log(f'Independent task "{task.title}" updated', session['user_id'], None, task.id)
        
        flash('Task updated successfully!', 'success')
        return redirect(url_for('tasks.view_task', id=task.id))
    
    # GET request - show form
    firm_id = session['firm_id']
    users = User.query.filter_by(firm_id=firm_id).all()
    
    # Get other tasks in the same project for dependency selection
    project_tasks = []
    if task.project_id:
        project_tasks = Task.query.filter_by(project_id=task.project_id).order_by(Task.title).all()
    
    return render_template('tasks/edit_task.html', task=task, users=users, project_tasks=project_tasks)


@tasks_bp.route('/<int:id>')
def view_task(id):
    task = Task.query.get_or_404(id)
    # Check access for both project tasks and independent tasks
    if task.project and task.project.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('tasks.list_tasks'))
    elif not task.project and task.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('tasks.list_tasks'))
    
    # Get task activity logs
    activity_logs = ActivityLog.query.filter_by(task_id=id).order_by(ActivityLog.timestamp.desc()).limit(10).all()
    
    # Get task comments
    comments = TaskComment.query.filter_by(task_id=id).order_by(TaskComment.created_at.desc()).all()
    
    return render_template('tasks/view_task.html', task=task, activity_logs=activity_logs, comments=comments)


@tasks_bp.route('/<int:id>/comments', methods=['POST'])
def add_task_comment(id):
    from services.task_service import TaskService
    
    firm_id = session['firm_id']
    user_id = session['user_id']
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
    task = Task.query.get_or_404(id)
    # Check access for both project tasks and independent tasks
    if task.project and task.project.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    elif not task.project and task.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
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
            session['user_id'],
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
    firm_id = session['firm_id']
    
    if not task_ids:
        return jsonify({'success': False, 'message': 'No tasks selected'})
    
    try:
        # Get tasks that belong to the firm
        tasks = Task.query.outerjoin(Project).filter(
            Task.id.in_(task_ids),
            db.or_(
                Project.firm_id == firm_id,
                db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            )
        ).all()
        
        if not tasks:
            return jsonify({'success': False, 'message': 'No valid tasks found'})
        
        updated_count = 0
        for task in tasks:
            # Update status if provided
            if 'status' in data:
                old_status = task.status
                task.status = data['status']
                if old_status != task.status:
                    # Log status change
                    create_activity_log(
                        f'Task "{task.title}" status changed from "{old_status}" to "{task.status}" (bulk update)',
                        session['user_id'],
                        task.project_id if task.project_id else None,
                        task.id
                    )
            
            # Update assignee if provided
            if 'assignee_id' in data:
                old_assignee_name = task.assignee.name if task.assignee else 'Unassigned'
                task.assignee_id = data['assignee_id'] if data['assignee_id'] else None
                new_assignee_name = task.assignee.name if task.assignee else 'Unassigned'
                if old_assignee_name != new_assignee_name:
                    # Log assignee change
                    create_activity_log(
                        f'Task "{task.title}" assignee changed from "{old_assignee_name}" to "{new_assignee_name}" (bulk update)',
                        session['user_id'],
                        task.project_id if task.project_id else None,
                        task.id
                    )
            
            # Update priority if provided
            if 'priority' in data:
                old_priority = task.priority
                task.priority = data['priority']
                if old_priority != task.priority:
                    # Log priority change
                    create_activity_log(
                        f'Task "{task.title}" priority changed from "{old_priority}" to "{task.priority}" (bulk update)',
                        session['user_id'],
                        task.project_id if task.project_id else None,
                        task.id
                    )
            
            updated_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Successfully updated {updated_count} tasks'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@tasks_bp.route('/bulk-delete', methods=['POST'])
def bulk_delete_tasks():
    data = request.get_json()
    task_ids = data.get('task_ids', [])
    firm_id = session['firm_id']
    
    if not task_ids:
        return jsonify({'success': False, 'message': 'No tasks selected'})
    
    try:
        # Get tasks that belong to the firm
        tasks = Task.query.outerjoin(Project).filter(
            Task.id.in_(task_ids),
            db.or_(
                Project.firm_id == firm_id,
                db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            )
        ).all()
        
        if not tasks:
            return jsonify({'success': False, 'message': 'No valid tasks found'})
        
        deleted_count = 0
        for task in tasks:
            # Log deletion
            create_activity_log(
                f'Task "{task.title}" deleted (bulk operation)',
                session['user_id'],
                task.project_id if task.project_id else None,
                None  # task_id will be None since task is being deleted
            )
            
            # Delete associated comments first
            TaskComment.query.filter_by(task_id=task.id).delete()
            
            # Delete the task
            db.session.delete(task)
            deleted_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Successfully deleted {deleted_count} tasks'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@tasks_bp.route('/<int:id>/update', methods=['POST'])
def update_task(id):
    task = Task.query.get_or_404(id)
    # Check access for both project tasks and independent tasks
    if task.project and task.project.firm_id != session['firm_id']:
        return jsonify({'error': 'Access denied'}), 403
    elif not task.project and task.firm_id != session['firm_id']:
        return jsonify({'error': 'Access denied'}), 403
    
    old_status = task.status
    new_status = request.json.get('status')
    
    if new_status in ['Not Started', 'In Progress', 'Needs Review', 'Completed']:
        task.status = new_status
        
        # Handle sequential task dependencies
        handle_sequential_task_dependencies(task, old_status, new_status)
        
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
                        session.get('user_id', 1),
                        task.project_id if task.project_id else None,
                        task.id
                    )
        
        db.session.commit()
        
        if old_status != new_status:
            create_activity_log(
                f'Task "{task.title}" status changed from "{old_status}" to "{new_status}"',
                session.get('user_id', 1),
                task.project_id if task.project_id else None,
                task.id
            )
        
        return jsonify({'success': True})
    
    return jsonify({'error': 'Invalid status'}), 400


@tasks_bp.route('/<int:id>/timer/start', methods=['POST'])
def start_timer(id):
    task = Task.query.get_or_404(id)
    # Check access
    if task.project and task.project.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    elif not task.project and task.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    if task.start_timer():
        db.session.commit()
        create_activity_log(f'Timer started for task "{task.title}"', session['user_id'], task.project_id, task.id)
        return jsonify({'success': True, 'message': 'Timer started'})
    else:
        return jsonify({'success': False, 'message': 'Timer already running'})


@tasks_bp.route('/<int:id>/timer/stop', methods=['POST'])
def stop_timer(id):
    task = Task.query.get_or_404(id)
    # Check access
    if task.project and task.project.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    elif not task.project and task.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    elapsed_hours = task.stop_timer()
    if elapsed_hours > 0:
        db.session.commit()
        create_activity_log(f'Timer stopped for task "{task.title}" - {elapsed_hours:.2f}h logged', session['user_id'], task.project_id, task.id)
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
    task = Task.query.get_or_404(id)
    # Check access
    if task.project and task.project.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    elif not task.project and task.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    return jsonify({
        'timer_running': task.timer_running,
        'current_duration': task.current_timer_duration,
        'total_hours': task.actual_hours or 0,
        'billable_amount': task.billable_amount
    })
