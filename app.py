from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, date, timedelta
import os
import secrets
import calendar
import time
from pathlib import Path
from dateutil.relativedelta import relativedelta
from werkzeug.utils import secure_filename
import mimetypes
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.abspath("instance/workflow.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File upload configuration
app.config['UPLOAD_FOLDER'] = os.path.abspath('uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 
    'ppt', 'pptx', 'csv', 'zip', 'rar', '7z', 'mp4', 'avi', 'mov', 'mp3', 'wav'
}

os.makedirs('instance', exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

from models import db, Firm, User, Template, TemplateTask, Project, Task, ActivityLog, Client, TaskComment, WorkType, TaskStatus, Contact, ClientContact, Attachment, ClientUser, DocumentChecklist, ChecklistItem, ClientDocument, DocumentTemplate, DocumentTemplateItem, IncomeWorksheet, DemoAccessRequest, ClientChecklistAccess

db.init_app(app)
migrate = Migrate(app, db)
from utils import generate_access_code, create_activity_log, process_recurring_tasks, calculate_next_due_date, calculate_task_due_date, find_or_create_client


# AI Analysis Helper Functions
def perform_checklist_ai_analysis(checklist):
    """Perform one-time AI analysis for a checklist and all its documents"""
    if checklist.ai_analysis_completed:
        return
    
    try:
        import json
        from datetime import datetime
        
        # Analyze all uploaded documents that haven't been analyzed yet
        total_documents = 0
        analyzed_documents = 0
        document_types = {}
        confidence_scores = []
        
        for item in checklist.items:
            for document in item.client_documents:
                total_documents += 1
                if not document.ai_analysis_completed:
                    # Skip analysis in this function - let individual requests handle it
                    # to avoid database locking issues
                    pass
                else:
                    # Document already analyzed
                    analyzed_documents += 1
                    if document.ai_document_type:
                        document_types[document.ai_document_type] = document_types.get(document.ai_document_type, 0) + 1
                    if document.ai_confidence_score:
                        confidence_scores.append(document.ai_confidence_score)
        
        # Only save checklist summary if we have some analyzed documents
        if analyzed_documents > 0:
            # Create checklist-level summary
            checklist_summary = {
                'total_documents': total_documents,
                'analyzed_documents': analyzed_documents,
                'document_types': document_types,
                'average_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0,
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'status': 'completed' if analyzed_documents == total_documents else 'partial'
            }
            
            try:
                # Save checklist analysis with proper error handling
                checklist.ai_analysis_completed = True
                checklist.ai_analysis_results = json.dumps(checklist_summary)
                checklist.ai_analysis_timestamp = datetime.utcnow()
                
                db.session.commit()
                
            except Exception as db_error:
                print(f"Database error saving checklist analysis: {db_error}")
                db.session.rollback()
        
    except Exception as e:
        print(f"Error performing checklist AI analysis: {e}")
        try:
            db.session.rollback()
        except:
            pass
# AI Document Analysis Integration
# Note: Requires environment setup (.env file with API keys)
try:
    from backend.services.document_processor import DocumentProcessor
    from backend.services.azure_service import AzureDocumentService
    from backend.services.gemini_service import GeminiDocumentService
    from backend.services.document_visualizer import DocumentVisualizer
    from backend.agents.tax_document_analyst_agent import TaxDocumentAnalystAgent
    from backend.models.document import FileUpload, ProcessedDocument
    from backend.utils.config import settings
    AI_SERVICES_AVAILABLE = True
    print("✅ AI Services loaded successfully")
except ImportError as e:
    AI_SERVICES_AVAILABLE = False
    print(f"⚠️  AI Services not available: {e}")
    print("💡 To enable AI features:")
    print("   1. Copy .env.template to .env")
    print("   2. Add your Azure and Gemini API keys")
    print("   3. Install dependencies: pip install -r requirements.txt")

# Recurring tasks are now integrated into the Task model

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, firm_id, entity_type, entity_id):
    """Save uploaded file and create attachment record"""
    if not file or not allowed_file(file.filename):
        return None, "Invalid file type"
    
    # Generate unique filename
    original_filename = secure_filename(file.filename)
    file_extension = original_filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    
    # Create firm-specific subdirectory
    firm_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(firm_id))
    os.makedirs(firm_upload_dir, exist_ok=True)
    
    file_path = os.path.join(firm_upload_dir, unique_filename)
    
    try:
        # Save file
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        
        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(original_filename)
        
        # Create attachment record
        attachment = Attachment(
            filename=unique_filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            uploaded_by=session['user_id'],
            firm_id=firm_id
        )
        
        if entity_type == 'task':
            attachment.task_id = entity_id
        elif entity_type == 'project':
            attachment.project_id = entity_id
        
        db.session.add(attachment)
        db.session.commit()
        
        return attachment, None
        
    except Exception as e:
        # Clean up file if database operation fails
        if os.path.exists(file_path):
            os.remove(file_path)
        return None, str(e)

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
    # Skip authentication for public endpoints and landing page
    if request.endpoint in ['static', 'home', 'landing', 'admin_login', 'admin_dashboard', 'generate_access_code_route', 'admin_authenticate']:
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
def home():
    # Show simplified landing page as main entry point
    return render_template('landing.html')

@app.route('/landing')
def landing():
    # Redirect to main landing page for consistency
    return redirect(url_for('home'))

@app.route('/login')
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
    email = request.form.get('email', '').strip()
    
    firm = Firm.query.filter_by(access_code=access_code, is_active=True).first()
    
    if firm:
        # Store email in session for tracking
        session['user_email'] = email
        session['firm_id'] = firm.id
        session['firm_name'] = firm.name
        
        # For demo access, store email in database for tracking
        if access_code == 'DEMO2024':
            try:
                # Check if email already exists for demo access
                existing_request = db.session.execute(
                    db.text("SELECT * FROM demo_access_request WHERE email = :email AND firm_access_code = 'DEMO2024'"),
                    {'email': email}
                ).first()
                
                if not existing_request:
                    # Create new demo access record
                    db.session.execute(
                        db.text("""
                            INSERT INTO demo_access_request 
                            (email, firm_access_code, ip_address, user_agent, granted, granted_at, created_at) 
                            VALUES (:email, 'DEMO2024', :ip_address, :user_agent, 1, :granted_at, :created_at)
                        """),
                        {
                            'email': email,
                            'ip_address': request.remote_addr,
                            'user_agent': request.headers.get('User-Agent', ''),
                            'granted_at': datetime.utcnow(),
                            'created_at': datetime.utcnow()
                        }
                    )
                    db.session.commit()
            except Exception as e:
                # Don't block access if demo tracking fails
                print(f"Demo tracking error: {e}")
                pass
        
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
    return render_template('select_user.html', users=users, firm_name=session.get('firm_name', 'Your Firm'))

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
    return redirect(url_for('home'))

@app.route('/clear-session')
def clear_session():
    """Clear session and redirect to landing page"""
    session.clear()
    return redirect(url_for('home'))



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
    
    # Get recent tasks and projects for the modern dashboard
    recent_tasks_list = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        )
    ).order_by(Task.created_at.desc()).limit(10).all()
    
    recent_projects_list = Project.query.filter_by(firm_id=firm_id).order_by(Project.created_at.desc()).limit(10).all()
    
    return render_template('dashboard_modern.html', 
                         projects=projects, 
                         active_tasks_count=total_tasks - completed_tasks,
                         active_projects_count=len(projects),
                         overdue_tasks_count=overdue_tasks,
                         users_count=len(users),
                         recent_tasks=recent_tasks_list,
                         recent_projects=recent_projects_list,
                         # Legacy data for fallback
                         total_tasks=total_tasks,
                         completed_tasks=completed_tasks,
                         active_clients=active_clients,
                         task_status_data=task_status_data,
                         work_type_status_data=work_type_status_data,
                         work_types=work_types,
                         priority_data=priority_data,
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
    
    return render_template('tasks_modern.html', tasks=tasks, users=users, projects=projects, today=date.today())

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

@app.route('/projects/<int:id>/delete', methods=['POST'])
def delete_project(id):
    project = Project.query.get_or_404(id)
    
    # Check access permission
    if project.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        project_name = project.name
        client_name = project.client_name
        
        # Get count of associated tasks for confirmation
        task_count = Task.query.filter_by(project_id=id).count()
        
        # Create activity log before deletion
        create_activity_log(f'Project "{project_name}" for {client_name} deleted (with {task_count} tasks)', session['user_id'])
        
        # Delete all associated tasks first (cascade deletion)
        tasks = Task.query.filter_by(project_id=id).all()
        for task in tasks:
            # Delete task comments first
            TaskComment.query.filter_by(task_id=task.id).delete()
            # Delete the task
            db.session.delete(task)
        
        # Delete project attachments if any
        Attachment.query.filter_by(project_id=id).delete()
        
        # Delete the project itself
        db.session.delete(project)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Project "{project_name}" and {task_count} associated tasks deleted successfully',
            'redirect': '/projects'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting project: {str(e)}'}), 500

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
                return redirect(url_for('create_task'))
        
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
                    except ValueError:
                        # If dep_id is not an integer, skip it.
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
        
        # Handle task dependency mode for template projects
        if (task.project and task.project.task_dependency_mode and 
            task.template_task_origin_id and old_status != new_status):
            
            # Get all template tasks for this project's template in order
            template = task.project.template_origin
            if template:
                template_tasks = TemplateTask.query.filter_by(
                    template_id=template.id
                ).order_by(TemplateTask.order.asc()).all()
                
                # Find the position of the current task
                current_task_position = None
                for i, template_task in enumerate(template_tasks):
                    if template_task.id == task.template_task_origin_id:
                        current_task_position = i
                        break
                
                if current_task_position is not None:
                    project_tasks = Task.query.filter_by(project_id=task.project_id).all()
                    
                    if new_status == 'Completed' and old_status != 'Completed':
                        # Mark all previous tasks as completed
                        auto_completed_count = 0
                        for i in range(current_task_position):
                            template_task_at_pos = template_tasks[i]
                            project_task = next(
                                (t for t in project_tasks if t.template_task_origin_id == template_task_at_pos.id),
                                None
                            )
                            if project_task and project_task.status != 'Completed':
                                project_task.status = 'Completed'
                                project_task.completed_at = datetime.utcnow()
                                auto_completed_count += 1
                        
                        if auto_completed_count > 0:
                            create_activity_log(
                                f'Auto-completed {auto_completed_count} previous tasks due to task dependency mode',
                                session.get('user_id', 1),
                                task.project_id,
                                task.id
                            )
                    
                    elif new_status == 'Not Started':
                        # Mark all subsequent tasks as not started
                        auto_reset_count = 0
                        for i in range(current_task_position + 1, len(template_tasks)):
                            template_task_at_pos = template_tasks[i]
                            project_task = next(
                                (t for t in project_tasks if t.template_task_origin_id == template_task_at_pos.id),
                                None
                            )
                            if project_task and project_task.status != 'Not Started':
                                project_task.status = 'Not Started'
                                project_task.completed_at = None
                                auto_reset_count += 1
                        
                        if auto_reset_count > 0:
                            create_activity_log(
                                f'Auto-reset {auto_reset_count} subsequent tasks to Not Started due to task dependency mode',
                                session.get('user_id', 1),
                                task.project_id,
                                task.id
                            )
        
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
            
            # Check if project should be auto-completed
            if task.project_id:
                check_and_update_project_completion(task.project_id)
        
        return jsonify({'success': True})
    
    return jsonify({'error': 'Invalid status'}), 400

@app.route('/tasks/<int:id>/timer/start', methods=['POST'])
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

@app.route('/tasks/<int:id>/timer/stop', methods=['POST'])
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

@app.route('/tasks/<int:id>/timer/status', methods=['GET'])
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

@app.route('/reports/time-tracking')
def time_tracking_report():
    firm_id = session['firm_id']
    
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    user_id = request.args.get('user_id')
    project_id = request.args.get('project_id')
    
    # Base query for tasks with time logged
    query = Task.query.outerjoin(Project).filter(
        db.or_(
            Project.firm_id == firm_id,
            db.and_(Task.project_id.is_(None), Task.firm_id == firm_id)
        ),
        Task.actual_hours > 0
    )
    
    # Apply filters
    if start_date:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        query = query.filter(Task.updated_at >= start_date_obj)
    
    if end_date:
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        query = query.filter(Task.updated_at <= end_date_obj)
    
    if user_id:
        query = query.filter(Task.assignee_id == user_id)
    
    if project_id:
        query = query.filter(Task.project_id == project_id)
    
    tasks = query.order_by(Task.updated_at.desc()).all()
    
    # Calculate summary statistics
    total_hours = sum(task.actual_hours or 0 for task in tasks)
    billable_hours = sum(task.actual_hours or 0 for task in tasks if task.is_billable)
    total_billable_amount = sum(task.billable_amount for task in tasks)
    
    # Get filter options
    users = User.query.filter_by(firm_id=firm_id).all()
    projects = Project.query.filter_by(firm_id=firm_id).all()
    
    return render_template('time_tracking_report.html', 
                         tasks=tasks,
                         users=users,
                         projects=projects,
                         total_hours=total_hours,
                         billable_hours=billable_hours,
                         total_billable_amount=total_billable_amount)

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
    
    # Get available contacts (not already associated with this client)
    associated_contact_ids = db.session.query(ClientContact.contact_id).filter_by(client_id=id).subquery()
    available_contacts = Contact.query.filter(~Contact.id.in_(associated_contact_ids)).all()
    
    return render_template('view_client.html', client=client, projects=projects, available_contacts=available_contacts)

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
    priority_filter = request.args.get('priority')
    due_filter = request.args.get('due_filter')
    
    # Get work types for filtering
    work_types = WorkType.query.filter_by(firm_id=firm_id, is_active=True).all()
    
    # If no work type is selected and work types exist, redirect to the first one
    if not work_type_filter and work_types:
        return redirect(url_for('kanban_view', work_type=work_types[0].id))
    
    current_work_type = None
    kanban_columns = []
    
    if work_type_filter:
        current_work_type = WorkType.query.filter_by(id=work_type_filter, firm_id=firm_id).first()
        if current_work_type:
            # Get the template associated with this work type
            template = Template.query.filter_by(
                work_type_id=current_work_type.id,
                firm_id=firm_id
            ).first()
            
            if template:
                # Use template tasks as Kanban columns
                kanban_columns = TemplateTask.query.filter_by(
                    template_id=template.id
                ).order_by(TemplateTask.order.asc()).all()
    
    # Base query for projects (not individual tasks)
    query = Project.query.filter_by(firm_id=firm_id, status='Active')
    
    # Apply work type filter
    if work_type_filter and current_work_type:
        query = query.filter(Project.work_type_id == current_work_type.id)
    
    # Apply priority filter
    if priority_filter:
        query = query.filter(Project.priority == priority_filter)
    
    # Apply due date filters
    today = date.today()
    if due_filter == 'overdue':
        query = query.filter(Project.due_date < today)
    elif due_filter == 'today':
        query = query.filter(Project.due_date == today)
    elif due_filter == 'this_week':
        week_end = today + timedelta(days=7)
        query = query.filter(Project.due_date.between(today, week_end))
    
    # Get all projects
    projects = query.order_by(Project.created_at.desc()).all()
    
    # Organize projects by current task progress (which template task they're currently on)
    projects_by_column = {}
    project_counts = {}
    
    if kanban_columns:
        # Initialize columns
        for column in kanban_columns:
            projects_by_column[column.id] = []
            project_counts[column.id] = 0
        
        # Add a "Completed" column for finished projects
        projects_by_column['completed'] = []
        project_counts['completed'] = 0
        
        for project in projects:
            # Determine which column this project belongs in based on task progress
            project_tasks = Task.query.filter_by(project_id=project.id).all()
            
            if not project_tasks:
                # No tasks yet - put in first column
                if kanban_columns:
                    first_column = kanban_columns[0]
                    projects_by_column[first_column.id].append(project)
                    project_counts[first_column.id] += 1
            else:
                # Find current task stage based on completion
                all_completed = True
                current_column_id = None
                
                # Go through template tasks in order to find current stage
                for template_task in kanban_columns:
                    # Find corresponding project task
                    project_task = next(
                        (t for t in project_tasks if t.template_task_origin_id == template_task.id),
                        None
                    )
                    
                    if project_task:
                        if project_task.status != 'Completed':
                            # This is the current stage
                            current_column_id = template_task.id
                            all_completed = False
                            break
                    else:
                        # Task doesn't exist yet - this is the current stage
                        current_column_id = template_task.id
                        all_completed = False
                        break
                
                if all_completed:
                    # All template tasks are completed
                    projects_by_column['completed'].append(project)
                    project_counts['completed'] += 1
                elif current_column_id:
                    projects_by_column[current_column_id].append(project)
                    project_counts[current_column_id] += 1
                else:
                    # Fallback to first column
                    if kanban_columns:
                        first_column = kanban_columns[0]
                        projects_by_column[first_column.id].append(project)
                        project_counts[first_column.id] += 1
    else:
        # If no work type selected, show message to select work type
        projects_by_column = {}
        project_counts = {}
    
    # Get filter options
    users = User.query.filter_by(firm_id=firm_id).all()
    
    return render_template('kanban_modern.html', 
                         projects_by_column=projects_by_column,
                         project_counts=project_counts,
                         kanban_columns=kanban_columns,
                         current_work_type=current_work_type,
                         work_types=work_types,
                         users=users,
                         today=date.today())

@app.route('/api/clients/search')
def search_clients():
    """API endpoint to search for clients by name"""
    if 'firm_id' not in session:
        return jsonify({'error': 'Access denied'}), 403
    
    firm_id = session['firm_id']
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'clients': []})
    
    # Search for clients by name (case-insensitive)
    clients = Client.query.filter(
        Client.firm_id == firm_id,
        Client.is_active == True,
        Client.name.ilike(f'%{query}%')
    ).order_by(Client.name.asc()).limit(10).all()
    
    client_data = []
    for client in clients:
        client_data.append({
            'id': client.id,
            'name': client.name,
            'email': client.email,
            'entity_type': client.entity_type,
            'contact_person': client.contact_person
        })
    
    return jsonify({'clients': client_data})

@app.route('/projects/<int:project_id>/move-status', methods=['POST'])
def move_project_status(project_id):
    """Move a project to a different template task stage"""
    project = Project.query.get_or_404(project_id)
    
    # Check access
    if project.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        new_column_id = request.json.get('status_id')  # Using same param name for compatibility
        
        if not new_column_id:
            return jsonify({'success': False, 'message': 'Column ID is required'}), 400
        
        # Handle special "completed" column
        if new_column_id == 'completed':
            # Mark all project tasks as completed
            project_tasks = Task.query.filter_by(project_id=project.id).all()
            for task in project_tasks:
                if task.status != 'Completed':
                    task.status = 'Completed'
                    
            # Log activity
            activity_log = ActivityLog(
                action=f"Project moved to Completed stage",
                project_id=project.id,
                user_id=session.get('user_id')
            )
            db.session.add(activity_log)
            db.session.commit()
            
            # Calculate progress (should be 100%)
            total_tasks = len(project_tasks)
            
            return jsonify({
                'success': True, 
                'message': 'Project moved to completed stage',
                'project_progress': 100,
                'completed_tasks': total_tasks,
                'total_tasks': total_tasks
            })
        
        # Verify the column (template task) exists
        template_task = TemplateTask.query.get(new_column_id)
        if not template_task:
            return jsonify({'success': False, 'message': 'Invalid template task'}), 400
        
        # Get all template tasks for this project's template in order
        template = project.template_origin
        if not template:
            return jsonify({'success': False, 'message': 'Project has no template'}), 400
            
        template_tasks = TemplateTask.query.filter_by(
            template_id=template.id
        ).order_by(TemplateTask.order.asc()).all()
        
        # Find the target template task position
        target_position = None
        for i, task in enumerate(template_tasks):
            if task.id == int(new_column_id):
                target_position = i
                break
        
        if target_position is None:
            return jsonify({'success': False, 'message': 'Invalid template task'}), 400
        
        # Update task statuses to reflect the new position
        # This logic applies to ALL projects in Kanban - when moved to a column,
        # all tasks up to that point should be completed
        project_tasks = Task.query.filter_by(project_id=project.id).all()
        
        # Mark all tasks before the target position as completed
        for i in range(target_position):
            template_task_at_pos = template_tasks[i]
            project_task = next(
                (t for t in project_tasks if t.template_task_origin_id == template_task_at_pos.id),
                None
            )
            if project_task and project_task.status != 'Completed':
                project_task.status = 'Completed'
                project_task.completed_at = datetime.utcnow()
        
        # Mark all tasks after the target position as not started (if they were completed)
        for i in range(target_position + 1, len(template_tasks)):
            template_task_at_pos = template_tasks[i]
            project_task = next(
                (t for t in project_tasks if t.template_task_origin_id == template_task_at_pos.id),
                None
            )
            if project_task and project_task.status == 'Completed':
                project_task.status = 'Not Started'
                project_task.completed_at = None
        
        # Mark the target task as in progress
        target_template_task = template_tasks[target_position]
        target_project_task = next(
            (t for t in project_tasks if t.template_task_origin_id == target_template_task.id),
            None
        )
        if target_project_task:
            if target_project_task.status == 'Completed':
                target_project_task.status = 'In Progress'
            elif target_project_task.status == 'Not Started':
                target_project_task.status = 'In Progress'
        
        # Log activity
        activity_log = ActivityLog(
            action=f"Project moved to {target_template_task.title} stage",
            project_id=project.id,
            user_id=session.get('user_id')
        )
        db.session.add(activity_log)
        db.session.commit()
        
        # Use Project model's progress calculation (single source of truth)
        return jsonify({
            'success': True,
            'message': f'Project moved to {target_template_task.title} stage',
            'project_progress': project.progress_percentage,
            'completed_tasks': len([t for t in project_tasks if t.status == 'Completed']),
            'total_tasks': len(project_tasks)
        })
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/project/<int:project_id>/progress', methods=['GET'])
def get_project_progress(project_id):
    """Get current progress data for a project"""
    project = Project.query.get_or_404(project_id)
    
    # Check access
    if project.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        # Use Project model's progress calculation (single source of truth)
        project_tasks = Task.query.filter_by(project_id=project.id).all()
        
        return jsonify({
            'success': True,
            'progress_percentage': project.progress_percentage,
            'completed_tasks': len([t for t in project_tasks if t.status == 'Completed']),
            'total_tasks': len(project_tasks)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

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

@app.route('/clients/<int:id>/delete', methods=['POST'])
def delete_client(id):
    client = Client.query.get_or_404(id)
    
    # Check access permission
    if client.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        client_name = client.name
        
        # Get counts for confirmation message
        project_count = Project.query.filter_by(client_id=id).count()
        task_count = Task.query.join(Project).filter_by(client_id=id).count()
        contact_count = len(client.contacts)
        
        # Create activity log before deletion
        create_activity_log(f'Client "{client_name}" deleted (with {project_count} projects, {task_count} tasks, {contact_count} contacts)', session['user_id'])
        
        # Delete all associated projects (which will cascade delete tasks and attachments)
        projects = Project.query.filter_by(client_id=id).all()
        for project in projects:
            # Delete project attachments
            Attachment.query.filter_by(project_id=project.id).delete()
            
            # Delete all tasks and their comments for this project
            tasks = Task.query.filter_by(project_id=project.id).all()
            for task in tasks:
                TaskComment.query.filter_by(task_id=task.id).delete()
                db.session.delete(task)
            
            # Delete the project
            db.session.delete(project)
        
        # Delete any independent tasks for this client
        independent_tasks = Task.query.filter_by(client_id=id, project_id=None).all()
        for task in independent_tasks:
            TaskComment.query.filter_by(task_id=task.id).delete()
            db.session.delete(task)
        
        # Delete client-contact associations
        ClientContact.query.filter_by(client_id=id).delete()
        
        # Delete client attachments
        Attachment.query.filter_by(client_id=id).delete()
        
        # Delete the client itself
        db.session.delete(client)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Client "{client_name}" and all associated data deleted successfully',
            'redirect': '/clients'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting client: {str(e)}'}), 500

@app.route('/clients/<int:id>/mark_inactive', methods=['POST'])
def mark_client_inactive(id):
    client = Client.query.get_or_404(id)
    
    # Check access permission
    if client.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        client_name = client.name
        previous_status = "Active" if client.is_active else "Inactive"
        
        # Toggle active status
        client.is_active = not client.is_active
        new_status = "Active" if client.is_active else "Inactive"
        
        # Update all associated projects to match client status
        projects = Project.query.filter_by(client_id=id).all()
        for project in projects:
            if client.is_active:
                # If activating client, set projects to Active if they were inactive
                if project.status in ['Inactive', 'On Hold']:
                    project.status = 'Active'
            else:
                # If deactivating client, set active projects to On Hold
                if project.status == 'Active':
                    project.status = 'On Hold'
        
        db.session.commit()
        
        # Create activity log
        action = f'Client "{client_name}" marked as {new_status} (was {previous_status})'
        if not client.is_active:
            action += f' - {len(projects)} projects set to On Hold'
        else:
            action += f' - {len(projects)} projects reactivated'
        
        create_activity_log(action, session['user_id'])
        
        return jsonify({
            'success': True, 
            'message': f'Client "{client_name}" marked as {new_status}',
            'new_status': new_status,
            'is_active': client.is_active
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating client status: {str(e)}'}), 500

@app.route('/admin/work_types', methods=['GET'])
def admin_work_types():
    if session.get('user_role') != 'Admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    work_types = WorkType.query.filter_by(firm_id=session['firm_id']).all()
    
    # Get task count by work type (through project relationship)
    work_type_usage = {}
    for wt in work_types:
        task_count = Task.query.join(Project).filter(
            Task.firm_id == session['firm_id'],
            Project.work_type_id == wt.id
        ).count()
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
    
    # Get only contacts associated with clients from this firm
    contacts_query = db.session.query(Contact).join(ClientContact).join(Client).filter(
        Client.firm_id == firm_id
    ).distinct()
    
    firm_contacts = contacts_query.all()
    
    # Add client count for each contact (only count clients from this firm)
    for contact in firm_contacts:
        contact.client_count = db.session.query(ClientContact).join(Client).filter(
            ClientContact.contact_id == contact.id,
            Client.firm_id == firm_id
        ).count()
    
    return render_template('contacts.html', contacts=firm_contacts)

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
    
    # Get client relationships associated with this contact in current firm
    client_relationships = db.session.query(ClientContact).join(Client).filter(
        ClientContact.contact_id == id,
        Client.firm_id == session['firm_id']
    ).all()
    
    # Get available clients (not already associated with this contact)
    associated_client_ids = db.session.query(ClientContact.client_id).filter_by(contact_id=id).subquery()
    available_clients = Client.query.filter(
        Client.firm_id == session['firm_id'],
        ~Client.id.in_(associated_client_ids)
    ).all()
    
    return render_template('view_contact.html', contact=contact, client_relationships=client_relationships, available_clients=available_clients)

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

@app.route('/clients/<int:client_id>/associate_contact', methods=['POST'])
def associate_client_contact(client_id):
    client = Client.query.get_or_404(client_id)
    
    if client.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('clients'))
    
    contact_id = request.form.get('contact_id')
    relationship_type = request.form.get('relationship_type')
    is_primary = request.form.get('is_primary') == '1'
    
    if not contact_id:
        flash('Please select a contact', 'error')
        return redirect(url_for('view_client', id=client_id))
    
    # Check if association already exists
    existing = ClientContact.query.filter_by(client_id=client_id, contact_id=contact_id).first()
    if existing:
        flash('Contact is already associated with this client', 'error')
        return redirect(url_for('view_client', id=client_id))
    
    # If setting as primary, remove primary status from other contacts
    if is_primary:
        ClientContact.query.filter_by(client_id=client_id, is_primary=True).update({'is_primary': False})
    
    # Create new association
    client_contact = ClientContact(
        client_id=client_id,
        contact_id=contact_id,
        relationship_type=relationship_type,
        is_primary=is_primary
    )
    
    db.session.add(client_contact)
    db.session.commit()
    
    contact = Contact.query.get(contact_id)
    create_activity_log(f'Contact "{contact.full_name}" linked to client "{client.name}" as {relationship_type}', session['user_id'])
    flash('Contact linked successfully!', 'success')
    
    return redirect(url_for('view_client', id=client_id))

@app.route('/contacts/<int:contact_id>/link_client', methods=['POST'])
def link_contact_client(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    
    client_id = request.form.get('client_id')
    relationship_type = request.form.get('relationship_type')
    is_primary = request.form.get('is_primary') == '1'
    
    if not client_id:
        flash('Please select a client', 'error')
        return redirect(url_for('view_contact', id=contact_id))
    
    client = Client.query.get_or_404(client_id)
    
    if client.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('contacts'))
    
    # Check if association already exists
    existing = ClientContact.query.filter_by(client_id=client_id, contact_id=contact_id).first()
    if existing:
        flash('Contact is already associated with this client', 'error')
        return redirect(url_for('view_contact', id=contact_id))
    
    # If setting as primary, remove primary status from other contacts for this client
    if is_primary:
        ClientContact.query.filter_by(client_id=client_id, is_primary=True).update({'is_primary': False})
    
    # Create new association
    client_contact = ClientContact(
        client_id=client_id,
        contact_id=contact_id,
        relationship_type=relationship_type,
        is_primary=is_primary
    )
    
    db.session.add(client_contact)
    db.session.commit()
    
    create_activity_log(f'Contact "{contact.full_name}" linked to client "{client.name}" as {relationship_type}', session['user_id'])
    flash('Client linked successfully!', 'success')
    
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


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file uploads for tasks and projects"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    entity_type = request.form.get('entity_type')  # 'task' or 'project'
    entity_id = request.form.get('entity_id')
    
    if not entity_type or not entity_id:
        return jsonify({'success': False, 'message': 'Missing entity information'}), 400
    
    firm_id = session['firm_id']
    
    # Verify entity belongs to firm
    if entity_type == 'task':
        task = Task.query.get_or_404(entity_id)
        if task.project and task.project.firm_id != firm_id:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        elif not task.project and task.firm_id != firm_id:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
    elif entity_type == 'project':
        project = Project.query.get_or_404(entity_id)
        if project.firm_id != firm_id:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
    else:
        return jsonify({'success': False, 'message': 'Invalid entity type'}), 400
    
    # Save file
    attachment, error = save_uploaded_file(file, firm_id, entity_type, entity_id)
    
    if error:
        return jsonify({'success': False, 'message': error}), 400
    
    # Activity log
    entity_name = task.title if entity_type == 'task' else project.name
    create_activity_log(
        f'File "{attachment.original_filename}" uploaded to {entity_type} "{entity_name}"',
        session['user_id'],
        project.id if entity_type == 'project' else (task.project_id if task.project else None),
        task.id if entity_type == 'task' else None
    )
    
    return jsonify({
        'success': True,
        'attachment': {
            'id': attachment.id,
            'original_filename': attachment.original_filename,
            'file_size_formatted': attachment.file_size_formatted,
            'uploaded_at': attachment.uploaded_at.strftime('%m/%d/%Y %I:%M %p'),
            'uploader_name': attachment.uploader.name
        }
    })

@app.route('/attachments/<int:attachment_id>/download')
def download_attachment(attachment_id):
    """Download an attachment"""
    attachment = Attachment.query.get_or_404(attachment_id)
    
    # Check access
    if attachment.firm_id != session['firm_id']:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    if not os.path.exists(attachment.file_path):
        flash('File not found', 'error')
        return redirect(request.referrer or url_for('dashboard'))
    
    # Activity log
    entity_type = 'task' if attachment.task_id else 'project'
    entity_name = attachment.task.title if attachment.task_id else attachment.project.name
    create_activity_log(
        f'File "{attachment.original_filename}" downloaded from {entity_type} "{entity_name}"',
        session['user_id'],
        attachment.project_id if attachment.project_id else (attachment.task.project_id if attachment.task and attachment.task.project else None),
        attachment.task_id
    )
    
    return send_file(
        attachment.file_path,
        as_attachment=True,
        download_name=attachment.original_filename,
        mimetype=attachment.mime_type
    )

@app.route('/attachments/<int:attachment_id>/delete', methods=['POST'])
def delete_attachment(attachment_id):
    """Delete an attachment"""
    attachment = Attachment.query.get_or_404(attachment_id)
    
    # Check access
    if attachment.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        # Delete physical file
        if os.path.exists(attachment.file_path):
            os.remove(attachment.file_path)
        
        # Activity log
        entity_type = 'task' if attachment.task_id else 'project'
        entity_name = attachment.task.title if attachment.task_id else attachment.project.name
        create_activity_log(
            f'File "{attachment.original_filename}" deleted from {entity_type} "{entity_name}"',
            session['user_id'],
            attachment.project_id if attachment.project_id else (attachment.task.project_id if attachment.task and attachment.task.project else None),
            attachment.task_id
        )
        
        # Delete database record
        db.session.delete(attachment)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'File deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/tasks/<int:task_id>/subtasks/create', methods=['POST'])
def create_subtask(task_id):
    """Create a new subtask for a parent task"""
    parent_task = Task.query.get_or_404(task_id)
    
    # Check access
    if parent_task.project and parent_task.project.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    elif not parent_task.project and parent_task.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        title = request.json.get('title', '').strip()
        description = request.json.get('description', '').strip()
        
        if not title:
            return jsonify({'success': False, 'message': 'Title is required'}), 400
        
        # Get next subtask order
        max_order = db.session.query(db.func.max(Task.subtask_order)).filter_by(parent_task_id=task_id).scalar() or 0
        
        # Create subtask
        subtask = Task(
            title=title,
            description=description,
            parent_task_id=task_id,
            subtask_order=max_order + 1,
            project_id=parent_task.project_id,
            firm_id=parent_task.firm_id or session['firm_id'],
            assignee_id=parent_task.assignee_id,  # Default to parent's assignee
            priority=parent_task.priority,  # Inherit priority
            status_id=parent_task.status_id,  # Inherit status system
            status=parent_task.status if not parent_task.status_id else 'Not Started'
        )
        
        db.session.add(subtask)
        db.session.commit()
        
        # Activity log
        create_activity_log(
            f'Subtask "{title}" created for task "{parent_task.title}"',
            session['user_id'],
            parent_task.project_id,
            parent_task.id
        )
        
        return jsonify({
            'success': True,
            'subtask': {
                'id': subtask.id,
                'title': subtask.title,
                'description': subtask.description,
                'status': subtask.current_status,
                'assignee_name': subtask.assignee.name if subtask.assignee else 'Unassigned',
                'created_at': subtask.created_at.strftime('%m/%d/%Y %I:%M %p')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/tasks/<int:task_id>/subtasks/reorder', methods=['POST'])
def reorder_subtasks(task_id):
    """Reorder subtasks within a parent task"""
    parent_task = Task.query.get_or_404(task_id)
    
    # Check access
    if parent_task.project and parent_task.project.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    elif not parent_task.project and parent_task.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        subtask_ids = request.json.get('subtask_ids', [])
        
        # Update order for each subtask
        for index, subtask_id in enumerate(subtask_ids):
            subtask = Task.query.get(subtask_id)
            if subtask and subtask.parent_task_id == task_id:
                subtask.subtask_order = index + 1
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Subtasks reordered successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/tasks/<int:task_id>/convert-to-subtask', methods=['POST'])
def convert_to_subtask(task_id):
    """Convert an existing task to a subtask of another task"""
    task = Task.query.get_or_404(task_id)
    
    # Check access
    if task.project and task.project.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    elif not task.project and task.firm_id != session['firm_id']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        parent_task_id = request.json.get('parent_task_id')
        
        if not parent_task_id:
            return jsonify({'success': False, 'message': 'Parent task ID is required'}), 400
        
        parent_task = Task.query.get(parent_task_id)
        if not parent_task:
            return jsonify({'success': False, 'message': 'Parent task not found'}), 404
        
        # Check that parent task belongs to same firm
        if parent_task.project and parent_task.project.firm_id != session['firm_id']:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        elif not parent_task.project and parent_task.firm_id != session['firm_id']:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Prevent circular relationships
        if parent_task_id == task_id:
            return jsonify({'success': False, 'message': 'Cannot make task a subtask of itself'}), 400
        
        # Check if parent task is already a subtask of this task (prevent circular)
        current = parent_task
        while current.parent_task:
            if current.parent_task.id == task_id:
                return jsonify({'success': False, 'message': 'Cannot create circular subtask relationship'}), 400
            current = current.parent_task
        
        # Get next subtask order
        max_order = db.session.query(db.func.max(Task.subtask_order)).filter_by(parent_task_id=parent_task_id).scalar() or 0
        
        # Convert to subtask
        task.parent_task_id = parent_task_id
        task.subtask_order = max_order + 1
        
        db.session.commit()
        
        # Activity log
        create_activity_log(
            f'Task "{task.title}" converted to subtask of "{parent_task.title}"',
            session['user_id'],
            parent_task.project_id,
            parent_task.id
        )
        
        return jsonify({'success': True, 'message': 'Task converted to subtask successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

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

# CPA Document Checklist Management Routes
@app.route('/checklists')
def document_checklists():
    """CPA view to manage document checklists"""
    firm_id = session['firm_id']
    
    # Get all checklists for the firm
    checklists = DocumentChecklist.query.join(Client).filter(
        Client.firm_id == firm_id
    ).all()
    
    # Get all clients for creating new checklists
    clients = Client.query.filter_by(firm_id=firm_id).all()
    
    return render_template('document_checklists.html', checklists=checklists, clients=clients)

@app.route('/create-checklist', methods=['GET', 'POST'])
def create_checklist():
    """Create a new document checklist"""
    firm_id = session['firm_id']
    
    if request.method == 'POST':
        client_id = request.form.get('client_id')
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        # Verify client belongs to this firm
        client = Client.query.filter_by(id=client_id, firm_id=firm_id).first()
        if not client:
            flash('Invalid client selected', 'error')
            return redirect(url_for('document_checklists'))
        
        checklist = DocumentChecklist(
            client_id=client_id,
            name=name,
            description=description,
            created_by=session['user_id'],
            is_active=True
        )
        
        db.session.add(checklist)
        db.session.commit()
        
        flash(f'Checklist "{name}" created successfully for {client.name}', 'success')
        return redirect(url_for('edit_checklist', checklist_id=checklist.id))
    
    # GET request - show form
    clients = Client.query.filter_by(firm_id=firm_id).all()
    return render_template('create_checklist_modern.html', clients=clients)

@app.route('/edit-checklist/<int:checklist_id>', methods=['GET', 'POST'])
def edit_checklist(checklist_id):
    """Edit a document checklist and its items"""
    firm_id = session['firm_id']
    
    # Get checklist and verify it belongs to this firm
    checklist = DocumentChecklist.query.join(Client).filter(
        DocumentChecklist.id == checklist_id,
        Client.firm_id == firm_id
    ).first_or_404()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        # If no specific action, this is the main form submission (Save Changes button)
        if not action:
            # Update basic checklist info
            checklist.name = request.form.get('name')
            checklist.description = request.form.get('description', '')
            
            # Handle deleted items first
            deleted_item_ids = request.form.getlist('deleted_item_ids[]')
            for item_id in deleted_item_ids:
                if item_id:
                    item = ChecklistItem.query.filter_by(
                        id=item_id, 
                        checklist_id=checklist_id
                    ).first()
                    if item:
                        db.session.delete(item)
            
            # Handle existing items updates
            item_ids = request.form.getlist('item_ids[]')
            item_titles = request.form.getlist('item_titles[]')
            item_descriptions = request.form.getlist('item_descriptions[]')
            item_required = request.form.getlist('item_required[]')
            item_sort_orders = request.form.getlist('item_sort_orders[]')
            
            # Update existing items
            for i, item_id in enumerate(item_ids):
                if item_id and i < len(item_titles):  # Only process if we have an ID and title
                    item = ChecklistItem.query.filter_by(
                        id=item_id, 
                        checklist_id=checklist_id
                    ).first()
                    
                    if item:
                        item.title = item_titles[i] if i < len(item_titles) else item.title
                        item.description = item_descriptions[i] if i < len(item_descriptions) else ''
                        item.is_required = str(i) in item_required
                        item.sort_order = int(item_sort_orders[i]) if i < len(item_sort_orders) and item_sort_orders[i] else item.sort_order
                
                elif not item_id and i < len(item_titles) and item_titles[i].strip():
                    # This is a new item (no ID but has title)
                    max_order = db.session.query(db.func.max(ChecklistItem.sort_order)).filter_by(
                        checklist_id=checklist_id
                    ).scalar() or 0
                    
                    new_item = ChecklistItem(
                        checklist_id=checklist_id,
                        title=item_titles[i],
                        description=item_descriptions[i] if i < len(item_descriptions) else '',
                        is_required=str(i) in item_required,
                        sort_order=int(item_sort_orders[i]) if i < len(item_sort_orders) and item_sort_orders[i] else max_order + 1
                    )
                    db.session.add(new_item)
            
            db.session.commit()
            flash('Checklist and items updated successfully', 'success')
            return redirect(url_for('edit_checklist', checklist_id=checklist_id))
        
        elif action == 'update_checklist':
            checklist.name = request.form.get('name')
            checklist.description = request.form.get('description', '')
            db.session.commit()
            flash('Checklist updated successfully', 'success')
            
        elif action == 'add_item':
            title = request.form.get('title')
            description = request.form.get('description', '')
            is_required = request.form.get('is_required') == 'on'
            
            # Get next sort order
            max_order = db.session.query(db.func.max(ChecklistItem.sort_order)).filter_by(
                checklist_id=checklist_id
            ).scalar() or 0
            
            item = ChecklistItem(
                checklist_id=checklist_id,
                title=title,
                description=description,
                is_required=is_required,
                sort_order=max_order + 1
            )
            
            db.session.add(item)
            db.session.commit()
            flash(f'Document item "{title}" added successfully', 'success')
            
        elif action == 'delete_item':
            item_id = request.form.get('item_id')
            item = ChecklistItem.query.filter_by(
                id=item_id, 
                checklist_id=checklist_id
            ).first()
            if item:
                db.session.delete(item)
                db.session.commit()
                flash('Document item deleted successfully', 'success')
        
        return redirect(url_for('edit_checklist', checklist_id=checklist_id))
    
    return render_template('edit_checklist.html', checklist=checklist)

@app.route('/client-access-setup/<int:client_id>', methods=['GET', 'POST'])
def client_access_setup(client_id):
    """Set up client portal access for a client"""
    firm_id = session['firm_id']
    
    # Verify client belongs to this firm
    client = Client.query.filter_by(id=client_id, firm_id=firm_id).first_or_404()
    
    # Check if client user already exists
    client_user = ClientUser.query.filter_by(client_id=client_id).first()
    
    if request.method == 'POST':
        action = request.form.get('action', 'create')
        
        if action == 'create' and not client_user:
            # Create new client user
            email = request.form.get('email') or client.email
            
            # Ensure we have an email (use client email as fallback)
            if not email:
                flash('Client must have an email address to create portal access. Please update client information first.', 'error')
                return redirect(url_for('client_access_setup', client_id=client_id))
            
            client_user = ClientUser(
                client_id=client_id,
                email=email,
                is_active=True
            )
            # Generate 8-character access code
            client_user.generate_access_code()
            
            db.session.add(client_user)
            db.session.commit()
            
            flash(f'Client portal access created successfully! Access code: {client_user.access_code}', 'success')
            
        elif action == 'regenerate' and client_user:
            # Regenerate access code
            old_code = client_user.access_code
            client_user.generate_access_code()
            db.session.commit()
            
            flash(f'New access code generated: {client_user.access_code}', 'success')
            
        elif action == 'toggle' and client_user:
            # Toggle active status
            client_user.is_active = not client_user.is_active
            db.session.commit()
            
            status = 'activated' if client_user.is_active else 'deactivated'
            flash(f'Client portal access {status}', 'success')
        
        # Refresh client_user object after changes
        if client_user:
            db.session.refresh(client_user)
    
    return render_template('client_access_setup.html', client=client, client_user=client_user)

@app.route('/checklist-dashboard/<int:checklist_id>')
def checklist_dashboard(checklist_id):
    """Modern dashboard view for a specific checklist"""
    firm_id = session['firm_id']
    
    # Get checklist and verify it belongs to this firm
    checklist = DocumentChecklist.query.join(Client).filter(
        DocumentChecklist.id == checklist_id,
        Client.firm_id == firm_id
    ).first_or_404()
    
    return render_template('checklist_dashboard.html', checklist=checklist)

@app.route('/download-document/<int:document_id>')
def download_document(document_id):
    """Download a client-uploaded document"""
    firm_id = session['firm_id']
    
    # Get document and verify access
    document = ClientDocument.query.join(ChecklistItem).join(DocumentChecklist).join(Client).filter(
        ClientDocument.id == document_id,
        Client.firm_id == firm_id
    ).first_or_404()
    
    if not os.path.exists(document.file_path):
        flash('File not found', 'error')
        return redirect(request.referrer or url_for('document_checklists'))
    
    return send_file(
        document.file_path,
        as_attachment=True,
        download_name=document.original_filename,
        mimetype=document.mime_type
    )

@app.route('/uploaded-documents')
def uploaded_documents():
    """View all uploaded documents across all checklists"""
    firm_id = session['firm_id']
    
    # Get all uploaded documents for this firm
    documents = ClientDocument.query.join(ChecklistItem).join(DocumentChecklist).join(Client).filter(
        Client.firm_id == firm_id
    ).order_by(ClientDocument.uploaded_at.desc()).all()
    
    return render_template('uploaded_documents.html', documents=documents)

@app.route('/api/checklist-stats/<int:checklist_id>')
def checklist_stats_api(checklist_id):
    """API endpoint for real-time checklist statistics"""
    firm_id = session['firm_id']
    
    checklist = DocumentChecklist.query.join(Client).filter(
        DocumentChecklist.id == checklist_id,
        Client.firm_id == firm_id
    ).first_or_404()
    
    stats = {
        'total_items': len(checklist.items),
        'pending': checklist.pending_items_count,
        'uploaded': checklist.uploaded_items_count,
        'completed': checklist.completed_items_count,
        'progress': checklist.progress_percentage,
        'last_activity': None
    }
    
    # Get last activity
    if checklist.items:
        latest_update = max([item.updated_at for item in checklist.items if item.updated_at])
        if latest_update:
            stats['last_activity'] = latest_update.strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify(stats)

# Client Portal Authentication Routes
@app.route('/client-portal')
@app.route('/client-login')
def client_login():
    """Client portal login page"""
    return render_template('client_login.html')

@app.route('/client-authenticate', methods=['POST'])
def client_authenticate():
    """Authenticate client user"""
    access_code = request.form.get('access_code', '').strip()
    client_user = ClientUser.query.filter_by(access_code=access_code, is_active=True).first()
    
    if client_user:
        session['client_user_id'] = client_user.id
        session['client_id'] = client_user.client_id
        session['client_email'] = client_user.email
        client_user.last_login = datetime.utcnow()
        db.session.commit()
        
        return redirect(url_for('client_dashboard'))
    else:
        flash('Invalid access code', 'error')
        return redirect(url_for('client_login'))

@app.route('/client-dashboard')
def client_dashboard():
    """Client portal dashboard"""
    if 'client_user_id' not in session:
        return redirect(url_for('client_login'))
    
    client_id = session['client_id']
    client = Client.query.get(client_id)
    
    # Get active checklists for this client
    checklists = DocumentChecklist.query.filter_by(
        client_id=client_id, 
        is_active=True
    ).all()
    
    return render_template('client_dashboard_modern.html', client=client, checklists=checklists)

@app.route('/client-logout')
def client_logout():
    """Client logout"""
    session.pop('client_user_id', None)
    session.pop('client_id', None)
    session.pop('client_email', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('client_login'))

@app.route('/client-upload/<int:item_id>', methods=['POST'])
def client_upload_document(item_id):
    """Handle client document upload"""
    if 'client_user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    client_id = session['client_id']
    
    # Verify the checklist item belongs to this client
    item = ChecklistItem.query.join(DocumentChecklist).filter(
        ChecklistItem.id == item_id,
        DocumentChecklist.client_id == client_id
    ).first()
    
    if not item:
        return jsonify({'success': False, 'message': 'Invalid document item'}), 404
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'File type not allowed'}), 400
    
    try:
        # Generate unique filename
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        # Create client-specific subdirectory
        client_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], f'client_{client_id}')
        os.makedirs(client_upload_dir, exist_ok=True)
        
        file_path = os.path.join(client_upload_dir, unique_filename)
        
        # Save file
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        
        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(original_filename)
        
        # Delete any existing document for this item
        existing_doc = ClientDocument.query.filter_by(
            client_id=client_id,
            checklist_item_id=item_id
        ).first()
        
        if existing_doc:
            # Remove old file
            if os.path.exists(existing_doc.file_path):
                os.remove(existing_doc.file_path)
            db.session.delete(existing_doc)
        
        # Create new document record
        document = ClientDocument(
            client_id=client_id,
            checklist_item_id=item_id,
            filename=unique_filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            uploaded_by_client=True
        )
        
        db.session.add(document)
        
        # Update item status
        item.status = 'uploaded'
        item.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'File uploaded successfully',
            'filename': original_filename
        })
        
    except Exception as e:
        db.session.rollback()
        # Clean up file if database operation fails
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/client-update-status/<int:item_id>', methods=['POST'])
def client_update_status(item_id):
    """Update document item status (already provided, not applicable)"""
    if 'client_user_id' not in session:
        flash('Not authenticated', 'error')
        return redirect(url_for('client_login'))
    
    client_id = session['client_id']
    new_status = request.form.get('status')
    
    if new_status not in ['already_provided', 'not_applicable', 'pending']:
        flash('Invalid status selected', 'error')
        return redirect(url_for('client_dashboard'))
    
    # Verify the checklist item belongs to this client
    item = ChecklistItem.query.join(DocumentChecklist).filter(
        ChecklistItem.id == item_id,
        DocumentChecklist.client_id == client_id
    ).first()
    
    if not item:
        flash('Document not found', 'error')
        return redirect(url_for('client_dashboard'))
    
    try:
        # If changing from uploaded status, remove the uploaded file
        if item.status == 'uploaded' and new_status != 'uploaded':
            existing_doc = ClientDocument.query.filter_by(
                client_id=client_id,
                checklist_item_id=item_id
            ).first()
            
            if existing_doc:
                # Remove file
                if os.path.exists(existing_doc.file_path):
                    os.remove(existing_doc.file_path)
                db.session.delete(existing_doc)
        
        # Update status
        item.status = new_status
        item.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        status_messages = {
            'already_provided': 'Marked as already provided',
            'not_applicable': 'Marked as not applicable',
            'pending': 'Reset to pending'
        }
        
        flash(status_messages.get(new_status, 'Status updated'), 'success')
        return redirect(url_for('client_dashboard'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating status: {str(e)}', 'error')
        return redirect(url_for('client_dashboard'))


# ====================================
# AI DOCUMENT ANALYSIS ROUTES
# ====================================

@app.route('/analyze-document/<int:document_id>', methods=['POST'])
def analyze_document(document_id):
    """Analyze a client document using AI (Azure + Gemini)"""
    if not AI_SERVICES_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'AI services not available. Please configure environment and install dependencies.'
        }), 503
    
    firm_id = session['firm_id']
    
    try:
        # Get the document and verify access
        document = db.session.query(ClientDocument).join(ChecklistItem).join(DocumentChecklist).join(Client).filter(
            ClientDocument.id == document_id,
            Client.firm_id == firm_id
        ).first()
        
        if not document:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        
        # Initialize document processor
        processor = DocumentProcessor()
        
        # Create FileUpload object for processing
        file_upload = FileUpload(
            filename=document.original_filename,
            content_type=document.mime_type,
            size=document.file_size,
            file_path=Path(document.file_path)
        )
        
        # Process document (this will be async in production)
        # For now, return success to show the UI works
        return jsonify({
            'success': True,
            'message': 'Document analysis started',
            'document_id': document_id,
            'status': 'processing'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Analysis failed: {str(e)}'
        }), 500

@app.route('/api/document-analysis/<int:document_id>', methods=['GET', 'POST'])
def get_document_analysis(document_id):
    """Get or trigger analysis for a document"""
    try:
        print(f"=== STARTING DOCUMENT ANALYSIS FOR ID: {document_id} ===")
        
        if 'firm_id' not in session:
            print("✗ No firm_id in session")
            return jsonify({'error': 'No firm session found'}), 401
            
        firm_id = session['firm_id']
        print(f"✓ Firm ID: {firm_id}")
    except Exception as session_error:
        print(f"✗ Session error: {session_error}")
        return jsonify({'error': f'Session error: {str(session_error)}'}), 500
    
    # Get the document and verify access
    try:
        print(f"Querying database for document {document_id}")
        document = db.session.query(ClientDocument).join(ChecklistItem).join(DocumentChecklist).join(Client).filter(
            ClientDocument.id == document_id,
            Client.firm_id == firm_id
        ).first()
        
        if not document:
            print(f"✗ Document {document_id} not found for firm {firm_id}")
            return jsonify({'error': 'Document not found'}), 404
            
        print(f"✓ Found document: {document.original_filename}")
        print(f"✓ Document path: {document.file_path}")
        
    except Exception as db_error:
        print(f"✗ Database query error: {db_error}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Database error: {str(db_error)}'}), 500
    
    # Check for force_reanalysis parameter
    force_reanalysis = request.args.get('force_reanalysis', 'false').lower() == 'true'
    
    # Check if AI analysis has already been completed (unless forcing re-analysis)
    if not force_reanalysis and document.ai_analysis_completed and document.ai_analysis_results:
        try:
            import json
            cached_results = json.loads(document.ai_analysis_results)
            cached_results['cached'] = True
            cached_results['analysis_timestamp'] = document.ai_analysis_timestamp.isoformat() if document.ai_analysis_timestamp else None
            return jsonify(cached_results)
        except (json.JSONDecodeError, AttributeError):
            # If cached results are corrupted, proceed with new analysis
            pass
    
    try:
        print(f"Starting analysis for document {document_id}")
        
        # Import services directly (simpler approach)
        try:
            from backend.services.azure_service import AzureDocumentService
            print("✓ Azure service imported")
        except Exception as import_error:
            print(f"✗ Failed to import Azure service: {import_error}")
            return jsonify({'error': f'Azure service import failed: {str(import_error)}'}), 500
            
        try:
            from backend.services.gemini_service import GeminiDocumentService
            print("✓ Gemini service imported")
        except Exception as import_error:
            print(f"✗ Failed to import Gemini service: {import_error}")
            # Continue without Gemini if it fails
            GeminiDocumentService = None
        
        import asyncio
        
        # Check if document file exists
        print(f"Checking document file: {document.file_path}")
        if not os.path.exists(document.file_path):
            print(f"✗ Document file not found: {document.file_path}")
            return jsonify({'error': 'Document file not found'}), 404
        print(f"✓ Document file exists: {os.path.getsize(document.file_path)} bytes")
        
        # Initialize services
        try:
            azure_service = AzureDocumentService()
            print("✓ Azure service initialized")
        except Exception as init_error:
            print(f"✗ Failed to initialize Azure service: {init_error}")
            return jsonify({'error': f'Azure service initialization failed: {str(init_error)}'}), 500
        
        gemini_service = None
        if GeminiDocumentService:
            try:
                gemini_service = GeminiDocumentService()
                print("✓ Gemini service initialized")
            except Exception as init_error:
                print(f"⚠ Gemini service initialization failed: {init_error}")
        
        # Process with Azure directly
        print(f"Analyzing document {document_id}: {document.original_filename}")
        azure_result_raw = None
        try:
            azure_result_raw = azure_service.analyze_document_from_file(document.file_path)
            print(f"✓ Azure analysis completed")
            print(f"Azure analysis result keys: {list(azure_result_raw.keys()) if azure_result_raw else 'None'}")
        except Exception as azure_error:
            print(f"⚠ Azure analysis failed (continuing with Gemini only): {azure_error}")
            # Continue without Azure - we'll use Gemini only
            azure_result_raw = None
        
        # Process with Gemini
        gemini_result_raw = None
        if gemini_service:
            try:
                print("Starting Gemini analysis...")
                with open(document.file_path, 'rb') as f:
                    content = f.read()
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    # Run the synchronous Gemini method in executor
                    gemini_result_raw = loop.run_until_complete(
                        loop.run_in_executor(
                            None,
                            gemini_service.analyze_document,
                            content,
                            document.original_filename,
                            document.mime_type or 'application/pdf'
                        )
                    )
                    print("✓ Gemini analysis completed")
                except Exception as gemini_error:
                    print(f"⚠ Gemini analysis error: {gemini_error}")
                    gemini_result_raw = None
                finally:
                    loop.close()
            except Exception as gemini_outer_error:
                print(f"⚠ Gemini processing error: {gemini_outer_error}")
                gemini_result_raw = None
        else:
            print("⚠ Gemini service not available, skipping Gemini analysis")
            
        # Convert results to our expected format
        azure_result = {}
        gemini_result = {}
        
        # Process Azure results
        if azure_result_raw:
            # Save the complete Azure raw response (contains polygon coordinates for visualization)
            azure_result = azure_result_raw.copy()
            
            # Also add extracted key-value pairs for easy display
            if 'key_value_pairs' not in azure_result:
                azure_result['key_value_pairs'] = []
            
            # Extract key-value pairs from Azure documents for display
            if 'documents' in azure_result and azure_result['documents']:
                for doc in azure_result['documents']:
                    if 'fields' in doc:
                        for field_name, field_data in doc['fields'].items():
                            field_value = 'N/A'
                            if isinstance(field_data, dict):
                                field_value = field_data.get('content') or field_data.get('value') or 'N/A'
                            azure_result['key_value_pairs'].append({
                                'key': field_name.replace('_', ' ').title(),
                                'value': str(field_value)
                            })
            
            # Ensure confidence score
            if 'confidence' not in azure_result:
                azure_result['confidence'] = 0.8  # Default confidence
                
            print(f"Azure result structure saved: {list(azure_result.keys())}")
            if 'documents' in azure_result:
                print(f"Found {len(azure_result['documents'])} documents with polygon data")
        else:
            # Create empty Azure result structure for compatibility
            azure_result = {
                'key_value_pairs': [],
                'confidence': 0.0,
                'documents': [],
                'status': 'Azure analysis unavailable (using Gemini only)'
            }
            print("⚠ Using empty Azure result structure (Azure API unavailable)")
                
        # Process Gemini results  
        if gemini_result_raw:
            gemini_result = {
                'document_type': getattr(gemini_result_raw, 'document_category', 'Unknown'),
                'summary': getattr(gemini_result_raw, 'document_analysis_summary', 'No summary available'),
                'key_findings': [],
                'recommendations': []
            }
            
            # Extract key findings
            if hasattr(gemini_result_raw, 'extracted_key_info') and gemini_result_raw.extracted_key_info:
                for key, value in gemini_result_raw.extracted_key_info.items():
                    if value:
                        gemini_result['key_findings'].append(f"{key.replace('_', ' ').title()}: {value}")
            
            # Extract recommendations
            if hasattr(gemini_result_raw, 'recommendations') and gemini_result_raw.recommendations:
                gemini_result['recommendations'] = gemini_result_raw.recommendations
            
        # Prepare results to save
        analysis_results = {
            'document_id': document_id,
            'filename': document.original_filename,
            'status': 'completed',
            'azure_result': azure_result,
            'gemini_result': gemini_result,
            'visualization_available': True,
            'processing_notes': f'Processed with Azure: {"Yes" if azure_result_raw else "No"}, Gemini: {"Yes" if gemini_result_raw else "No"}'
        }
        
        print(f"✓ Analysis results prepared")
        print(f"Azure data: {'Yes' if azure_result_raw else 'No'}")
        print(f"Gemini data: {'Yes' if gemini_result_raw else 'No'}")
        
        # Save analysis results to database with proper transaction handling
        import json
        from datetime import datetime
        
        try:
            print("Saving to database...")
            document.ai_analysis_completed = True
            document.ai_analysis_results = json.dumps(analysis_results)
            document.ai_analysis_timestamp = datetime.utcnow()
            document.ai_document_type = gemini_result.get('document_type', 'Unknown')
            document.ai_confidence_score = azure_result.get('confidence', 0.0)
            
            db.session.commit()
            print("✓ Database save successful")
            
        except Exception as db_error:
            print(f"⚠ Database update error: {db_error}")
            db.session.rollback()
            # Still return results even if database save fails
        
        print("✓ Analysis completed successfully")
        return jsonify(analysis_results)
        
    except Exception as e:
        print(f"✗ FATAL ERROR in document analysis: {e}")
        import traceback
        traceback.print_exc()
        
        # Ensure session is clean for future requests
        try:
            db.session.rollback()
        except:
            pass
        
        return jsonify({
            'error': 'Document analysis failed',
            'details': str(e),
            'message': 'Unable to process document. Please ensure Azure and Gemini API keys are configured correctly.'
        }), 500

@app.route('/api/analyze-checklist/<int:checklist_id>', methods=['POST'])
def analyze_checklist_api(checklist_id):
    """API endpoint to trigger checklist-level AI analysis"""
    try:
        firm_id = session['firm_id']
        
        # Get checklist and verify it belongs to this firm
        checklist = DocumentChecklist.query.join(Client).filter(
            DocumentChecklist.id == checklist_id,
            Client.firm_id == firm_id
        ).first()
        
        if not checklist:
            return jsonify({'error': 'Checklist not found'}), 404
        
        if checklist.ai_analysis_completed:
            return jsonify({
                'status': 'already_completed',
                'message': 'Checklist analysis already completed',
                'results': checklist.get_ai_analysis_summary()
            })
        
        # Perform the analysis
        perform_checklist_ai_analysis(checklist)
        
        return jsonify({
            'status': 'completed',
            'message': 'Checklist analysis completed successfully',
            'results': checklist.get_ai_analysis_summary()
        })
        
    except Exception as e:
        print(f"Checklist analysis API error: {e}")
        try:
            db.session.rollback()
        except:
            pass
        
        return jsonify({
            'error': 'Checklist analysis failed',
            'details': str(e)
        }), 500

@app.route('/api/export-checklist-analysis/<int:checklist_id>', methods=['GET'])
def export_checklist_analysis_api(checklist_id):
    """Export all analysis results from a checklist in JSON format"""
    try:
        firm_id = session['firm_id']
        
        # Get checklist and verify it belongs to this firm
        checklist = DocumentChecklist.query.join(Client).filter(
            DocumentChecklist.id == checklist_id,
            Client.firm_id == firm_id
        ).first()
        
        if not checklist:
            return jsonify({'error': 'Checklist not found'}), 404
        
        # Collect all analyzed documents from the checklist
        analyzed_documents = []
        for item in checklist.items:
            for document in item.client_documents:
                if document.ai_analysis_completed and document.ai_analysis_results:
                    try:
                        # Parse the saved analysis results (they're stored as JSON string)
                        import json
                        if isinstance(document.ai_analysis_results, str):
                            saved_results = json.loads(document.ai_analysis_results)
                        else:
                            saved_results = document.ai_analysis_results
                        
                        doc_data = {
                            'filename': document.original_filename,
                            'processing_status': 'completed',
                            'document_id': document.id,
                            'created_at': document.uploaded_at.isoformat() if document.uploaded_at else None,
                            'processing_notes': f"Cached analysis from {document.ai_analysis_timestamp.strftime('%m/%d/%Y %I:%M %p') if document.ai_analysis_timestamp else 'unknown time'}",
                            
                            # Include just the essential Azure and Gemini results (no flattening)
                            'azure_result': saved_results.get('azure_result', {}),
                            'gemini_result': saved_results.get('gemini_result', {}),
                            
                            'validation_errors_count': 0
                        }
                        
                        analyzed_documents.append(doc_data)
                        
                    except (json.JSONDecodeError, AttributeError, KeyError) as e:
                        print(f"Error parsing saved analysis for document {document.id}: {e}")
                        # Include basic info even if parsing fails
                        doc_data = {
                            'filename': document.original_filename,
                            'processing_status': 'error',
                            'document_id': document.id,
                            'error': f'Failed to parse saved analysis: {str(e)}'
                        }
                        analyzed_documents.append(doc_data)
        
        if not analyzed_documents:
            return jsonify({
                'error': 'No analyzed documents found',
                'message': 'Please analyze documents before exporting'
            }), 400
        
        # Create export data structure in the same format as the original JavaScript export
        export_data = {
            'export_date': datetime.utcnow().isoformat(),
            'document_count': len(analyzed_documents),
            'documents': analyzed_documents
        }
        
        # Create filename
        safe_client_name = "".join(c for c in checklist.client.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"analysis_export_{safe_client_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Return JSON as a direct download (not through jsonify which adds HTML wrapper)
        from flask import Response
        import json
        
        json_str = json.dumps(export_data, indent=2)
        
        response = Response(
            json_str,
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )
        
        return response
        
    except Exception as e:
        print(f"Analysis export error: {e}")
        return jsonify({
            'error': 'Export failed',
            'details': str(e)
        }), 500

@app.route('/api/generate-income-worksheet/<int:checklist_id>', methods=['POST'])
def generate_income_worksheet_api(checklist_id):
    """Generate income worksheet CSV from all documents in a checklist"""
    try:
        firm_id = session['firm_id']
        
        # Get checklist and verify it belongs to this firm
        checklist = DocumentChecklist.query.join(Client).filter(
            DocumentChecklist.id == checklist_id,
            Client.firm_id == firm_id
        ).first()
        
        if not checklist:
            return jsonify({'error': 'Checklist not found'}), 404
        
        # Collect all uploaded documents from the checklist
        documents_data = []
        for item in checklist.items:
            for document in item.client_documents:
                if os.path.exists(document.file_path):
                    documents_data.append({
                        'id': document.id,
                        'file_path': document.file_path,
                        'filename': document.original_filename,
                        'mime_type': document.mime_type
                    })
        
        if not documents_data:
            return jsonify({
                'error': 'No documents found in checklist',
                'message': 'Please upload documents before generating income worksheet'
            }), 400
        
        # Import the income worksheet service
        from backend.services.income_worksheet_service import IncomeWorksheetService
        from backend.models.document import FileUpload
        from pathlib import Path
        import asyncio
        
        # Convert documents to FileUpload objects
        file_uploads = []
        for doc_data in documents_data:
            file_upload = FileUpload(
                filename=doc_data['filename'],
                content_type=doc_data['mime_type'] or 'application/pdf',
                size=os.path.getsize(doc_data['file_path']),
                file_path=Path(doc_data['file_path'])
            )
            file_uploads.append(file_upload)
        
        # Generate income worksheet
        worksheet_service = IncomeWorksheetService()
        client_name = checklist.client.name
        
        # Run the async worksheet generation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                worksheet_service.generate_income_worksheet(file_uploads, client_name)
            )
            
            if not result['success']:
                return jsonify({
                    'error': 'Income worksheet generation failed',
                    'details': result.get('error', 'Unknown error'),
                    'message': 'Unable to extract tax data from documents'
                }), 500
            
            # Save worksheet to database (replace existing if any)
            try:
                import json
                
                # Check if worksheet already exists for this checklist
                existing_worksheet = IncomeWorksheet.query.filter_by(checklist_id=checklist_id).first()
                
                if existing_worksheet:
                    # Update existing worksheet
                    existing_worksheet.filename = result['filename']
                    existing_worksheet.csv_content = result['csv_content']
                    existing_worksheet.document_count = result['document_count']
                    existing_worksheet.generated_at = datetime.utcnow()
                    existing_worksheet.generated_by = session['user_id']
                    existing_worksheet.validation_results = json.dumps(result['validation'])
                    existing_worksheet.ai_analysis_version = '1.0'
                    
                    worksheet = existing_worksheet
                    action = 'updated'
                else:
                    # Create new worksheet
                    worksheet = IncomeWorksheet(
                        checklist_id=checklist_id,
                        filename=result['filename'],
                        csv_content=result['csv_content'],
                        document_count=result['document_count'],
                        generated_by=session['user_id'],
                        validation_results=json.dumps(result['validation']),
                        ai_analysis_version='1.0'
                    )
                    db.session.add(worksheet)
                    action = 'created'
                
                db.session.commit()
                
                # Return the CSV content and metadata with save info
                return jsonify({
                    'success': True,
                    'csv_content': result['csv_content'],
                    'filename': result['filename'],
                    'document_count': result['document_count'],
                    'validation': result['validation'],
                    'generated_at': result['generated_at'],
                    'client_name': client_name,
                    'checklist_name': checklist.name,
                    'saved': True,
                    'worksheet_id': worksheet.id,
                    'action': action,
                    'file_size': worksheet.file_size_formatted
                })
                
            except Exception as save_error:
                print(f"Error saving worksheet to database: {save_error}")
                # Still return the CSV content even if save fails
                return jsonify({
                    'success': True,
                    'csv_content': result['csv_content'],
                    'filename': result['filename'],
                    'document_count': result['document_count'],
                    'validation': result['validation'],
                    'generated_at': result['generated_at'],
                    'client_name': client_name,
                    'checklist_name': checklist.name,
                    'saved': False,
                    'save_error': str(save_error)
                })
            
        finally:
            loop.close()
            
    except Exception as e:
        print(f"Income worksheet generation error: {e}")
        try:
            db.session.rollback()
        except:
            pass
        
        return jsonify({
            'error': 'Income worksheet generation failed',
            'details': str(e),
            'message': 'Unable to process documents. Please ensure all documents are valid tax forms.'
        }), 500

@app.route('/download-income-worksheet/<int:checklist_id>')
def download_income_worksheet(checklist_id):
    """Download income worksheet CSV file"""
    try:
        # Generate the worksheet using the API endpoint logic
        from flask import Response
        
        # Call the generation API internally
        with app.test_request_context():
            session['firm_id'] = session.get('firm_id')
            session['user_id'] = session.get('user_id')
            
            api_response = generate_income_worksheet_api(checklist_id)
            
            if api_response[1] != 200:  # Check status code
                flash('Failed to generate income worksheet', 'error')
                return redirect(url_for('checklist_dashboard', checklist_id=checklist_id))
            
            result = api_response[0].get_json()
            
            if not result['success']:
                flash(f'Income worksheet generation failed: {result.get("error", "Unknown error")}', 'error')
                return redirect(url_for('checklist_dashboard', checklist_id=checklist_id))
            
            # Create CSV response
            csv_content = result['csv_content']
            filename = result['filename']
            
            return Response(
                csv_content,
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Type': 'text/csv; charset=utf-8'
                }
            )
            
    except Exception as e:
        print(f"Error downloading income worksheet: {e}")
        flash('Failed to download income worksheet', 'error')
        return redirect(url_for('checklist_dashboard', checklist_id=checklist_id))

@app.route('/api/saved-income-worksheet/<int:checklist_id>')
def get_saved_income_worksheet(checklist_id):
    """Get saved income worksheet for a checklist"""
    try:
        firm_id = session['firm_id']
        
        # Get checklist and verify it belongs to this firm
        checklist = DocumentChecklist.query.join(Client).filter(
            DocumentChecklist.id == checklist_id,
            Client.firm_id == firm_id
        ).first()
        
        if not checklist:
            return jsonify({'error': 'Checklist not found'}), 404
        
        # Get saved worksheet
        worksheet = IncomeWorksheet.query.filter_by(checklist_id=checklist_id).first()
        
        if not worksheet:
            return jsonify({'saved': False, 'message': 'No saved worksheet found'})
        
        return jsonify({
            'saved': True,
            'worksheet_id': worksheet.id,
            'filename': worksheet.filename,
            'document_count': worksheet.document_count,
            'generated_at': worksheet.generated_at.isoformat() if worksheet.generated_at else None,
            'file_size': worksheet.file_size_formatted,
            'is_recent': worksheet.is_recent,
            'generator_name': worksheet.generator.name if worksheet.generator else 'Unknown',
            'validation': worksheet.get_validation_data()
        })
        
    except Exception as e:
        print(f"Error retrieving saved worksheet: {e}")
        return jsonify({'error': 'Failed to retrieve saved worksheet'}), 500

@app.route('/download-saved-worksheet/<int:worksheet_id>')
def download_saved_worksheet(worksheet_id):
    """Download a saved income worksheet by ID"""
    try:
        firm_id = session['firm_id']
        
        # Get worksheet and verify access through checklist
        worksheet = IncomeWorksheet.query.join(DocumentChecklist).join(Client).filter(
            IncomeWorksheet.id == worksheet_id,
            Client.firm_id == firm_id
        ).first()
        
        if not worksheet:
            flash('Saved worksheet not found', 'error')
            return redirect(url_for('document_checklists'))
        
        from flask import Response
        
        return Response(
            worksheet.csv_content,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="{worksheet.filename}"',
                'Content-Type': 'text/csv; charset=utf-8'
            }
        )
        
    except Exception as e:
        print(f"Error downloading saved worksheet: {e}")
        flash('Failed to download saved worksheet', 'error')
        return redirect(url_for('document_checklists'))

@app.route('/create-document-visualization/<int:document_id>', methods=['POST'])
def create_document_visualization(document_id):
    """Create a visualization of a document with field detection annotations"""
    try:
        firm_id = session['firm_id']
        
        # Get the document and verify access
        document = db.session.query(ClientDocument).join(ChecklistItem).join(DocumentChecklist).join(Client).filter(
            ClientDocument.id == document_id,
            Client.firm_id == firm_id
        ).first()
        
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        # Check if document file exists
        if not os.path.exists(document.file_path):
            return jsonify({
                'success': False, 
                'error': 'Document file not found on server'
            }), 404
        
        # Setup output paths
        output_dir = Path('static/visualizations')
        output_dir.mkdir(exist_ok=True, parents=True)
        output_path = output_dir / f'document_{document_id}_annotated.png'
        
        # Check for recent cached version (1 hour cache)
        if output_path.exists():
            file_age = time.time() - output_path.stat().st_mtime
            if file_age < 3600:  # 1 hour
                return jsonify({
                    'success': True,
                    'visualization_url': f'/document-visualization/{document_id}',
                    'message': 'Visualization loaded from cache'
                })
            else:
                # Remove old cache
                output_path.unlink(missing_ok=True)
        
        # Import services
        try:
            from backend.services.azure_service import AzureDocumentService
            print("Azure service imported successfully")
        except Exception as import_error:
            print(f"Failed to import Azure service: {import_error}")
            return jsonify({
                'success': False,
                'error': f'Azure service import failed: {str(import_error)}'
            }), 500
            
        try:
            from backend.services.document_visualizer import DocumentVisualizer
            print("Document visualizer imported successfully")
        except Exception as import_error:
            print(f"Failed to import Document visualizer: {import_error}")
            return jsonify({
                'success': False,
                'error': f'Document visualizer import failed: {str(import_error)}'
            }), 500
        
        # Initialize services
        azure_service = AzureDocumentService()
        visualizer = DocumentVisualizer({
            'visualization_type': 'tick',
            'annotation_color': (0, 255, 0),  # Green ticks (BGR)
            'tick_size': 20,
            'annotation_thickness': 3,
            'show_label': False
        })
        
        # Use cached Azure analysis results for visualization (contains polygon coordinates)
        azure_result = None
        if document.ai_analysis_completed and document.ai_analysis_results:
            try:
                import json
                cached_results = json.loads(document.ai_analysis_results)
                if cached_results.get('azure_result'):
                    azure_result = cached_results['azure_result']
                    print(f"Using cached Azure results for visualization (document {document_id})")
                    print(f"Cached Azure result keys: {list(azure_result.keys()) if azure_result else 'None'}")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error parsing cached Azure results: {e}")
        
        # If no cached results available, cannot create visualization
        if not azure_result:
            return jsonify({
                'success': False,
                'error': 'No cached Azure analysis results available for visualization. Please analyze the document first using "Analyze All Documents".'
            }), 400
        
        # Check for required document structure with polygon data
        if not azure_result.get('documents') or not azure_result['documents']:
            return jsonify({
                'success': False,
                'error': 'No document structure found in cached results. Polygon coordinate data needed for visualization.'
            }), 400
        
        # Format result for visualizer
        formatted_result = {
            'documents': azure_result['documents']
        }
        
        print(f"Using cached Azure data with {len(azure_result['documents'])} documents for visualization")
        
        # Handle PDF to image conversion if needed
        image_path = document.file_path
        temp_image_path = None
        
        # Check if document is PDF and needs conversion
        if document.mime_type == 'application/pdf' or document.file_path.lower().endswith('.pdf'):
            try:
                from pdf2image import convert_from_path
                # Convert first page to image
                pages = convert_from_path(document.file_path, first_page=1, last_page=1, dpi=200)
                if pages:
                    temp_dir = Path('static/visualizations')
                    temp_dir.mkdir(exist_ok=True, parents=True)
                    temp_image_path = temp_dir / f'document_{document_id}_temp.png'
                    pages[0].save(temp_image_path, 'PNG')
                    image_path = str(temp_image_path)
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Could not convert PDF to image for visualization'
                    }), 500
            except ImportError:
                return jsonify({
                    'success': False,
                    'error': 'PDF conversion not available - pdf2image package required'
                }), 500
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'PDF conversion failed: {str(e)}'
                }), 500
        
        # Create annotated visualization
        try:
            print(f"Creating visualization for document {document_id}")
            print(f"Image path: {image_path}")
            print(f"Document structure has {len(formatted_result['documents'][0].get('fields', {}))} fields")
            
            annotated_path = visualizer.create_visualization(
                image_path=image_path,
                api_result=formatted_result,
                output_path=str(output_path)
            )
            
            print(f"Visualization created: {annotated_path}")
            
        except Exception as viz_error:
            print(f"Visualization creation error: {viz_error}")
            import traceback
            traceback.print_exc()
            
            # Clean up temp file if created
            if temp_image_path and temp_image_path.exists():
                temp_image_path.unlink(missing_ok=True)
                
            return jsonify({
                'success': False,
                'error': f'Failed to create visualization: {str(viz_error)}'
            }), 500
        
        # Clean up temp file if created
        if temp_image_path and temp_image_path.exists():
            temp_image_path.unlink(missing_ok=True)
        
        if annotated_path and os.path.exists(annotated_path):
            return jsonify({
                'success': True,
                'visualization_url': f'/document-visualization/{document_id}',
                'message': 'Visualization created successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create visualization - output file not created'
            }), 500
            
    except Exception as e:
        print(f"Visualization creation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Visualization creation failed',
            'details': str(e)
        }), 500

@app.route('/document-visualization/<int:document_id>')
def serve_document_visualization(document_id):
    """Serve the annotated document image"""
    firm_id = session['firm_id']
    
    # Get the document and verify access
    document = db.session.query(ClientDocument).join(ChecklistItem).join(DocumentChecklist).join(Client).filter(
        ClientDocument.id == document_id,
        Client.firm_id == firm_id
    ).first()
    
    if not document:
        return "Document not found", 404
    
    # Check for annotated version first
    annotated_path = Path('static/visualizations') / f'document_{document_id}_annotated.png'
    
    if annotated_path.exists():
        # Serve the annotated version with tick marks
        return send_file(
            str(annotated_path),
            mimetype='image/png',
            as_attachment=False
        )
    else:
        # Fall back to original document if annotation doesn't exist
        if not os.path.exists(document.file_path):
            return "Document file not found", 404
        
        # For image files, serve directly
        if document.mime_type and document.mime_type.startswith('image/'):
            return send_file(
                document.file_path,
                mimetype=document.mime_type,
                as_attachment=False
            )
        else:
            # For PDFs or other formats, try to convert to image first
            try:
                from pdf2image import convert_from_path
                pages = convert_from_path(document.file_path, first_page=1, last_page=1)
                if pages:
                    # Save as temporary PNG and serve
                    temp_dir = Path('static/visualizations')
                    temp_dir.mkdir(exist_ok=True, parents=True)
                    temp_path = temp_dir / f'document_{document_id}_temp.png'
                    pages[0].save(temp_path, 'PNG')
                    return send_file(
                        str(temp_path),
                        mimetype='image/png',
                        as_attachment=False
                    )
            except ImportError:
                pass
            
            # Final fallback - serve original file
            return send_file(
                document.file_path,
                mimetype=document.mime_type or 'application/octet-stream',
                as_attachment=False
            )

@app.route('/generate-bulk-workpaper', methods=['POST'])
def generate_bulk_workpaper():
    """Generate workpaper PDF for multiple analyzed documents"""
    try:
        data = request.get_json()
        documents = data.get('documents', {})
        title = data.get('title', 'Tax Document Workpaper')
        client_name = data.get('client_name', 'Client Documents')
        tax_year = data.get('tax_year', str(datetime.now().year))
        
        if not documents:
            return jsonify({'error': 'No documents provided'}), 400
        
        try:
            # Use the actual workpaper generator service
            from backend.services.workpaper_generator import WorkpaperGenerator
            from backend.models.document import ProcessingBatch, ProcessedDocument, FileUpload, WorkpaperMetadata, ProcessingStatus
            from pathlib import Path
            
            # Create ProcessedDocument objects from our analysis results
            processed_docs = []
            for doc_id, doc_data in documents.items():
                # Get the actual document from database
                db_doc = ClientDocument.query.filter_by(id=int(doc_id), firm_id=session['firm_id']).first()
                if not db_doc:
                    continue
                    
                # Create FileUpload object
                file_upload = FileUpload(
                    filename=doc_data.get('filename', db_doc.original_filename),  # Use original filename
                    content_type=db_doc.mime_type or 'application/pdf',
                    size=os.path.getsize(db_doc.file_path) if os.path.exists(db_doc.file_path) else 0,
                    file_path=Path(db_doc.file_path)
                )
                
                # Create a mock ProcessedDocument
                processed_doc = ProcessedDocument(file_upload=file_upload)
                processed_doc.processing_status = ProcessingStatus.COMPLETED
                
                # Add our analysis results with proper structure expected by WorkpaperGenerator
                if 'azure_result' in doc_data:
                    azure_data = doc_data['azure_result']
                    processed_doc.azure_result = type('AzureResult', (), {
                        'confidence': azure_data.get('confidence', 0),
                        'doc_type': azure_data.get('doc_type', 'unknown'),
                        'fields': {pair['key']: pair['value'] for pair in azure_data.get('key_value_pairs', [])},
                        'raw_response': azure_data
                    })()
                
                if 'gemini_result' in doc_data:
                    gemini_data = doc_data['gemini_result']
                    document_type = gemini_data.get('document_type', 'Unknown Document')
                    
                    # Create proper bookmark structure
                    bookmark_structure = type('BookmarkStructure', (), {
                        'level1': 'Tax Documents',  # Top level category
                        'level2': document_type,    # Document type
                        'level3': doc_data.get('filename', db_doc.filename)  # Individual document
                    })()
                    
                    processed_doc.gemini_result = type('GeminiResult', (), {
                        'document_category': document_type,
                        'document_analysis_summary': gemini_data.get('summary', ''),
                        'suggested_bookmark_structure': bookmark_structure
                    })()
                
                processed_docs.append(processed_doc)
            
            if not processed_docs:
                return jsonify({'error': 'No processed documents available for workpaper generation'}), 400
            
            # Create ProcessingBatch using the proper model
            batch = ProcessingBatch(
                batch_id=f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                documents=processed_docs,
                total_documents=len(processed_docs),
                processed_documents=len(processed_docs),
                failed_documents=0,
                status=ProcessingStatus.COMPLETED
            )
            
            # Generate the actual PDF workpaper
            generator = WorkpaperGenerator()
            workpaper_path = generator.generate_workpaper(
                batch,
                title=title,
                client_name=client_name,
                tax_year=tax_year,
                preparer_name=session.get('user_name', 'CPA')
            )
            
            if workpaper_path and Path(workpaper_path).exists():
                # Return the generated PDF
                return send_file(
                    workpaper_path,
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name=f'workpaper_{tax_year}_{datetime.now().strftime("%Y%m%d")}.pdf'
                )
            else:
                raise Exception("Workpaper generation returned no file")
                
        except Exception as e:
            print(f"Workpaper generation error: {e}")
            
            # Fallback to simple text workpaper if PDF generation fails
            workpaper_content = f"""
TAX DOCUMENT WORKPAPER
=====================

Title: {title}
Client: {client_name}
Tax Year: {tax_year}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Firm: {session.get('firm_name', 'Demo Firm')}

DOCUMENT ANALYSIS SUMMARY
========================

Total Documents Analyzed: {len(documents)}

"""
            
            for doc_id, doc_data in documents.items():
                workpaper_content += f"""
DOCUMENT: {doc_data.get('filename', 'Unknown')}
----------------------------------------
Status: {doc_data.get('status', 'Unknown')}
Document Type: {doc_data.get('gemini_result', {}).get('document_type', 'Unknown')}
Confidence: {doc_data.get('azure_result', {}).get('confidence', 0):.2f}

Summary: {doc_data.get('gemini_result', {}).get('summary', 'No summary available')}

Key Findings:
"""
                findings = doc_data.get('gemini_result', {}).get('key_findings', [])
                for finding in findings[:5]:
                    workpaper_content += f"- {finding}\n"
                
                workpaper_content += "\n"
            
            # Return as text file with error note
            workpaper_content += f"\n\nNOTE: PDF generation failed ({str(e)}), returning as text file.\n"
            
            response = make_response(workpaper_content.encode('utf-8'))
            response.headers['Content-Type'] = 'text/plain'
            response.headers['Content-Disposition'] = f'attachment; filename=workpaper_{tax_year}_{datetime.now().strftime("%Y%m%d")}.txt'
            return response
        
    except Exception as e:
        print(f"Bulk workpaper error: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/api/chat-with-document', methods=['POST'])
def chat_with_document():
    """Handle AI chat interactions about analyzed documents"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
        
        data = request.get_json()
        document_id = data.get('document_id')
        message = data.get('message', '').strip()
        analysis_data = data.get('analysis_data')
        
        if not document_id or not message:
            return jsonify({'error': 'Document ID and message are required'}), 400
        
        # Verify document belongs to current firm
        document = ClientDocument.query.filter_by(id=document_id, firm_id=session['firm_id']).first()
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        if AI_SERVICES_AVAILABLE:
            try:
                # This would use the TaxDocumentAnalystAgent
                # For now, provide intelligent mock responses based on the message
                response = generate_chat_response(message, analysis_data, document)
                return jsonify({'response': response})
            except Exception as e:
                logger.error(f"AI chat error: {e}")
                return jsonify({'response': 'I apologize, but I encountered an error processing your question. Please try again or rephrase your question.'})
        else:
            # Fallback response when AI services aren't available
            return jsonify({
                'response': 'AI chat is currently unavailable. Please configure Azure Document Intelligence and Gemini AI services to enable this feature.'
            })
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def generate_chat_response(message, analysis_data, document):
    """Generate intelligent chat responses based on the message and analysis data"""
    message_lower = message.lower()
    
    # Basic document information responses
    if any(word in message_lower for word in ['what', 'type', 'document', 'kind']):
        if analysis_data and analysis_data.get('gemini_result', {}).get('document_type'):
            doc_type = analysis_data['gemini_result']['document_type']
            return f"This is a {doc_type}. The document was uploaded as '{document.filename}' and has been analyzed for key tax-related information."
        else:
            return f"This document '{document.filename}' appears to be a tax-related document that was uploaded for analysis."
    
    # Summary and key findings
    if any(word in message_lower for word in ['summary', 'summarize', 'overview', 'main']):
        if analysis_data and analysis_data.get('gemini_result', {}).get('summary'):
            summary = analysis_data['gemini_result']['summary']
            return f"Here's a summary of the document: {summary}"
        else:
            return "I can provide a summary once the document has been fully analyzed. Please run the analysis first."
    
    # Key findings
    if any(word in message_lower for word in ['findings', 'important', 'key', 'significant']):
        if analysis_data and analysis_data.get('gemini_result', {}).get('key_findings'):
            findings = analysis_data['gemini_result']['key_findings'][:3]  # Top 3 findings
            findings_text = "Here are the key findings from this document:\n" + "\n".join([f"• {finding}" for finding in findings])
            return findings_text
        else:
            return "Key findings will be available after document analysis is complete."
    
    # Recommendations
    if any(word in message_lower for word in ['recommend', 'suggest', 'advice', 'should', 'need']):
        if analysis_data and analysis_data.get('gemini_result', {}).get('recommendations'):
            recommendations = analysis_data['gemini_result']['recommendations'][:2]  # Top 2 recommendations
            rec_text = "Based on the analysis, here are my recommendations:\n" + "\n".join([f"• {rec}" for rec in recommendations])
            return rec_text
        else:
            return "I can provide recommendations after the document analysis is complete."
    
    # Data extraction questions
    if any(word in message_lower for word in ['amount', 'value', 'total', 'income', 'deduction']):
        if analysis_data and analysis_data.get('azure_result', {}).get('key_value_pairs'):
            kvp = analysis_data['azure_result']['key_value_pairs']
            # Look for relevant financial data
            financial_pairs = [pair for pair in kvp if any(term in pair.get('key', '').lower() 
                              for term in ['amount', 'total', 'income', 'tax', 'deduction', 'value'])]
            if financial_pairs:
                data_text = "Here are the financial values I found:\n" + "\n".join([
                    f"• {pair.get('key', 'Unknown')}: {pair.get('value', 'N/A')}" for pair in financial_pairs[:5]
                ])
                return data_text
            else:
                return "I found structured data in the document, but no specific financial amounts matching your query."
        else:
            return "Financial data extraction requires document analysis to be completed first."
    
    # Tables and structured data
    if any(word in message_lower for word in ['table', 'rows', 'columns', 'data', 'structured']):
        if analysis_data and analysis_data.get('azure_result', {}).get('tables'):
            tables = analysis_data['azure_result']['tables']
            if tables:
                table_count = len(tables)
                total_cells = sum(len(table.get('cells', [])) for table in tables)
                return f"I found {table_count} table(s) in this document with a total of {total_cells} data cells. This structured data has been extracted and can be used for further analysis."
            else:
                return "No structured tables were detected in this document."
        else:
            return "Table analysis requires document processing to be completed first."
    
    # Compliance and tax-specific questions
    if any(word in message_lower for word in ['compliance', 'regulation', 'irs', 'tax', 'filing']):
        return "For tax compliance questions, I recommend reviewing the key findings and recommendations from the analysis. If you have specific compliance concerns, please consult with your tax advisor."
    
    # Default helpful response
    return f"I can help you understand this document ({document.filename}). You can ask me about:\n• Document summary and key findings\n• Financial amounts and values\n• Recommendations for next steps\n• Structured data and tables\n• Tax compliance considerations\n\nWhat specific aspect would you like to know more about?"

@app.route('/generate-workpaper/<int:document_id>', methods=['POST'])
def generate_workpaper(document_id):
    """Generate workpaper PDF for a document"""
    try:
        document = ClientDocument.query.filter_by(id=document_id, firm_id=session['firm_id']).first()
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        if AI_SERVICES_AVAILABLE:
            try:
                # This would use the workpaper generator service
                # For now, return a mock PDF response
                from io import BytesIO
                import json
                
                # Create a simple text-based "workpaper" for demonstration
                analysis_data = request.get_json() if request.is_json else {}
                
                # Create a basic PDF-like response (in practice, this would use ReportLab)
                workpaper_content = f"""
WORKPAPER ANALYSIS REPORT
Document: {document.filename}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Firm: {session.get('firm_name', 'Demo Firm')}

DOCUMENT ANALYSIS SUMMARY:
{json.dumps(analysis_data, indent=2)}
"""
                
                # In a real implementation, this would generate a proper PDF
                response = make_response(workpaper_content.encode('utf-8'))
                response.headers['Content-Type'] = 'application/pdf'
                response.headers['Content-Disposition'] = f'attachment; filename=workpaper_{document_id}.pdf'
                return response
                
            except Exception as e:
                logger.error(f"Workpaper generation error: {e}")
                return jsonify({'error': 'Failed to generate workpaper'}), 500
        else:
            return jsonify({'error': 'Workpaper generation requires AI services to be configured'}), 503
        
    except Exception as e:
        logger.error(f"Workpaper endpoint error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ====================================
# PUBLIC CLIENT ACCESS ROUTES
# ====================================

@app.route('/checklist/<token>')
def public_checklist(token):
    """Public access to client checklist via secure token"""
    try:
        # Find checklist by access token
        checklist = DocumentChecklist.query.filter_by(access_token=token, is_active=True).first()
        
        if not checklist:
            return render_template('error.html', 
                                 error_title="Checklist Not Found",
                                 error_message="The requested checklist could not be found or the link has expired."), 404
        
        # Check if token is expired
        if checklist.is_token_expired:
            return render_template('error.html',
                                 error_title="Link Expired", 
                                 error_message="This checklist link has expired. Please contact your CPA for a new link."), 403
        
        # Record access
        checklist.record_token_access()
        db.session.commit()
        
        # Get client information
        client = checklist.client
        
        # Render public checklist view (no login required)
        return render_template('public_checklist.html', 
                             checklist=checklist,
                             client=client,
                             items=checklist.items)
    
    except Exception as e:
        app.logger.error(f"Public checklist access error: {e}")
        return render_template('error.html',
                             error_title="Access Error",
                             error_message="An error occurred while accessing the checklist. Please try again or contact your CPA."), 500


@app.route('/checklist/<token>/upload', methods=['POST'])
def public_checklist_upload(token):
    """Handle file uploads from public checklist"""
    try:
        # Find checklist by access token
        checklist = DocumentChecklist.query.filter_by(access_token=token, is_active=True).first()
        
        if not checklist or checklist.is_token_expired:
            return jsonify({'success': False, 'message': 'Invalid or expired checklist link'}), 403
        
        item_id = request.form.get('item_id')
        item = ChecklistItem.query.filter_by(id=item_id, checklist_id=checklist.id).first()
        
        if not item:
            return jsonify({'success': False, 'message': 'Invalid checklist item'}), 404
        
        # Handle file upload
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            # Create client-specific upload directory
            client_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], f'client_{checklist.client_id}')
            os.makedirs(client_upload_dir, exist_ok=True)
            
            # Generate secure filename
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            file_path = os.path.join(client_upload_dir, unique_filename)
            
            # Save file
            file.save(file_path)
            
            # Create document record
            document = ClientDocument(
                checklist_id=checklist.id,
                item_id=item.id,
                filename=filename,
                file_path=file_path,
                file_size=os.path.getsize(file_path),
                mime_type=mimetypes.guess_type(filename)[0] or 'application/octet-stream',
                uploaded_at=datetime.utcnow()
            )
            db.session.add(document)
            
            # Update item status
            item.update_status('uploaded')
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'message': f'File "{filename}" uploaded successfully',
                'item_id': item.id,
                'new_status': 'uploaded'
            })
        else:
            return jsonify({'success': False, 'message': 'File type not allowed'}), 400
    
    except Exception as e:
        app.logger.error(f"Public checklist upload error: {e}")
        return jsonify({'success': False, 'message': 'Upload failed. Please try again.'}), 500


@app.route('/checklist/<token>/status', methods=['POST'])
def public_checklist_status(token):
    """Handle status updates from public checklist"""
    try:
        # Find checklist by access token
        checklist = DocumentChecklist.query.filter_by(access_token=token, is_active=True).first()
        
        if not checklist or checklist.is_token_expired:
            return jsonify({'success': False, 'message': 'Invalid or expired checklist link'}), 403
        
        item_id = request.form.get('item_id')
        new_status = request.form.get('status')
        
        if new_status not in ['already_provided', 'not_applicable']:
            return jsonify({'success': False, 'message': 'Invalid status'}), 400
        
        item = ChecklistItem.query.filter_by(id=item_id, checklist_id=checklist.id).first()
        
        if not item:
            return jsonify({'success': False, 'message': 'Invalid checklist item'}), 404
        
        # Update item status
        item.update_status(new_status)
        db.session.commit()
        
        status_messages = {
            'already_provided': 'marked as already provided',
            'not_applicable': 'marked as not applicable'
        }
        
        return jsonify({
            'success': True, 
            'message': f'Item "{item.title}" {status_messages[new_status]}',
            'item_id': item.id,
            'new_status': new_status
        })
    
    except Exception as e:
        app.logger.error(f"Public checklist status update error: {e}")
        return jsonify({'success': False, 'message': 'Status update failed. Please try again.'}), 500


@app.route('/checklist/<int:checklist_id>/share')
def share_checklist(checklist_id):
    """Generate or display share link for checklist"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    checklist = DocumentChecklist.query.filter_by(
        id=checklist_id, 
        created_by=session['user_id']
    ).first()
    
    if not checklist:
        flash('Checklist not found', 'error')
        return redirect(url_for('document_checklists'))
    
    # Generate token if not exists
    if not checklist.access_token:
        checklist.generate_access_token()
        checklist.client_email = checklist.client.email if checklist.client.email else ""
        checklist.token_expires_at = datetime.utcnow() + timedelta(days=30)  # 30 day expiration
        db.session.commit()
    
    # Generate full URL for sharing
    public_url = request.url_root.rstrip('/') + checklist.public_url
    
    return render_template('share_checklist.html', 
                         checklist=checklist, 
                         client=checklist.client,
                         public_url=public_url)


@app.route('/checklist/<int:checklist_id>/revoke-share', methods=['POST'])
def revoke_checklist_share(checklist_id):
    """Revoke share link for checklist"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authorized'}), 401
    
    checklist = DocumentChecklist.query.filter_by(
        id=checklist_id, 
        created_by=session['user_id']
    ).first()
    
    if not checklist:
        return jsonify({'success': False, 'message': 'Checklist not found'}), 404
    
    checklist.revoke_token()
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Share link revoked successfully'})


@app.route('/checklist/<int:checklist_id>/regenerate-share', methods=['POST'])
def regenerate_checklist_share(checklist_id):
    """Regenerate share link for checklist"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authorized'}), 401
    
    checklist = DocumentChecklist.query.filter_by(
        id=checklist_id, 
        created_by=session['user_id']
    ).first()
    
    if not checklist:
        return jsonify({'success': False, 'message': 'Checklist not found'}), 404
    
    # Generate new token
    checklist.generate_access_token()
    checklist.token_expires_at = datetime.utcnow() + timedelta(days=30)
    db.session.commit()
    
    # Return new URL
    public_url = request.url_root.rstrip('/') + checklist.public_url
    
    return jsonify({
        'success': True, 
        'message': 'New share link generated',
        'public_url': public_url
    })


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0')


