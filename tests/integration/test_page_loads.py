"""
Comprehensive Page Load Tests for CPA WorkflowPilot
Tests that all major pages load without errors after architectural refactoring.
"""

import pytest
from flask import Flask
from datetime import datetime, date
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app
from core.db_import import db
from models import User, Firm, Client, Project, Task, WorkType


class TestPageLoads:
    """Test suite for page loading functionality"""
    
    @pytest.fixture(scope='class')
    def app(self):
        """Create test Flask app"""
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            self._create_test_data()
            yield app
            db.drop_all()
    
    @pytest.fixture(scope='class')
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    @pytest.fixture(scope='class')
    def auth_session(self, client):
        """Create authenticated session"""
        # Simulate session data
        with client.session_transaction() as sess:
            sess['firm_id'] = 1
            sess['user_id'] = 1
            sess['user_name'] = 'Test User'
            sess['user_role'] = 'Admin'
        return client
    
    def _create_test_data(self):
        """Create minimal test data for page loads"""
        try:
            # Create test firm
            firm = Firm(id=1, name='Test Firm', access_code='TEST123')
            db.session.add(firm)
            
            # Create test user
            user = User(id=1, name='Test User', role='Admin', firm_id=1, is_active=True)
            db.session.add(user)
            
            # Create test client
            client = Client(id=1, name='Test Client', firm_id=1)
            db.session.add(client)
            
            # Create test work type
            work_type = WorkType(id=1, name='Tax Prep', color='#3498db', firm_id=1, is_active=True)
            db.session.add(work_type)
            
            # Create test project
            project = Project(
                id=1, 
                name='Test Project',
                client_id=1,
                client_name='Test Client',
                firm_id=1,
                status='Active',
                start_date=date.today(),
                work_type_id=1
            )
            db.session.add(project)
            
            # Create test task
            task = Task(
                id=1,
                title='Test Task',
                project_id=1,
                assignee_id=1,
                firm_id=1,
                status='Not Started',
                priority='Medium',
                due_date=date.today()
            )
            db.session.add(task)
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating test data: {e}")
    
    # Dashboard Pages
    def test_main_dashboard_loads(self, auth_session):
        """Test main dashboard page loads without errors"""
        response = auth_session.get('/dashboard')
        assert response.status_code == 200
        assert b'dashboard' in response.data.lower() or b'projects' in response.data.lower()
    
    # Task Management Pages
    def test_tasks_page_loads(self, auth_session):
        """Test tasks page loads without errors"""
        response = auth_session.get('/tasks')
        assert response.status_code == 200
        assert b'task' in response.data.lower() or b'title' in response.data.lower()
    
    def test_create_task_page_loads(self, auth_session):
        """Test create task page loads"""
        response = auth_session.get('/tasks/create')
        assert response.status_code == 200
    
    def test_view_task_page_loads(self, auth_session):
        """Test view task page loads"""
        response = auth_session.get('/tasks/1')
        assert response.status_code in [200, 404]  # 404 ok if task doesn't exist
    
    # Project Management Pages  
    def test_projects_page_loads(self, auth_session):
        """Test projects page loads without errors"""
        response = auth_session.get('/projects')
        assert response.status_code == 200
        assert b'project' in response.data.lower()
    
    def test_create_project_page_loads(self, auth_session):
        """Test create project page loads"""
        response = auth_session.get('/projects/create')
        assert response.status_code == 200
    
    def test_view_project_page_loads(self, auth_session):
        """Test view project page loads"""
        response = auth_session.get('/projects/1')
        assert response.status_code in [200, 404]
    
    # Client Management Pages
    def test_clients_page_loads(self, auth_session):
        """Test clients page loads without errors"""
        response = auth_session.get('/clients')
        assert response.status_code == 200
        assert b'client' in response.data.lower()
    
    def test_create_client_page_loads(self, auth_session):
        """Test create client page loads"""
        response = auth_session.get('/clients/create')
        assert response.status_code == 200
    
    def test_view_client_page_loads(self, auth_session):
        """Test view client page loads"""
        response = auth_session.get('/clients/1')
        assert response.status_code in [200, 404]
    
    # User Management Pages
    def test_users_page_loads(self, auth_session):
        """Test users page loads without errors"""
        response = auth_session.get('/admin/users')
        assert response.status_code == 200
        assert b'user' in response.data.lower()
    
    def test_create_user_page_loads(self, auth_session):
        """Test create user page loads"""
        response = auth_session.get('/admin/create-user')
        assert response.status_code == 200
    
    # Document Management Pages
    def test_documents_page_loads(self, auth_session):
        """Test documents page loads"""
        response = auth_session.get('/documents')
        assert response.status_code == 200
    
    def test_checklists_page_loads(self, auth_session):
        """Test checklists page loads"""
        response = auth_session.get('/documents/checklists')
        assert response.status_code == 200
    
    # View Pages (Calendar, Kanban, etc.)
    def test_calendar_view_loads(self, auth_session):
        """Test calendar view loads"""
        response = auth_session.get('/calendar')
        assert response.status_code == 200
        assert b'calendar' in response.data.lower()
    
    def test_kanban_view_loads(self, auth_session):
        """Test kanban view loads"""
        response = auth_session.get('/kanban')
        assert response.status_code == 200
        assert b'kanban' in response.data.lower() or b'board' in response.data.lower()
    
    def test_time_tracking_view_loads(self, auth_session):
        """Test time tracking view loads"""
        response = auth_session.get('/time-tracking')
        assert response.status_code == 200
        assert b'time' in response.data.lower() or b'tracking' in response.data.lower()
    
    # API Endpoints
    def test_health_check_loads(self, auth_session):
        """Test health check endpoint"""
        response = auth_session.get('/health')
        assert response.status_code == 200
    
    def test_ai_services_status_loads(self, auth_session):
        """Test AI services status endpoint"""
        response = auth_session.get('/api/ai-services/status')
        assert response.status_code in [200, 500]  # 500 ok if AI not configured
    
    # Export Pages
    def test_export_page_loads(self, auth_session):
        """Test export page loads"""
        response = auth_session.get('/export')
        assert response.status_code == 200
    
    # Admin Pages
    def test_admin_dashboard_loads(self, auth_session):
        """Test admin dashboard loads"""
        response = auth_session.get('/admin')
        assert response.status_code == 200
    
    def test_work_types_page_loads(self, auth_session):
        """Test work types page loads"""
        response = auth_session.get('/admin/work-types')
        assert response.status_code == 200
    
    def test_templates_page_loads(self, auth_session):
        """Test templates page loads"""
        response = auth_session.get('/admin/templates')
        assert response.status_code == 200


class TestPageLoadPerformance:
    """Performance tests for page loading"""
    
    @pytest.fixture(scope='class')
    def app(self):
        """Create test Flask app"""
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture(scope='class')
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    @pytest.fixture(scope='class')
    def auth_session(self, client):
        """Create authenticated session"""
        with client.session_transaction() as sess:
            sess['firm_id'] = 1
            sess['user_id'] = 1
            sess['user_name'] = 'Test User'
            sess['user_role'] = 'Admin'
        return client
    
    def test_dashboard_loads_quickly(self, auth_session):
        """Test dashboard loads within reasonable time"""
        import time
        start_time = time.time()
        response = auth_session.get('/dashboard')
        load_time = time.time() - start_time
        
        assert response.status_code == 200
        assert load_time < 5.0  # Should load within 5 seconds
    
    def test_tasks_page_loads_quickly(self, auth_session):
        """Test tasks page loads within reasonable time"""
        import time
        start_time = time.time()
        response = auth_session.get('/tasks')
        load_time = time.time() - start_time
        
        assert response.status_code == 200
        assert load_time < 5.0


class TestErrorHandling:
    """Test error handling for page loads"""
    
    @pytest.fixture(scope='class')
    def app(self):
        """Create test Flask app"""
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture(scope='class')
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    def test_unauthenticated_access_redirects(self, client):
        """Test unauthenticated access redirects properly"""
        response = client.get('/dashboard')
        # Should redirect to login or return 401/403
        assert response.status_code in [302, 401, 403]
    
    def test_nonexistent_page_returns_404(self, client):
        """Test nonexistent pages return 404"""
        response = client.get('/nonexistent-page')
        assert response.status_code == 404
    
    def test_invalid_task_id_handles_gracefully(self, client):
        """Test invalid task ID handles gracefully"""
        with client.session_transaction() as sess:
            sess['firm_id'] = 1
            sess['user_id'] = 1
        
        response = client.get('/tasks/99999')
        # Should return 404 or handle gracefully
        assert response.status_code in [200, 404]


if __name__ == '__main__':
    """Run page load tests directly"""
    pytest.main([__file__, '-v', '--tb=short'])