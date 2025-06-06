from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
import os
import secrets
import calendar
from dateutil.relativedelta import relativedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.abspath("instance/workflow.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

os.makedirs('instance', exist_ok=True)

from models import db, Firm, User, Template, TemplateTask, Project, Task, ActivityLog, Client, TaskComment, WorkType, TaskStatus, Contact, ClientContact, RecurringTask

db.init_app(app)
from utils import generate_access_code, create_activity_log, process_recurring_tasks, calculate_next_due_date, calculate_task_due_date, find_or_create_client

# Process recurring tasks on startup (in a real deployment, this would be handled by a cron job)
@app.before_first_request
def startup_tasks():
    try:
        process_recurring_tasks()
    except Exception as e:
        print(f"Failed to process recurring tasks on startup: {e}")

def would_create_circular_dependency(task_id, dependency_id):
    """Check if adding dependency_id as a dependency of task_id would create a circular dependency"""
    def has_path(from_id, to_id, visited=None):
        if visited is None:
            visited = set()
        
        if from_id == to_id:
            return True
        
        if from_id in visited:
            return False
        
        visited.add(from_id)
        
        # Get all tasks that depend on from_id
        dependent_tasks = Task.query.filter(Task.dependencies.like(f'%{from_id}%')).all()
        
        for dependent_task in dependent_tasks:
            if dependent_task.id in dependent_task.dependency_list:  # Safety check
                continue
            if has_path(dependent_task.id, to_id, visited.copy()):
                return True
        
        return False
    
    # Check if dependency_id already depends on task_id (would create cycle)
    return has_path(dependency_id, task_id)

def check_and_update_project_completion(project_id):
    """Check if all tasks in a project are completed and update project status accordingly"""
    if not project_id:
        return
    
    project = Project.query.get(project_id)
    if not project:
        return
    
    # Count total tasks and completed tasks
    total_tasks = Task.query.filter_by(project_id=project_id).count()
    completed_tasks = Task.query.filter_by(project_id=project_id, status='Completed').count()
    
    # If all tasks are completed, mark project as completed
    if total_tasks > 0 and completed_tasks == total_tasks and project.status != 'Completed':
        project.status = 'Completed'
        create_activity_log(
            f'Project "{project.name}" automatically marked as completed (all tasks finished)',
            session.get('user_id', 1),
            project_id
        )
    # If project was marked completed but has incomplete tasks, reactivate it
    elif project.status == 'Completed' and completed_tasks < total_tasks:
        project.status = 'Active'
        create_activity_log(
            f'Project "{project.name}" reactivated (incomplete tasks detected)',
            session.get('user_id', 1),
            project_id
        )

# Database initialization handled by init_db.py

@app.before_request
def check_access():
    # Skip authentication for public endpoints
    if request.endpoint in ['static', 'admin_login', 'admin_dashboard', 'generate_access_code_route', 'admin_authenticate']:
        return
    
    # Skip for login flow
    if request.endpoint in ['login', 'authenticate', 'select_user', 'set_user']:
        return
    
    # Check firm access
    if 'firm_id' not in session:
        return redirect(url_for('login'))
    
    # Check user selection (except for user selection pages)
    if 'user_id' not in session:
        return redirect(url_for('select_user'))

@app.route('/')
def login():
    if 'firm_id' in session:
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('select_user'))
    return render_template('login.html')

@app.route('/authenticate', methods=['POST'])
def authenticate():
    access_code = request.form.get('access_code', '').strip()
    firm = Firm.query.filter_by(access_code=access_code, is_active=True).first()
    
    if firm:
        session['firm_id'] = firm.id
        session['firm_name'] = firm.name
        return redirect(url_for('select_user'))
    else:
        flash('Invalid access code', 'error')
        return redirect(url_for('login'))

@app.route('/select-user')
def select_user():
    if 'firm_id' not in session:
        return redirect(url_for('login'))
    
    firm_id = session['firm_id']
    users = User.query.filter_by(firm_id=firm_id).all()
    return render_template('select_user.html', users=users)

@app.route('/set-user', methods=['POST'])
def set_user():
    if 'firm_id' not in session:
        return redirect(url_for('login'))
    
    user_id = request.form.get('user_id')
    user = User.query.filter_by(id=user_id, firm_id=session['firm_id']).first()
    
    if user:
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_role'] = user.role
        flash(f'Welcome, {user.name}!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid user selection', 'error')
        return redirect(url_for('select_user'))

@app.route('/switch-user')
def switch_user():
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_role', None)
    return redirect(url_for('select_user'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    firm_id = session['firm_id']
    projects = Project.query.filter_by(firm_id=firm_id, status='Active').all()
    
    # Basic counts - include both project tasks and independent tasks
    total_tasks = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        )
    ).count()
    
    # Count completed tasks using new status system
    completed_tasks = Task.query.outerjoin(Project).outerjoin(TaskStatus).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        ),
        db.or_(
            TaskStatus.is_terminal == True,  # New status system
            db.and_(Task.status_id.is_(None), Task.status == 'Completed')  # Legacy fallback
        )
    ).count()
    
    # Count overdue tasks (exclude completed)
    overdue_tasks = Task.query.outerjoin(Project).outerjoin(TaskStatus).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        ),
        Task.due_date < date.today(),
        db.or_(
            TaskStatus.is_terminal == False,  # New status system
            db.and_(Task.status_id.is_(None), Task.status != 'Completed')  # Legacy fallback
        )
    ).count()
    
    active_clients = Client.query.filter_by(firm_id=firm_id, is_active=True).count()
    
    # Get work types for enhanced dashboard
    work_types = WorkType.query.filter_by(firm_id=firm_id, is_active=True).all()
    
    # Task status distribution by work type
    work_type_status_data = {}
    for work_type in work_types:
        work_type_data = {
            'name': work_type.name,
            'color': work_type.color,
            'statuses': {}
        }
        
        for status in work_type.task_statuses:
            # Count tasks with this specific status
            count = Task.query.join(Project).filter(
                Project.firm_id == firm_id,
                Project.work_type_id == work_type.id,
                Task.status_id == status.id
            ).count()
            work_type_data['statuses'][status.name] = {
                'count': count,
                'color': status.color,
                'is_terminal': status.is_terminal
            }
        
        work_type_status_data[work_type.name] = work_type_data
    
    # Legacy status distribution for backward compatibility
    task_status_data = {}
    for status in ['Not Started', 'In Progress', 'Needs Review', 'Completed']:
        count = Task.query.outerjoin(Project).filter(
            db.or_(
                Project.firm_id == firm_id,
                db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            ),
            Task.status == status
        ).count()
        task_status_data[status] = count
    
    # Priority distribution (exclude completed tasks)
    priority_data = {}
    for priority in ['High', 'Medium', 'Low']:
        count = Task.query.outerjoin(Project).outerjoin(TaskStatus).filter(
            db.or_(
                Project.firm_id == firm_id,
                db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            ),
            Task.priority == priority,
            db.or_(
                TaskStatus.is_terminal == False,  # New status system
                db.and_(Task.status_id.is_(None), Task.status != 'Completed')  # Legacy fallback
            )
        ).count()
        priority_data[priority] = count
    
    # Recent activity (last 7 days)
    week_ago = datetime.now() - timedelta(days=7)
    recent_tasks = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        ),
        Task.created_at >= week_ago
    ).count()
    
    # Workload by user - include both project tasks and independent tasks
    user_workload = {}
    users = User.query.filter_by(firm_id=firm_id).all()
    for user in users:
        active_tasks = Task.query.outerjoin(Project).outerjoin(TaskStatus).filter(
            db.or_(
                Project.firm_id == firm_id,
                db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            ),
            Task.assignee_id == user.id,
            db.or_(
                TaskStatus.is_terminal == False,  # New status system
                db.and_(Task.status_id.is_(None), Task.status.in_(['Not Started', 'In Progress', 'Needs Review']))  # Legacy fallback
            )
        ).count()
        user_workload[user.name] = active_tasks
    
    # Upcoming deadlines (next 7 days) - include both project tasks and independent tasks
    next_week = date.today() + timedelta(days=7)
    upcoming_tasks = Task.query.outerjoin(Project).outerjoin(TaskStatus).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        ),
        Task.due_date.between(date.today(), next_week),
        db.or_(
            TaskStatus.is_terminal == False,  # New status system
            db.and_(Task.status_id.is_(None), Task.status != 'Completed')  # Legacy fallback
        )
    ).order_by(Task.due_date.asc()).limit(5).all()
    
    # Critical notifications - overdue and due today
    today_tasks = Task.query.outerjoin(Project).outerjoin(TaskStatus).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        ),
        Task.due_date == date.today(),
        db.or_(
            TaskStatus.is_terminal == False,  # New status system
            db.and_(Task.status_id.is_(None), Task.status != 'Completed')  # Legacy fallback
        )
    ).count()
    
    # Due this week count
    due_this_week = Task.query.outerjoin(Project).outerjoin(TaskStatus).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        ),
        Task.due_date.between(date.today(), next_week),
        db.or_(
            TaskStatus.is_terminal == False,  # New status system
            db.and_(Task.status_id.is_(None), Task.status != 'Completed')  # Legacy fallback
        )
    ).count()
    
    return render_template('dashboard.html', 
                         projects=projects, 
                         total_tasks=total_tasks,
                         completed_tasks=completed_tasks,
                         overdue_tasks=overdue_tasks,
                         active_clients=active_clients,
                         task_status_data=task_status_data,
                         work_type_status_data=work_type_status_data,
                         work_types=work_types,
                         priority_data=priority_data,
                         recent_tasks=recent_tasks,
                         user_workload=user_workload,
                         upcoming_tasks=upcoming_tasks,
                         today_tasks=today_tasks,
                         due_this_week=due_this_week)

@app.route('/admin')
def admin_login():
    return render_template('admin_login.html')

@app.route('/admin/authenticate', methods=['POST'])
def admin_authenticate():
    password = request.form.get('password')
    if password == os.environ.get('ADMIN_PASSWORD', 'admin123'):
        session['admin'] = True
        return redirect(url_for('admin_dashboard'))
    else:
        flash('Invalid admin password', 'error')
        return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    firms = Firm.query.all()
    return render_template('admin_dashboard.html', firms=firms)

@app.route('/admin/generate-code', methods=['POST'])
def generate_access_code_route():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    firm_name = request.form.get('firm_name')
    access_code = generate_access_code()
    
    firm = Firm(name=firm_name, access_code=access_code)
    db.session.add(firm)
    db.session.commit()
    
    flash(f'Access code generated: {access_code}', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/templates')
def templates():
    firm_id = session['firm_id']
    templates = Template.query.filter_by(firm_id=firm_id).all()
    return render_template('templates.html', templates=templates)

@app.route('/templates/create', methods=['GET', 'POST'])
def create_template():
    if request.method == 'POST':
        firm_id = session['firm_id']
        
        template = Template(
            name=request.form.get('name'),
            description=request.form.get('description'),
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
        flash('Template created successfully!', 'success')
        return redirect(url_for('templates'))
    
    return render_template('create_template.html')

@app.route('/templates/<int:id>/edit', methods=['GET', 'POST'])
def edit_template(id):
    template = Template.query.get_or_404(id)
    if template.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('templates'))
    
    if request.method == 'POST':
        template.name = request.form.get('name')
        template.description = request.form.get('description')
        
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
        flash('Template updated successfully!', 'success')
        return redirect(url_for('templates'))
    
    return render_template('edit_template.html', template=template)

@app.route('/projects')
def projects():
    firm_id = session['firm_id']
    projects = Project.query.filter_by(firm_id=firm_id).all()
    return render_template('projects.html', projects=projects)

@app.route('/projects/create', methods=['GET', 'POST'])
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
        
        # Find or create client
        client = find_or_create_client(client_name, firm_id)
        
        # Check if this was a new client
        was_new_client = client.email is None
        
        # Get template to access work type
        template = Template.query.get(template_id)
        
        project = Project(
            name=project_name or f"{client.name} - {template.name}",
            client_id=client.id,
            work_type_id=template.work_type_id,  # Inherit work type from template
            start_date=start_date,
            due_date=due_date,
            priority=priority,
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
        return redirect(url_for('view_project', id=project.id))
    
    firm_id = session['firm_id']
    templates = Template.query.filter_by(firm_id=firm_id).all()
    clients = Client.query.filter_by(firm_id=firm_id, is_active=True).all()
    return render_template('create_project.html', templates=templates, clients=clients)

@app.route('/projects/<int:id>')
def view_project(id):
    project = Project.query.get_or_404(id)
    if project.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('projects'))
    
    tasks = Task.query.filter_by(project_id=id).order_by(Task.due_date.asc()).all()
    activity_logs = ActivityLog.query.filter_by(project_id=id).order_by(ActivityLog.timestamp.desc()).limit(10).all()
    
    return render_template('view_project.html', project=project, tasks=tasks, activity_logs=activity_logs)

@app.route('/projects/<int:id>/edit', methods=['GET', 'POST'])
def edit_project(id):
    project = Project.query.get_or_404(id)
    if project.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('projects'))
    
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
        return redirect(url_for('view_project', id=project.id))
    
    # GET request - show form
    firm_id = session['firm_id']
    users = User.query.filter_by(firm_id=firm_id).all()
    return render_template('edit_project.html', project=project, users=users)

@app.route('/tasks')
def tasks():
    firm_id = session['firm_id']
    
    # Get filter parameters - support multiple values
    status_filters = request.args.getlist('status')
    priority_filters = request.args.getlist('priority')
    assignee_filters = request.args.getlist('assignee')
    project_filters = request.args.getlist('project')
    overdue_filter = request.args.get('overdue')
    due_date_filter = request.args.get('due_date')
    
    # Base query - include both project tasks and independent tasks
    query = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        )
    )
    
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
        query = query.filter(Task.due_date < today, Task.status != 'Completed')
    elif due_date_filter == 'today':
        query = query.filter(Task.due_date == today)
    elif due_date_filter == 'soon':
        # Due within next 3 days
        soon_date = today + timedelta(days=3)
        query = query.filter(Task.due_date.between(today, soon_date))
    
    # Order by due date (nulls last) and priority
    tasks = query.order_by(
        Task.due_date.asc().nullslast(),
        db.case(
            (Task.priority == 'High', 1),
            (Task.priority == 'Medium', 2),
            (Task.priority == 'Low', 3),
            else_=4
        )
    ).all()
    
    # Get filter options
    users = User.query.filter_by(firm_id=firm_id).all()
    projects = Project.query.filter_by(firm_id=firm_id).all()
    
    return render_template('tasks.html', tasks=tasks, users=users, projects=projects)

@app.route('/tasks/<int:id>/delete', methods=['POST'])
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

@app.route('/tasks/create', methods=['GET', 'POST'])
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
                return redirect(url_for('create_task'))
        
        # Create task
        task = Task(
            title=title,
            description=description,
            due_date=due_date_obj,
            priority=priority,
            estimated_hours=estimated_hours_float,
            project_id=project_id if project_id else None,
            firm_id=firm_id,
            assignee_id=assignee_id if assignee_id else None
        )
        db.session.add(task)
        db.session.commit()
        
        # Activity log
        if project_id:
            create_activity_log(f'Task "{task.title}" created', session['user_id'], project_id, task.id)
        else:
            create_activity_log(f'Independent task "{task.title}" created', session['user_id'], None, task.id)
        
        flash('Task created successfully!', 'success')
        return redirect(url_for('tasks'))
    
    # GET request - show form
    firm_id = session['firm_id']
    projects = Project.query.filter_by(firm_id=firm_id, status='Active').all()
    users = User.query.filter_by(firm_id=firm_id).all()
    
    # Pre-select project if provided
    selected_project = request.args.get('project_id')
    
    # Pre-fill due date if provided (from calendar click)
    prefill_due_date = request.args.get('due_date')
    
    return render_template('create_task.html', projects=projects, users=users, selected_project=selected_project, prefill_due_date=prefill_due_date)

@app.route('/tasks/<int:id>/edit', methods=['GET', 'POST'])
def edit_task(id):
    task = Task.query.get_or_404(id)
    # Check access for both project tasks and independent tasks
    if task.project and task.project.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('tasks'))
    elif not task.project and task.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('tasks'))
    
    if request.method == 'POST':
        # Track original values for change detection
        original_assignee_id = task.assignee_id
        original_assignee_name = task.assignee.name if task.assignee else 'Unassigned'
        
        # Get form data
        task.title = request.form.get('title')
        task.description = request.form.get('description')
        assignee_id = request.form.get('assignee_id')
        new_assignee_id = assignee_id if assignee_id else None
        task.assignee_id = new_assignee_id
        task.priority = request.form.get('priority', 'Medium')
        task.status = request.form.get('status', task.status)
        
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
                            # Check for circular dependency
                            if not would_create_circular_dependency(task.id, dep_id):
                                valid_dependencies.append(str(dep_id))
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
        return redirect(url_for('view_task', id=task.id))
    
    # GET request - show form
    firm_id = session['firm_id']
    users = User.query.filter_by(firm_id=firm_id).all()
    
    # Get other tasks in the same project for dependency selection
    project_tasks = []
    if task.project_id:
        project_tasks = Task.query.filter_by(project_id=task.project_id).order_by(Task.title).all()
    
    return render_template('edit_task.html', task=task, users=users, project_tasks=project_tasks)

@app.route('/tasks/<int:id>')
def view_task(id):
    task = Task.query.get_or_404(id)
    # Check access for both project tasks and independent tasks
    if task.project and task.project.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('tasks'))
    elif not task.project and task.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('tasks'))
    
    # Get task activity logs
    activity_logs = ActivityLog.query.filter_by(task_id=id).order_by(ActivityLog.timestamp.desc()).limit(10).all()
    
    # Get task comments
    comments = TaskComment.query.filter_by(task_id=id).order_by(TaskComment.created_at.desc()).all()
    
    return render_template('view_task.html', task=task, activity_logs=activity_logs, comments=comments)

@app.route('/tasks/<int:id>/comments', methods=['POST'])
def add_task_comment(id):
    task = Task.query.get_or_404(id)
    # Check access for both project tasks and independent tasks
    if task.project and task.project.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    elif not task.project and task.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    comment_text = request.form.get('comment', '').strip()
    if not comment_text:
        return jsonify({'success': False, 'message': 'Comment cannot be empty'})
    
    try:
        # Create comment
        comment = TaskComment(
            comment=comment_text,
            task_id=task.id,
            user_id=session['user_id']
        )
        db.session.add(comment)
        
        # Create activity log
        create_activity_log(
            f'Comment added to task "{task.title}"',
            session['user_id'],
            task.project_id if task.project_id else None,
            task.id
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'comment': {
                'id': comment.id,
                'comment': comment.comment,
                'user_name': comment.user.name,
                'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/tasks/<int:id>/log-time', methods=['POST'])
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

@app.route('/tasks/bulk-update', methods=['POST'])
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
        
        # Check for project auto-completion for all affected projects
        affected_projects = set()
        for task in tasks:
            if task.project_id and 'status' in data:
                affected_projects.add(task.project_id)
        
        for project_id in affected_projects:
            check_and_update_project_completion(project_id)
        
        db.session.commit()  # Commit any project status changes
        
        return jsonify({
            'success': True, 
            'message': f'Successfully updated {updated_count} tasks'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/tasks/bulk-delete', methods=['POST'])
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

@app.route('/tasks/<int:id>/update', methods=['POST'])
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
        db.session.commit()
        
        if old_status != new_status:
            create_activity_log(
                f'Task "{task.title}" status changed from "{old_status}" to "{new_status}"',
                session.get('user_id', 1),
                task.project_id if task.project_id else None,
                task.id
            )
            
            # Check if project should be auto-completed
            if task.project_id:
                check_and_update_project_completion(task.project_id)
        
        return jsonify({'success': True})
    
    return jsonify({'error': 'Invalid status'}), 400

@app.route('/users')
def users():
    firm_id = session['firm_id']
    users = User.query.filter_by(firm_id=firm_id).all()
    return render_template('users.html', users=users)

@app.route('/users/create', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        firm_id = session['firm_id']
        
        user = User(
            name=request.form.get('name'),
            role=request.form.get('role', 'Member'),
            firm_id=firm_id
        )
        db.session.add(user)
        db.session.commit()
        
        flash('User created successfully!', 'success')
        return redirect(url_for('users'))
    
    return render_template('create_user.html')

@app.route('/clients')
def clients():
    firm_id = session['firm_id']
    clients = Client.query.filter_by(firm_id=firm_id).order_by(Client.name.asc()).all()
    return render_template('clients.html', clients=clients)

@app.route('/clients/create', methods=['GET', 'POST'])
def create_client():
    if request.method == 'POST':
        firm_id = session['firm_id']
        
        client = Client(
            name=request.form.get('name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            contact_person=request.form.get('contact_person'),
            entity_type=request.form.get('entity_type', 'Individual'),
            tax_id=request.form.get('tax_id'),
            notes=request.form.get('notes'),
            firm_id=firm_id
        )
        db.session.add(client)
        db.session.commit()
        
        # Activity log
        create_activity_log(f'Client "{client.name}" created', session['user_id'])
        
        flash('Client created successfully!', 'success')
        return redirect(url_for('clients'))
    
    return render_template('create_client.html')

@app.route('/clients/<int:id>')
def view_client(id):
    client = Client.query.get_or_404(id)
    if client.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('clients'))
    
    projects = Project.query.filter_by(client_id=id).order_by(Project.created_at.desc()).all()
    return render_template('view_client.html', client=client, projects=projects)

@app.route('/calendar')
def calendar_view():
    firm_id = session['firm_id']
    
    # Get year and month from query parameters or use current date
    year = int(request.args.get('year', date.today().year))
    month = int(request.args.get('month', date.today().month))
    
    # Create date object for the requested month
    current_date = date(year, month, 1)
    
    # Get start and end dates for the calendar view (include previous/next month days)
    start_of_month = date(year, month, 1)
    
    # Get the first day of the week for the month
    first_weekday = start_of_month.weekday()
    # Adjust for Sunday start (weekday() returns 0=Monday, we want 0=Sunday)
    days_back = (first_weekday + 1) % 7
    calendar_start = start_of_month - timedelta(days=days_back)
    
    # Get end of month
    if month == 12:
        end_of_month = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_of_month = date(year, month + 1, 1) - timedelta(days=1)
    
    # Calculate days forward to complete the calendar grid (6 weeks * 7 days = 42 days)
    days_shown = (end_of_month - calendar_start).days + 1
    days_needed = 42 - days_shown
    calendar_end = end_of_month + timedelta(days=days_needed)
    
    # Query tasks for the calendar period - include both project and independent tasks
    tasks = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        ),
        Task.due_date.between(calendar_start, calendar_end)
    ).order_by(Task.due_date.asc()).all()
    
    # Organize tasks by date
    calendar_data = {}
    for task in tasks:
        if task.due_date:
            date_str = task.due_date.strftime('%Y-%m-%d')
            if date_str not in calendar_data:
                calendar_data[date_str] = []
            
            # Prepare task data for JSON serialization
            task_data = {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'priority': task.priority,
                'is_overdue': task.is_overdue,
                'is_due_soon': task.is_due_soon,
                'project_name': task.project.client_name if task.project else None,
                'assignee_name': task.assignee.name if task.assignee else None
            }
            calendar_data[date_str].append(task_data)
    
    return render_template('calendar.html', 
                         calendar_data=calendar_data,
                         current_date=current_date,
                         year=year,
                         month=month)

@app.route('/kanban')
def kanban_view():
    firm_id = session['firm_id']
    
    # Get filter parameters
    work_type_filter = request.args.get('work_type')
    project_filter = request.args.get('project')
    assignee_filter = request.args.get('assignee')
    priority_filter = request.args.get('priority')
    due_filter = request.args.get('due_filter')
    
    # Get work types for filtering
    work_types = WorkType.query.filter_by(firm_id=firm_id, is_active=True).all()
    current_work_type = None
    kanban_statuses = []
    
    if work_type_filter:
        current_work_type = WorkType.query.filter_by(id=work_type_filter, firm_id=firm_id).first()
        if current_work_type:
            kanban_statuses = TaskStatus.query.filter_by(
                work_type_id=current_work_type.id,
                firm_id=firm_id
            ).order_by(TaskStatus.position.asc()).all()
    
    # Base query - include both project and independent tasks
    query = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        )
    )
    
    # Apply work type filter
    if work_type_filter and current_work_type:
        query = query.filter(Project.work_type_id == current_work_type.id)
    
    # Apply other filters
    if project_filter:
        query = query.filter(Task.project_id == project_filter)
    if assignee_filter:
        query = query.filter(Task.assignee_id == assignee_filter)
    if priority_filter:
        query = query.filter(Task.priority == priority_filter)
    
    # Apply due date filters
    today = date.today()
    if due_filter == 'overdue':
        query = query.filter(Task.due_date < today)
    elif due_filter == 'today':
        query = query.filter(Task.due_date == today)
    elif due_filter == 'this_week':
        week_end = today + timedelta(days=7)
        query = query.filter(Task.due_date.between(today, week_end))
    
    # Get all tasks
    tasks = query.order_by(Task.created_at.desc()).all()
    
    # Organize tasks by status
    if current_work_type and kanban_statuses:
        # Use custom statuses for work type
        tasks_by_status = {}
        task_counts = {}
        
        for status in kanban_statuses:
            tasks_by_status[status.id] = []
            task_counts[status.id] = 0
        
        for task in tasks:
            # Use new status system if available, fallback to legacy
            if task.status_id and task.status_id in task_counts:
                tasks_by_status[task.status_id].append(task)
                task_counts[task.status_id] += 1
            elif not task.status_id:
                # Legacy fallback - try to match legacy status to new status by name
                for status in kanban_statuses:
                    if status.name == task.status:
                        tasks_by_status[status.id].append(task)
                        task_counts[status.id] += 1
                        break
    else:
        # Use legacy status columns
        tasks_by_status = {
            'Not Started': [],
            'In Progress': [],
            'Needs Review': [],
            'Completed': []
        }
        
        task_counts = {
            'Not Started': 0,
            'In Progress': 0,
            'Needs Review': 0,
            'Completed': 0
        }
        
        for task in tasks:
            current_status = task.current_status  # Use the property that handles both systems
            if current_status in tasks_by_status:
                tasks_by_status[current_status].append(task)
                task_counts[current_status] += 1
    
    # Get filter options
    users = User.query.filter_by(firm_id=firm_id).all()
    projects = Project.query.filter_by(firm_id=firm_id).all()
    
    return render_template('kanban.html', 
                         tasks_by_status=tasks_by_status,
                         task_counts=task_counts,
                         kanban_statuses=kanban_statuses,
                         current_work_type=current_work_type,
                         work_types=work_types,
                         users=users, 
                         projects=projects)

@app.route('/search')
def search():
    firm_id = session['firm_id']
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')
    
    results = {
        'tasks': [],
        'projects': [],
        'clients': [],
        'query': query,
        'search_type': search_type
    }
    
    if not query:
        return render_template('search.html', **results)
    
    # Search tasks
    if search_type in ['all', 'tasks']:
        task_query = Task.query.outerjoin(Project).filter(
            db.or_(
                Project.firm_id == firm_id,
                db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            )
        )
        
        # Search in task title, description, and comments
        task_filters = db.or_(
            Task.title.ilike(f'%{query}%'),
            Task.description.ilike(f'%{query}%'),
            Task.comments.ilike(f'%{query}%')
        )
        
        results['tasks'] = task_query.filter(task_filters).order_by(Task.created_at.desc()).limit(20).all()
    
    # Search projects
    if search_type in ['all', 'projects']:
        project_query = Project.query.filter_by(firm_id=firm_id)
        
        # Search in project name and client name
        project_filters = db.or_(
            Project.name.ilike(f'%{query}%')
        )
        
        # Also search by client name if client relationship exists
        project_query = project_query.join(Client, Project.client_id == Client.id, isouter=True)
        project_filters = db.or_(
            project_filters,
            Client.name.ilike(f'%{query}%')
        )
        
        results['projects'] = project_query.filter(project_filters).order_by(Project.created_at.desc()).limit(20).all()
    
    # Search clients
    if search_type in ['all', 'clients']:
        client_query = Client.query.filter_by(firm_id=firm_id)
        
        # Search in client name, email, contact person, and notes
        client_filters = db.or_(
            Client.name.ilike(f'%{query}%'),
            Client.email.ilike(f'%{query}%'),
            Client.contact_person.ilike(f'%{query}%'),
            Client.notes.ilike(f'%{query}%'),
            Client.tax_id.ilike(f'%{query}%')
        )
        
        results['clients'] = client_query.filter(client_filters).order_by(Client.created_at.desc()).limit(20).all()
    
    return render_template('search.html', **results)

@app.route('/export/tasks')
def export_tasks():
    firm_id = session['firm_id']
    format_type = request.args.get('format', 'csv')
    
    # Get all tasks for the firm
    tasks = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        )
    ).all()
    
    if format_type == 'csv':
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Task Title', 'Description', 'Status', 'Priority', 
            'Due Date', 'Estimated Hours', 'Actual Hours',
            'Assignee', 'Project', 'Client', 'Created Date'
        ])
        
        # Write data
        for task in tasks:
            writer.writerow([
                task.title,
                task.description or '',
                task.status,
                task.priority,
                task.due_date.strftime('%Y-%m-%d') if task.due_date else '',
                task.estimated_hours or '',
                task.actual_hours or '',
                task.assignee.name if task.assignee else '',
                task.project.name if task.project else 'Independent Task',
                task.project.client_name if task.project else '',
                task.created_at.strftime('%Y-%m-%d %H:%M:%S') if task.created_at else ''
            ])
        
        output.seek(0)
        
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=tasks_export_{date.today().strftime("%Y%m%d")}.csv'}
        )
    
    return jsonify({'error': 'Unsupported format'}), 400

@app.route('/export/projects')
def export_projects():
    firm_id = session['firm_id']
    format_type = request.args.get('format', 'csv')
    
    # Get all projects for the firm
    projects = Project.query.filter_by(firm_id=firm_id).all()
    
    if format_type == 'csv':
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Project Name', 'Client Name', 'Status', 'Priority',
            'Start Date', 'Due Date', 'Template', 'Progress %',
            'Total Tasks', 'Completed Tasks', 'Created Date'
        ])
        
        # Write data
        for project in projects:
            completed_tasks = len([t for t in project.tasks if t.status == 'Completed'])
            total_tasks = len(project.tasks)
            
            writer.writerow([
                project.name,
                project.client_name,
                project.status,
                project.priority if hasattr(project, 'priority') else 'Medium',
                project.start_date.strftime('%Y-%m-%d') if project.start_date else '',
                project.due_date.strftime('%Y-%m-%d') if project.due_date else '',
                project.template_origin.name if project.template_origin else '',
                f'{project.progress_percentage}%',
                total_tasks,
                completed_tasks,
                project.created_at.strftime('%Y-%m-%d %H:%M:%S') if project.created_at else ''
            ])
        
        output.seek(0)
        
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=projects_export_{date.today().strftime("%Y%m%d")}.csv'}
        )
    
    return jsonify({'error': 'Unsupported format'}), 400

@app.route('/export/clients')
def export_clients():
    firm_id = session['firm_id']
    format_type = request.args.get('format', 'csv')
    
    # Get all clients for the firm
    clients = Client.query.filter_by(firm_id=firm_id).all()
    
    if format_type == 'csv':
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Client Name', 'Entity Type', 'Email', 'Phone', 'Address',
            'Contact Person', 'Tax ID', 'Active Projects', 'Notes', 'Created Date'
        ])
        
        # Write data
        for client in clients:
            active_projects = Project.query.filter_by(client_id=client.id, status='Active').count()
            
            writer.writerow([
                client.name,
                client.entity_type or '',
                client.email or '',
                client.phone or '',
                client.address or '',
                client.contact_person or '',
                client.tax_id or '',
                active_projects,
                client.notes or '',
                client.created_at.strftime('%Y-%m-%d %H:%M:%S') if client.created_at else ''
            ])
        
        output.seek(0)
        
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=clients_export_{date.today().strftime("%Y%m%d")}.csv'}
        )
    
    return jsonify({'error': 'Unsupported format'}), 400

@app.route('/clients/<int:id>/edit', methods=['GET', 'POST'])
def edit_client(id):
    client = Client.query.get_or_404(id)
    if client.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('clients'))
    
    if request.method == 'POST':
        client.name = request.form.get('name')
        client.email = request.form.get('email')
        client.phone = request.form.get('phone')
        client.address = request.form.get('address')
        client.contact_person = request.form.get('contact_person')
        client.entity_type = request.form.get('entity_type')
        client.tax_id = request.form.get('tax_id')
        client.notes = request.form.get('notes')
        
        db.session.commit()
        
        # Activity log
        create_activity_log(f'Client "{client.name}" updated', session['user_id'])
        
        flash('Client updated successfully!', 'success')
        return redirect(url_for('view_client', id=client.id))
    
    return render_template('edit_client.html', client=client)

@app.route('/admin/work_types', methods=['GET'])
def admin_work_types():
    if session.get('user_role') != 'Admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    work_types = WorkType.query.filter_by(firm_id=session['firm_id']).all()
    
    # Get task count by work type
    work_type_usage = {}
    for wt in work_types:
        task_count = Task.query.filter_by(firm_id=session['firm_id'], work_type_id=wt.id).count()
        work_type_usage[wt.id] = task_count
    
    return render_template('admin_work_types.html', 
                         work_types=work_types, 
                         work_type_usage=work_type_usage)

@app.route('/admin/work_types/create', methods=['POST'])
def admin_create_work_type():
    if session.get('user_role') != 'Admin':
        return jsonify({'error': 'Access denied'}), 403
    
    name = request.form.get('name')
    color = request.form.get('color', '#3b82f6')
    
    if not name:
        return jsonify({'error': 'Work type name is required'}), 400
    
    # Check if work type already exists
    existing = WorkType.query.filter_by(firm_id=session['firm_id'], name=name).first()
    if existing:
        return jsonify({'error': 'Work type with this name already exists'}), 400
    
    work_type = WorkType(
        firm_id=session['firm_id'],
        name=name,
        color=color
    )
    
    db.session.add(work_type)
    db.session.flush()  # Get the ID
    
    # Create default status
    default_status = TaskStatus(
        work_type_id=work_type.id,
        name='Not Started',
        color='#6b7280',
        position=1,
        is_default=True,
        is_terminal=False
    )
    
    db.session.add(default_status)
    db.session.commit()
    
    create_activity_log(f'Work type "{name}" created', session['user_id'])
    
    return jsonify({'success': True, 'work_type_id': work_type.id})

@app.route('/admin/work_types/<int:work_type_id>/edit', methods=['POST'])
def admin_edit_work_type(work_type_id):
    if session.get('user_role') != 'Admin':
        return jsonify({'error': 'Access denied'}), 403
    
    work_type = WorkType.query.filter_by(id=work_type_id, firm_id=session['firm_id']).first()
    if not work_type:
        return jsonify({'error': 'Work type not found'}), 404
    
    name = request.form.get('name')
    color = request.form.get('color')
    
    if not name:
        return jsonify({'error': 'Work type name is required'}), 400
    
    # Check if name conflicts with another work type
    existing = WorkType.query.filter_by(firm_id=session['firm_id'], name=name).filter(WorkType.id != work_type_id).first()
    if existing:
        return jsonify({'error': 'Work type with this name already exists'}), 400
    
    old_name = work_type.name
    work_type.name = name
    if color:
        work_type.color = color
    
    db.session.commit()
    
    create_activity_log(f'Work type "{old_name}" updated to "{name}"', session['user_id'])
    
    return jsonify({'success': True})

@app.route('/admin/work_types/<int:work_type_id>/statuses/create', methods=['POST'])
def admin_create_status(work_type_id):
    if session.get('user_role') != 'Admin':
        return jsonify({'error': 'Access denied'}), 403
    
    work_type = WorkType.query.filter_by(id=work_type_id, firm_id=session['firm_id']).first()
    if not work_type:
        return jsonify({'error': 'Work type not found'}), 404
    
    name = request.form.get('name')
    color = request.form.get('color', '#6b7280')
    is_terminal = request.form.get('is_terminal') == 'true'
    is_default = request.form.get('is_default') == 'true'
    
    if not name:
        return jsonify({'error': 'Status name is required'}), 400
    
    # Check if status already exists for this work type
    existing = TaskStatus.query.filter_by(work_type_id=work_type_id, name=name).first()
    if existing:
        return jsonify({'error': 'Status with this name already exists for this work type'}), 400
    
    # Get next position
    max_position = db.session.query(db.func.max(TaskStatus.position)).filter_by(work_type_id=work_type_id).scalar() or 0
    
    # If setting as default, remove default from others
    if is_default:
        TaskStatus.query.filter_by(work_type_id=work_type_id, is_default=True).update({'is_default': False})
    
    status = TaskStatus(
        work_type_id=work_type_id,
        name=name,
        color=color,
        position=max_position + 1,
        is_default=is_default,
        is_terminal=is_terminal
    )
    
    db.session.add(status)
    db.session.commit()
    
    create_activity_log(f'Status "{name}" created for work type "{work_type.name}"', session['user_id'])
    
    return jsonify({'success': True, 'status_id': status.id})

@app.route('/admin/statuses/<int:status_id>/edit', methods=['POST'])
def admin_edit_status(status_id):
    if session.get('user_role') != 'Admin':
        return jsonify({'error': 'Access denied'}), 403
    
    status = TaskStatus.query.join(WorkType).filter(
        TaskStatus.id == status_id,
        WorkType.firm_id == session['firm_id']
    ).first()
    
    if not status:
        return jsonify({'error': 'Status not found'}), 404
    
    name = request.form.get('name')
    color = request.form.get('color')
    is_terminal = request.form.get('is_terminal') == 'true'
    is_default = request.form.get('is_default') == 'true'
    
    if not name:
        return jsonify({'error': 'Status name is required'}), 400
    
    # Check if name conflicts with another status in same work type
    existing = TaskStatus.query.filter_by(work_type_id=status.work_type_id, name=name).filter(TaskStatus.id != status_id).first()
    if existing:
        return jsonify({'error': 'Status with this name already exists for this work type'}), 400
    
    # If setting as default, remove default from others
    if is_default and not status.is_default:
        TaskStatus.query.filter_by(work_type_id=status.work_type_id, is_default=True).update({'is_default': False})
    
    old_name = status.name
    status.name = name
    if color:
        status.color = color
    status.is_terminal = is_terminal
    status.is_default = is_default
    
    db.session.commit()
    
    create_activity_log(f'Status "{old_name}" updated to "{name}" for work type "{status.work_type.name}"', session['user_id'])
    
    return jsonify({'success': True})

@app.route('/admin/statuses/<int:status_id>/delete', methods=['POST'])
def admin_delete_status(status_id):
    if session.get('user_role') != 'Admin':
        return jsonify({'error': 'Access denied'}), 403
    
    status = TaskStatus.query.join(WorkType).filter(
        TaskStatus.id == status_id,
        WorkType.firm_id == session['firm_id']
    ).first()
    
    if not status:
        return jsonify({'error': 'Status not found'}), 404
    
    # Check if status is in use
    task_count = Task.query.filter_by(work_type_status_id=status_id).count()
    if task_count > 0:
        return jsonify({'error': f'Cannot delete status. It is currently used by {task_count} task(s).'}), 400
    
    # Check if it's the only status for the work type
    status_count = TaskStatus.query.filter_by(work_type_id=status.work_type_id).count()
    if status_count <= 1:
        return jsonify({'error': 'Cannot delete the only status for a work type'}), 400
    
    # If deleting default status, make another one default
    if status.is_default:
        next_default = TaskStatus.query.filter_by(work_type_id=status.work_type_id).filter(TaskStatus.id != status_id).first()
        if next_default:
            next_default.is_default = True
    
    status_name = status.name
    work_type_name = status.work_type.name
    
    db.session.delete(status)
    db.session.commit()
    
    create_activity_log(f'Status "{status_name}" deleted from work type "{work_type_name}"', session['user_id'])
    
    return jsonify({'success': True})

@app.route('/admin/work_types/<int:work_type_id>/statuses/reorder', methods=['POST'])
def admin_reorder_statuses(work_type_id):
    if session.get('user_role') != 'Admin':
        return jsonify({'error': 'Access denied'}), 403
    
    work_type = WorkType.query.filter_by(id=work_type_id, firm_id=session['firm_id']).first()
    if not work_type:
        return jsonify({'error': 'Work type not found'}), 404
    
    status_ids = request.json.get('status_ids', [])
    
    for i, status_id in enumerate(status_ids):
        status = TaskStatus.query.filter_by(id=status_id, work_type_id=work_type_id).first()
        if status:
            status.position = i + 1
    
    db.session.commit()
    
    create_activity_log(f'Status order updated for work type "{work_type.name}"', session['user_id'])
    
    return jsonify({'success': True})

@app.route('/contacts')
def contacts():
    firm_id = session['firm_id']
    
    # Get all contacts with client count
    contacts = db.session.query(Contact).join(ClientContact).join(Client).filter(
        Client.firm_id == firm_id
    ).distinct().all()
    
    # Get contacts not associated with any clients in this firm
    orphaned_contacts = db.session.query(Contact).outerjoin(ClientContact).outerjoin(Client).filter(
        (Client.firm_id != firm_id) | (Client.id == None)
    ).distinct().all()
    
    all_contacts = list(set(contacts + orphaned_contacts))
    
    # Add client count to each contact
    for contact in all_contacts:
        contact.client_count = db.session.query(ClientContact).join(Client).filter(
            ClientContact.contact_id == contact.id,
            Client.firm_id == firm_id
        ).count()
    
    return render_template('contacts.html', contacts=all_contacts)

@app.route('/contacts/create', methods=['GET', 'POST'])
def create_contact():
    if request.method == 'POST':
        contact = Contact(
            first_name=request.form.get('first_name'),
            last_name=request.form.get('last_name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            title=request.form.get('title'),
            company=request.form.get('company'),
            address=request.form.get('address'),
            notes=request.form.get('notes')
        )
        
        try:
            db.session.add(contact)
            db.session.commit()
            
            create_activity_log(f'Contact "{contact.first_name} {contact.last_name}" created', session['user_id'])
            flash('Contact created successfully!', 'success')
            return redirect(url_for('contacts'))
            
        except Exception as e:
            db.session.rollback()
            if 'UNIQUE constraint failed' in str(e):
                flash('A contact with this email already exists.', 'error')
            else:
                flash('Error creating contact.', 'error')
            return redirect(url_for('create_contact'))
    
    return render_template('create_contact.html')

@app.route('/contacts/<int:id>')
def view_contact(id):
    contact = Contact.query.get_or_404(id)
    
    # Get clients associated with this contact in current firm
    client_contacts = db.session.query(ClientContact, Client).join(Client).filter(
        ClientContact.contact_id == id,
        Client.firm_id == session['firm_id']
    ).all()
    
    clients = [cc[1] for cc in client_contacts]
    
    return render_template('view_contact.html', contact=contact, clients=clients)

@app.route('/contacts/<int:id>/edit', methods=['GET', 'POST'])
def edit_contact(id):
    contact = Contact.query.get_or_404(id)
    
    if request.method == 'POST':
        contact.first_name = request.form.get('first_name')
        contact.last_name = request.form.get('last_name')
        contact.email = request.form.get('email')
        contact.phone = request.form.get('phone')
        contact.title = request.form.get('title')
        contact.company = request.form.get('company')
        contact.address = request.form.get('address')
        contact.notes = request.form.get('notes')
        
        try:
            db.session.commit()
            create_activity_log(f'Contact "{contact.first_name} {contact.last_name}" updated', session['user_id'])
            flash('Contact updated successfully!', 'success')
            return redirect(url_for('view_contact', id=contact.id))
            
        except Exception as e:
            db.session.rollback()
            if 'UNIQUE constraint failed' in str(e):
                flash('A contact with this email already exists.', 'error')
            else:
                flash('Error updating contact.', 'error')
    
    return render_template('edit_contact.html', contact=contact)

@app.route('/contacts/<int:contact_id>/clients/<int:client_id>/associate', methods=['POST'])
def associate_contact_client(contact_id, client_id):
    contact = Contact.query.get_or_404(contact_id)
    client = Client.query.get_or_404(client_id)
    
    if client.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('contacts'))
    
    # Check if association already exists
    existing = ClientContact.query.filter_by(client_id=client_id, contact_id=contact_id).first()
    if existing:
        flash('Contact is already associated with this client.', 'error')
        return redirect(url_for('view_contact', id=contact_id))
    
    client_contact = ClientContact(client_id=client_id, contact_id=contact_id)
    db.session.add(client_contact)
    db.session.commit()
    
    create_activity_log(f'Contact "{contact.first_name} {contact.last_name}" associated with client "{client.name}"', session['user_id'])
    flash('Contact associated with client successfully!', 'success')
    
    return redirect(url_for('view_contact', id=contact_id))

@app.route('/contacts/<int:contact_id>/clients/<int:client_id>/disassociate', methods=['POST'])
def disassociate_contact_client(contact_id, client_id):
    client = Client.query.get_or_404(client_id)
    
    if client.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('contacts'))
    
    client_contact = ClientContact.query.filter_by(client_id=client_id, contact_id=contact_id).first()
    if client_contact:
        db.session.delete(client_contact)
        db.session.commit()
        
        contact = Contact.query.get(contact_id)
        create_activity_log(f'Contact "{contact.first_name} {contact.last_name}" disassociated from client "{client.name}"', session['user_id'])
        flash('Contact disassociated from client successfully!', 'success')
    
    return redirect(url_for('view_contact', id=contact_id))

@app.route('/api/clients')
def api_clients():
    """API endpoint to get clients for the current firm"""
    firm_id = session['firm_id']
    clients = Client.query.filter_by(firm_id=firm_id, is_active=True).all()
    
    return jsonify([{
        'id': client.id,
        'name': client.name,
        'entity_type': client.entity_type
    } for client in clients])

@app.route('/recurring-tasks')
def recurring_tasks():
    firm_id = session['firm_id']
    recurring_tasks = RecurringTask.query.filter_by(firm_id=firm_id).order_by(RecurringTask.next_due_date.asc()).all()
    return render_template('recurring_tasks.html', recurring_tasks=recurring_tasks)

@app.route('/recurring-tasks/create', methods=['GET', 'POST'])
def create_recurring_task():
    if request.method == 'POST':
        firm_id = session['firm_id']
        
        # Get form data
        title = request.form.get('title')
        description = request.form.get('description')
        recurrence_rule = request.form.get('recurrence_rule')
        priority = request.form.get('priority', 'Medium')
        estimated_hours = request.form.get('estimated_hours')
        assignee_id = request.form.get('assignee_id')
        client_id = request.form.get('client_id')
        work_type_id = request.form.get('work_type_id')
        next_due_date = request.form.get('next_due_date')
        
        # Convert estimated_hours
        estimated_hours_float = None
        if estimated_hours:
            try:
                estimated_hours_float = float(estimated_hours)
            except ValueError:
                pass
        
        # Convert next_due_date
        next_due_date_obj = datetime.strptime(next_due_date, '%Y-%m-%d').date()
        
        # Get default status for work type if specified
        status_id = None
        if work_type_id:
            default_status = TaskStatus.query.filter_by(
                work_type_id=work_type_id,
                is_default=True
            ).first()
            if default_status:
                status_id = default_status.id
        
        # Create recurring task
        recurring_task = RecurringTask(
            firm_id=firm_id,
            title=title,
            description=description,
            recurrence_rule=recurrence_rule,
            priority=priority,
            estimated_hours=estimated_hours_float,
            default_assignee_id=assignee_id if assignee_id else None,
            client_id=client_id if client_id else None,
            work_type_id=work_type_id if work_type_id else None,
            status_id=status_id,
            next_due_date=next_due_date_obj
        )
        
        db.session.add(recurring_task)
        db.session.commit()
        
        # Activity log
        create_activity_log(f'Recurring task "{recurring_task.title}" created', session['user_id'])
        
        flash('Recurring task created successfully!', 'success')
        return redirect(url_for('recurring_tasks'))
    
    # GET request - show form
    firm_id = session['firm_id']
    users = User.query.filter_by(firm_id=firm_id).all()
    clients = Client.query.filter_by(firm_id=firm_id, is_active=True).all()
    work_types = WorkType.query.filter_by(firm_id=firm_id, is_active=True).all()
    
    return render_template('create_recurring_task.html', users=users, clients=clients, work_types=work_types)

@app.route('/recurring-tasks/<int:id>/edit', methods=['GET', 'POST'])
def edit_recurring_task(id):
    recurring_task = RecurringTask.query.get_or_404(id)
    if recurring_task.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('recurring_tasks'))
    
    if request.method == 'POST':
        # Update task details
        recurring_task.title = request.form.get('title')
        recurring_task.description = request.form.get('description')
        recurring_task.recurrence_rule = request.form.get('recurrence_rule')
        recurring_task.priority = request.form.get('priority', 'Medium')
        recurring_task.is_active = 'is_active' in request.form
        
        # Handle estimated hours
        estimated_hours = request.form.get('estimated_hours')
        if estimated_hours:
            try:
                recurring_task.estimated_hours = float(estimated_hours)
            except ValueError:
                recurring_task.estimated_hours = None
        else:
            recurring_task.estimated_hours = None
        
        # Handle assignee
        assignee_id = request.form.get('assignee_id')
        recurring_task.default_assignee_id = assignee_id if assignee_id else None
        
        # Handle client
        client_id = request.form.get('client_id')
        recurring_task.client_id = client_id if client_id else None
        
        # Handle work type and default status
        work_type_id = request.form.get('work_type_id')
        recurring_task.work_type_id = work_type_id if work_type_id else None
        
        if work_type_id:
            default_status = TaskStatus.query.filter_by(
                work_type_id=work_type_id,
                is_default=True
            ).first()
            if default_status:
                recurring_task.status_id = default_status.id
        else:
            recurring_task.status_id = None
        
        # Handle next due date
        next_due_date = request.form.get('next_due_date')
        if next_due_date:
            recurring_task.next_due_date = datetime.strptime(next_due_date, '%Y-%m-%d').date()
        
        db.session.commit()
        
        # Activity log
        create_activity_log(f'Recurring task "{recurring_task.title}" updated', session['user_id'])
        
        flash('Recurring task updated successfully!', 'success')
        return redirect(url_for('recurring_tasks'))
    
    # GET request - show form
    firm_id = session['firm_id']
    users = User.query.filter_by(firm_id=firm_id).all()
    clients = Client.query.filter_by(firm_id=firm_id, is_active=True).all()
    work_types = WorkType.query.filter_by(firm_id=firm_id, is_active=True).all()
    
    return render_template('edit_recurring_task.html', recurring_task=recurring_task, users=users, clients=clients, work_types=work_types)

@app.route('/recurring-tasks/<int:id>/toggle', methods=['POST'])
def toggle_recurring_task(id):
    recurring_task = RecurringTask.query.get_or_404(id)
    if recurring_task.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    recurring_task.is_active = not recurring_task.is_active
    db.session.commit()
    
    status = 'activated' if recurring_task.is_active else 'deactivated'
    create_activity_log(f'Recurring task "{recurring_task.title}" {status}', session['user_id'])
    
    return jsonify({'success': True, 'is_active': recurring_task.is_active})

@app.route('/recurring-tasks/<int:id>/delete', methods=['POST'])
def delete_recurring_task(id):
    recurring_task = RecurringTask.query.get_or_404(id)
    if recurring_task.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    task_title = recurring_task.title
    
    # Delete all generated tasks that haven't been started yet
    Task.query.filter_by(
        recurring_task_origin_id=recurring_task.id,
        status='Not Started'
    ).delete()
    
    db.session.delete(recurring_task)
    db.session.commit()
    
    create_activity_log(f'Recurring task "{task_title}" deleted', session['user_id'])
    
    return jsonify({'success': True, 'message': 'Recurring task deleted successfully'})

@app.route('/admin/process-recurring', methods=['POST'])
def admin_process_recurring():
    """Manual trigger for processing recurring tasks"""
    if session.get('user_role') != 'Admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        process_recurring_tasks()
        return jsonify({'success': True, 'message': 'Recurring tasks processed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True)