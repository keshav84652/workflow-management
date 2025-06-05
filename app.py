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
    if request.endpoint in ['static', 'admin_login', 'admin_dashboard', 'generate_access_code_route', 'admin_authenticate']:
        return
    
    if 'firm_id' not in session and request.endpoint not in ['login', 'authenticate']:
        return redirect(url_for('login'))

@app.route('/')
def login():
    if 'firm_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/authenticate', methods=['POST'])
def authenticate():
    access_code = request.form.get('access_code', '').strip()
    firm = Firm.query.filter_by(access_code=access_code, is_active=True).first()
    
    if firm:
        session['firm_id'] = firm.id
        session['firm_name'] = firm.name
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid access code', 'error')
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    firm_id = session['firm_id']
    projects = Project.query.filter_by(firm_id=firm_id, status='Active').all()
    overdue_tasks = Task.query.join(Project).filter(
        Project.firm_id == firm_id,
        Task.due_date < date.today(),
        Task.status != 'Completed'
    ).count()
    
    return render_template('dashboard.html', projects=projects, overdue_tasks=overdue_tasks)

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
        user_id = session.get('user_id', 1)  # We'll implement proper user selection later
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

@app.route('/tasks')
def tasks():
    firm_id = session['firm_id']
    tasks = Task.query.join(Project).filter(
        Project.firm_id == firm_id
    ).order_by(Task.due_date.asc()).all()
    
    return render_template('tasks.html', tasks=tasks)

@app.route('/tasks/<int:id>/update', methods=['POST'])
def update_task(id):
    task = Task.query.get_or_404(id)
    if task.project.firm_id != session['firm_id']:
        return jsonify({'error': 'Access denied'}), 403
    
    old_status = task.status
    new_status = request.json.get('status')
    
    if new_status in ['Not Started', 'In Progress', 'Needs Review', 'Completed']:
        task.status = new_status
        db.session.commit()
        
        if old_status != new_status:
            create_activity_log(
                f'Task status changed from "{old_status}" to "{new_status}"',
                session.get('user_id', 1),
                task.project_id,
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

if __name__ == '__main__':
    app.run(debug=True)