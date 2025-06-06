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

from models import db, Firm, User, Template, TemplateTask, Project, Task, ActivityLog, Client, TaskComment

db.init_app(app)
from utils import generate_access_code, create_activity_log, process_recurring_tasks, calculate_next_due_date, calculate_task_due_date, find_or_create_client

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
    completed_tasks = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        ),
        Task.status == 'Completed'
    ).count()
    overdue_tasks = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        ),
        Task.due_date < date.today(),
        Task.status != 'Completed'
    ).count()
    active_clients = Client.query.filter_by(firm_id=firm_id, is_active=True).count()
    
    # Task status distribution
    task_status_data = {}
    for status in ['Not Started', 'In Progress', 'Needs Review', 'Completed']:
        count = Task.query.join(Project).filter(
            Project.firm_id == firm_id,
            Task.status == status
        ).count()
        task_status_data[status] = count
    
    # Priority distribution
    priority_data = {}
    for priority in ['High', 'Medium', 'Low']:
        count = Task.query.join(Project).filter(
            Project.firm_id == firm_id,
            Task.priority == priority
        ).count()
        priority_data[priority] = count
    
    # Recent activity (last 7 days)
    week_ago = datetime.now() - timedelta(days=7)
    recent_tasks = Task.query.join(Project).filter(
        Project.firm_id == firm_id,
        Task.created_at >= week_ago
    ).count()
    
    # Workload by user - include both project tasks and independent tasks
    user_workload = {}
    users = User.query.filter_by(firm_id=firm_id).all()
    for user in users:
        active_tasks = Task.query.outerjoin(Project).filter(
            db.or_(
                Project.firm_id == firm_id,
                db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
            ),
            Task.assignee_id == user.id,
            Task.status.in_(['Not Started', 'In Progress', 'Needs Review'])
        ).count()
        user_workload[user.name] = active_tasks
    
    # Upcoming deadlines (next 7 days) - include both project tasks and independent tasks
    next_week = date.today() + timedelta(days=7)
    upcoming_tasks = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        ),
        Task.due_date.between(date.today(), next_week),
        Task.status != 'Completed'
    ).order_by(Task.due_date.asc()).limit(5).all()
    
    # Critical notifications - overdue and due today
    today_tasks = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        ),
        Task.due_date == date.today(),
        Task.status != 'Completed'
    ).count()
    
    # Due this week count
    due_this_week = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        ),
        Task.due_date.between(date.today(), next_week),
        Task.status != 'Completed'
    ).count()
    
    return render_template('dashboard.html', 
                         projects=projects, 
                         total_tasks=total_tasks,
                         completed_tasks=completed_tasks,
                         overdue_tasks=overdue_tasks,
                         active_clients=active_clients,
                         task_status_data=task_status_data,
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
        
        project = Project(
            name=project_name or f"{client.name} - {Template.query.get(template_id).name}",
            client_id=client.id,
            start_date=start_date,
            due_date=due_date,
            priority=priority,
            firm_id=firm_id,
            template_origin_id=template_id
        )
        db.session.add(project)
        db.session.flush()
        
        # Create tasks from template
        template = Template.query.get(template_id)
        for template_task in template.template_tasks:
            # Calculate due date
            task_due_date = calculate_task_due_date(start_date, template_task)
            
            task = Task(
                title=template_task.title,
                description=template_task.description,
                due_date=task_due_date,
                priority=template_task.default_priority or 'Medium',
                estimated_hours=template_task.estimated_hours,
                project_id=project.id,
                assignee_id=template_task.default_assignee_id,
                template_task_origin_id=template_task.id
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
    return render_template('edit_project.html', project=project)

@app.route('/tasks')
def tasks():
    firm_id = session['firm_id']
    
    # Get filter parameters
    status_filter = request.args.get('status')
    priority_filter = request.args.get('priority')
    assignee_filter = request.args.get('assignee')
    project_filter = request.args.get('project')
    overdue_filter = request.args.get('overdue')
    
    # Base query - include both project tasks and independent tasks
    query = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        )
    )
    
    # Apply filters
    if status_filter:
        query = query.filter(Task.status == status_filter)
    if priority_filter:
        query = query.filter(Task.priority == priority_filter)
    if assignee_filter:
        query = query.filter(Task.assignee_id == assignee_filter)
    if project_filter:
        query = query.filter(Task.project_id == project_filter)
    if overdue_filter == 'true':
        query = query.filter(Task.due_date < date.today(), Task.status != 'Completed')
    
    # Order by due date
    tasks = query.order_by(Task.due_date.asc()).all()
    
    # Get filter options
    users = User.query.filter_by(firm_id=firm_id).all()
    projects = Project.query.filter_by(firm_id=firm_id).all()
    
    return render_template('tasks.html', tasks=tasks, users=users, projects=projects)

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
    
    return render_template('create_task.html', projects=projects, users=users, selected_project=selected_project)

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
    
    return render_template('edit_task.html', task=task, users=users)

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
    project_filter = request.args.get('project')
    assignee_filter = request.args.get('assignee')
    priority_filter = request.args.get('priority')
    
    # Base query - include both project and independent tasks
    query = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        )
    )
    
    # Apply filters
    if project_filter:
        query = query.filter(Task.project_id == project_filter)
    if assignee_filter:
        query = query.filter(Task.assignee_id == assignee_filter)
    if priority_filter:
        query = query.filter(Task.priority == priority_filter)
    
    # Get all tasks
    tasks = query.order_by(Task.created_at.desc()).all()
    
    # Organize tasks by status
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
        if task.status in tasks_by_status:
            tasks_by_status[task.status].append(task)
            task_counts[task.status] += 1
    
    # Get filter options
    users = User.query.filter_by(firm_id=firm_id).all()
    projects = Project.query.filter_by(firm_id=firm_id).all()
    
    return render_template('kanban.html', 
                         tasks_by_status=tasks_by_status,
                         task_counts=task_counts,
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

if __name__ == '__main__':
    app.run(debug=True)