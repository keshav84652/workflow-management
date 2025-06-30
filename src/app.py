from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from datetime import datetime, date, timedelta
import calendar
import os
import time
from pathlib import Path
from dateutil.relativedelta import relativedelta
from werkzeug.utils import secure_filename
import mimetypes
import uuid

# Import configuration and core utilities
from .config import get_config
from src.shared.database.db_import import db
from flask_migrate import Migrate

# Import models
from src.models import (
    Firm, User, Template, TemplateTask, Project, Task, ActivityLog, 
    Client, TaskComment, WorkType, TaskStatus, Contact, ClientContact, 
    Attachment, ClientUser, DocumentChecklist, ChecklistItem, 
    ClientDocument, DocumentTemplate, DocumentTemplateItem, 
    IncomeWorksheet, DemoAccessRequest, ClientChecklistAccess
)

migrate = Migrate()

def create_app(config_name='default'):
    # Create Flask application with correct paths
    # Get the parent directory (project root) for templates and static files
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(project_root, 'templates')
    static_dir = os.path.join(project_root, 'static')
    
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=static_dir)

    # Load configuration
    config_class = get_config(config_name)
    app.config.from_object(config_class)

    # Create necessary directories (relative to project root)
    instance_dir = os.path.join(project_root, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Register Jinja2 template filters
    from src.shared.utils.template_filters import register_template_filters
    register_template_filters(app)
    
    # Register modules
    from .modules.auth import register_module as register_auth
    from .modules.client import register_module as register_client
    from .modules.document import register_module as register_document
    from .modules.admin import register_module as register_admin
    from .modules.project import register_module as register_project
    from .modules.dashboard import register_module as register_dashboard
    
    # All blueprints have been moved to modules
    
    # Register modules
    register_auth(app)
    register_client(app)
    register_document(app)
    register_admin(app)
    register_project(app)
    register_dashboard(app)
    
    # Initialize dependency injection container
    from src.shared.di_container import setup_service_registry
    from src.shared.bootstrap import register_services
    
    # Set up both DI systems for compatibility
    setup_service_registry()  # New DI container
    register_services()       # Legacy service registry
    
    # All blueprints now registered through modules

    # Add error handlers
    from werkzeug.routing import BuildError

    @app.errorhandler(BuildError)
    def handle_build_error(e):
        """Handle URL build errors without clearing session"""
        import traceback
        
        # Log detailed error for debugging
        app.logger.error(f'BuildError: {e}')
        app.logger.error(f'Endpoint: {e.endpoint}')
        app.logger.error(f'Values: {e.values}')
        app.logger.error(f'Method: {e.method}')
        app.logger.error(f'Traceback: {traceback.format_exc()}')
        
        # Show more specific error message in development
        if app.debug:
            flash(f'URL Build Error: {e.endpoint} with values {e.values}', 'error')
        else:
            flash(f'Page not found or URL error. Please try again.', 'error')
        
        # Redirect to dashboard if user is logged in, otherwise to login
        if 'firm_id' in session and 'user_id' in session:
            return redirect(url_for('dashboard.main'))
        else:
            return redirect(url_for('auth.login'))

    @app.errorhandler(404)
    def handle_not_found(e):
        """Handle 404 errors without clearing session"""
        flash('Page not found. Redirecting to dashboard.', 'warning')
        
        # Redirect to dashboard if user is logged in, otherwise to login
        if 'firm_id' in session and 'user_id' in session:
            return redirect(url_for('dashboard.main'))
        else:
            return redirect(url_for('auth.login'))

    @app.errorhandler(500)
    def handle_server_error(e):
        """Handle server errors without clearing session"""
        app.logger.error(f'Server Error: {e}')
        flash('A server error occurred. Please try again.', 'error')
        
        # Redirect to dashboard if user is logged in, otherwise to login
        if 'firm_id' in session and 'user_id' in session:
            return redirect(url_for('dashboard.main'))
        else:
            return redirect(url_for('auth.login'))

    from src.shared.utils.consolidated import generate_access_code
    # ActivityLoggingService now available through src.shared.services
    # Services accessed through bootstrap to avoid coupling
    from src.shared.bootstrap import get_task_service, get_client_service

    # Business logic functions moved to appropriate services:
    # - perform_checklist_ai_analysis -> DocumentService.perform_checklist_ai_analysis
    # - would_create_circular_dependency -> TaskService.would_create_circular_dependency
    # - check_and_update_project_completion -> ProjectService.check_and_update_project_completion

    # AI Document Analysis Integration
    # AI services are now auto-detected based on available API keys in config
    from src.modules.document.analysis_service import AIAnalysisService

    with app.app_context():
        # Initialize service registry for dependency injection
        from src.shared.bootstrap import register_services
        register_services()
        
        print("AI Services status determined by configuration:")
        print("   Azure Document Intelligence:", "Available" if app.config.get('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT') and app.config.get('AZURE_DOCUMENT_INTELLIGENCE_KEY') else "Not configured")
        print("   Gemini API:", "Available" if app.config.get('GEMINI_API_KEY') else "Not configured")
        print("   Overall AI Services:", "Available" if config_class().AI_SERVICES_AVAILABLE else "Not configured")
        
        # Test AI service initialization
        ai_service = AIAnalysisService(app.config)
        print(f"   AI Service Status: {'Ready' if ai_service.is_available() else 'Not available'}")
        print("   Service Registry: Initialized with dependency injection")

    # Recurring tasks are now integrated into the Task model
    
    # Note: File validation logic moved to AttachmentService
    # Note: save_uploaded_file function moved to blueprints/attachments.py

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
        if request.endpoint in ['client_portal.client_login', 'client_portal.client_authenticate', 'client_portal.client_dashboard', 'client_portal.client_logout']:
            return
        
        # Skip for public checklist access
        if request.endpoint and any(endpoint in request.endpoint for endpoint in ['public_checklist', 'documents.public']):
            return
        
        # Log session status for debugging
        app.logger.debug(f'Session check for endpoint {request.endpoint}: firm_id={session.get("firm_id")}, user_id={session.get("user_id")}')
        
        # Check firm access - be more conservative about clearing session
        if 'firm_id' not in session:
            app.logger.warning(f'No firm_id in session for endpoint {request.endpoint}. Session keys: {list(session.keys())}')
            
            # Don't clear session aggressively - just redirect
            flash('Your session has expired. Please log in again.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Check user selection (except for user selection pages)
        if 'user_id' not in session:
            app.logger.warning(f'No user_id in session for endpoint {request.endpoint}. Session: firm_id={session.get("firm_id")}')
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
    return app


if __name__ == '__main__':
    app = create_app()
    # REMOVED db.create_all() - was wiping out data on every app start!
    # Database tables should be created via migrations or init_db.py only
    app.run(debug=True, host='0.0.0.0', port=5002, use_reloader=False)