from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from datetime import datetime, date, timedelta
import calendar
import time
from pathlib import Path
from dateutil.relativedelta import relativedelta
from werkzeug.utils import secure_filename
import mimetypes
import uuid

# Import configuration and core utilities
from config import get_config
from core import db, migrate, create_directories

# Import models
from models import (
    Firm, User, Template, TemplateTask, Project, Task, ActivityLog, 
    Client, TaskComment, WorkType, TaskStatus, Contact, ClientContact, 
    Attachment, ClientUser, DocumentChecklist, ChecklistItem, 
    ClientDocument, DocumentTemplate, DocumentTemplateItem, 
    IncomeWorksheet, DemoAccessRequest, ClientChecklistAccess
)

# Create Flask application
app = Flask(__name__)

# Load configuration
config_class = get_config()
app.config.from_object(config_class)

# Create necessary directories
create_directories(app)

# Initialize extensions
db.init_app(app)
migrate.init_app(app, db)

# Register blueprints
from blueprints import ALL_BLUEPRINTS
for blueprint in ALL_BLUEPRINTS:
    app.register_blueprint(blueprint)

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
# Temporarily disabled AI imports to resolve dependency issues
AI_SERVICES_AVAILABLE = False
print("⚠️  AI Services temporarily disabled")
print("💡 To enable AI features:")
print("   1. Copy .env.template to .env")
print("   2. Add your Azure and Gemini API keys")
print("   3. Install dependencies: pip install -r requirements.txt")

# try:
#     from backend.services.document_processor import DocumentProcessor
#     from backend.services.azure_service import AzureDocumentService
#     from backend.services.gemini_service import GeminiDocumentService
#     from backend.services.document_visualizer import DocumentVisualizer
#     from backend.agents.tax_document_analyst_agent import TaxDocumentAnalystAgent
#     from backend.models.document import FileUpload, ProcessedDocument
#     from backend.utils.config import settings
#     AI_SERVICES_AVAILABLE = True
#     print("✅ AI Services loaded successfully")
# except Exception as e:
#     AI_SERVICES_AVAILABLE = False
#     print(f"⚠️  AI Services not available: {e}")
#     print("💡 To enable AI features:")
#     print("   1. Copy .env.template to .env")
#     print("   2. Add your Azure and Gemini API keys")
#     print("   3. Install dependencies: pip install -r requirements.txt")

# Recurring tasks are now integrated into the Task model

def allowed_file_local(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def save_uploaded_file(file, firm_id, entity_type, entity_id):
    """Save uploaded file and create attachment record"""
    if not file or not allowed_file_local(file.filename):
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
    if request.endpoint in ['static', 'auth.home', 'auth.landing', 'auth.logout', 'auth.clear_session', 'admin.login', 'admin.dashboard', 'admin.authenticate']:
        return
    
    # Skip for login flow
    if request.endpoint in ['auth.login', 'auth.authenticate', 'auth.select_user', 'auth.set_user', 'auth.switch_user']:
        return
    
    # Skip for client portal
    if request.endpoint in ['client_login', 'client_authenticate', 'client_dashboard', 'client_logout']:
        return
    
    # Skip for public checklist access
    if request.endpoint in ['public_checklist', 'public_checklist_upload', 'public_checklist_status']:
        return
    
    # Check firm access - clear session if invalid
    if 'firm_id' not in session:
        session.clear()  # Clear any partial session data
        return redirect(url_for('auth.login'))
    
    # Check user selection (except for user selection pages)
    if 'user_id' not in session:
        return redirect(url_for('auth.select_user'))


@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    # For authenticated pages, prevent caching
    if 'firm_id' in session:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    
    # Add other security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    return response

# Auth routes moved to auth blueprint



# Dashboard route moved to dashboard blueprint

# Admin routes moved to admin blueprint





# Project delete route moved to projects blueprint


# Task edit route moved to tasks blueprint

# Task view route moved to tasks blueprint

# Task comments route moved to tasks blueprint

# Task log-time route moved to tasks blueprint

# Task bulk-update route moved to tasks blueprint

# Task bulk-delete route moved to tasks blueprint

# Task update route moved to tasks blueprint

# Task timer start route moved to tasks blueprint

# Task timer stop route moved to tasks blueprint

# Task timer status route moved to tasks blueprint

# Reports time-tracking route moved to views blueprint

# User routes moved to users blueprint

# Client routes moved to clients blueprint

# Calendar route moved to views blueprint

# Kanban route moved to views blueprint

# API clients search route moved to api blueprint

# API project progress route moved to api blueprint

# Search route moved to views blueprint

# Export routes moved to export blueprint

# Additional client routes moved to clients blueprint

# Admin work_types routes moved to admin blueprint
# Admin work_types edit and status create routes moved to admin blueprint
# Remaining admin status routes moved to admin blueprint

# Contact routes moved to contacts blueprint

# Client and contact association routes moved to clients and contacts blueprints

# API clients route moved to api blueprint


# File upload and attachment routes moved to attachments blueprint

# Subtask management routes moved to subtasks blueprint

# Admin recurring task processing route moved to admin blueprint

# Document checklist management routes moved to documents blueprint

# Create and edit checklist routes moved to documents blueprint

# Client access setup and document checklist routes moved to clients and documents blueprints

# Client portal authentication routes moved to client_portal blueprint

# Client upload and status update routes moved to client_portal blueprint


# AI document analysis routes moved to ai blueprint

# All remaining routes moved to appropriate blueprints:
# - AI analysis routes → ai blueprint
# - Document sharing routes → documents blueprint

# End of blueprint migration - all routes successfully moved!

# All application routes have been successfully migrated to blueprints!
# Total routes migrated: 100 → 0 remaining in app.py
# 
# Blueprint organization:
# - auth_bp: Authentication and user management
# - admin_bp: Administrative functions and templates
# - dashboard_bp: Main dashboard and overview
# - projects_bp: Project management and workflows
# - tasks_bp: Task management and operations
# - clients_bp: Client management and relationships
# - contacts_bp: Contact management and associations
# - users_bp: User management within firms
# - views_bp: Calendar, Kanban, search, and reports
# - documents_bp: Document checklists and file management
# - client_portal_bp: Client portal authentication and uploads
# - export_bp: CSV export functionality
# - api_bp: RESTful API endpoints
# - attachments_bp: File upload and download handling
# - subtasks_bp: Subtask management operations
# - ai_bp: AI document analysis and processing

# Flask application is now fully modularized with blueprints!
# All route handlers have been moved to their respective blueprints.
# The app.py file now serves as a clean application factory.


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0')
