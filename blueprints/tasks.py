"""
Task management blueprint
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime, date, timedelta
from core import db
from models import Task, Project, User, Client, Template, ActivityLog, TaskComment, WorkType, TaskStatus
from utils import create_activity_log

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')


@tasks_bp.route('/')
def list_tasks():
    firm_id = session['firm_id']
    
    # Get filter parameters - support multiple values
    status_filters = request.args.getlist('status')
    priority_filters = request.args.getlist('priority')
    assignee_filters = request.args.getlist('assignee')
    project_filters = request.args.getlist('project')
    overdue_filter = request.args.get('overdue')
    due_date_filter = request.args.get('due_date')
    show_completed = request.args.get('show_completed', 'false').lower() == 'true'
    
    # Base query - include both project tasks and independent tasks
    query = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        )
    )
    
    # Hide completed tasks by default
    if not show_completed:
        query = query.filter(Task.status != 'completed')
    
    # Apply multi-select filters
    if status_filters:
        query = query.filter(Task.status.in_(status_filters))
    
    if priority_filters:
        query = query.filter(Task.priority.in_(priority_filters))
    
    if assignee_filters:
        # Handle both assigned users and unassigned tasks
        assignee_conditions = []
        if 'unassigned' in assignee_filters:
            assignee_conditions.append(Task.assignee_id.is_(None))
        
        user_ids = [f for f in assignee_filters if f != 'unassigned']
        if user_ids:
            assignee_conditions.append(Task.assignee_id.in_(user_ids))
        
        if assignee_conditions:
            query = query.filter(db.or_(*assignee_conditions))
    
    if project_filters:
        # Handle both project tasks and independent tasks
        project_conditions = []
        if 'independent' in project_filters:
            project_conditions.append(Task.project_id.is_(None))
        
        project_ids = [f for f in project_filters if f != 'independent']
        if project_ids:
            project_conditions.append(Task.project_id.in_(project_ids))
        
        if project_conditions:
            query = query.filter(db.or_(*project_conditions))
    
    # Date-based filters
    today = date.today()
    if overdue_filter == 'true':
        # Exclude completed tasks and tasks from completed projects
        query = query.filter(
            Task.due_date < today, 
            Task.status != 'Completed',
            db.or_(
                Task.project_id.is_(None),  # Independent tasks
                Project.status != 'Completed'  # Tasks from non-completed projects
            )
        )
    elif due_date_filter == 'today':
        query = query.filter(Task.due_date == today)
    elif due_date_filter == 'soon':
        # Due within next 3 days
        soon_date = today + timedelta(days=3)
        query = query.filter(Task.due_date.between(today, soon_date))
    
    # Get all tasks first
    all_tasks = query.order_by(
        Task.due_date.asc().nullslast(),
        db.case(
            (Task.priority == 'High', 1),
            (Task.priority == 'Medium', 2),
            (Task.priority == 'Low', 3),
            else_=4
        )
    ).all()
    
    # Filter to show only current active task per interdependent project
    tasks = []
    seen_projects = set()
    
    for task in all_tasks:
        if task.project and task.project.task_dependency_mode:
            # For interdependent projects, only show the first active task per project
            if task.project_id not in seen_projects and not task.is_completed:
                tasks.append(task)
                seen_projects.add(task.project_id)
        else:
            # For independent tasks or non-interdependent projects, show all tasks
            tasks.append(task)
    
    # Get filter options
    users = User.query.filter_by(firm_id=firm_id).all()
    projects = Project.query.filter_by(firm_id=firm_id).all()
    
    return render_template('tasks/tasks_modern.html', tasks=tasks, users=users, projects=projects, today=date.today())


@tasks_bp.route('/<int:id>/delete', methods=['POST'])
def delete_task(id):
    task = Task.query.get_or_404(id)
    
    # Check access for both project tasks and independent tasks
    if task.project and task.project.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    elif not task.project and task.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        task_title = task.title
        project_id = task.project_id
        
        # Create activity log before deletion
        if project_id:
            create_activity_log(f'Task "{task_title}" deleted', session['user_id'], project_id)
        else:
            create_activity_log(f'Independent task "{task_title}" deleted', session['user_id'])
        
        # Delete associated comments first
        TaskComment.query.filter_by(task_id=id).delete()
        
        # Delete the task
        db.session.delete(task)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Task deleted successfully'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


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