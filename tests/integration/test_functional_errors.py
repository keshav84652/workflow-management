"""
Functional Error Detection Tests for CPA WorkflowPilot
Tests that go beyond HTTP status codes to catch actual functional errors.
These tests would have caught the missing methods that caused runtime errors.
"""

import pytest
from flask import Flask
from datetime import datetime, date
import os
import sys
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app
from core.db_import import db
from models import User, Firm, Client, Project, Task, WorkType


class TestFunctionalErrors:
    """Test suite for functional error detection beyond HTTP status codes"""
    
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
        with client.session_transaction() as sess:
            sess['firm_id'] = 1
            sess['user_id'] = 1
            sess['user_name'] = 'Test User'
            sess['user_role'] = 'Admin'
        return client
    
    def _create_test_data(self):
        """Create test data for functional testing"""
        try:
            # Create test firm
            firm = Firm(id=1, name='Test Firm', access_code='TEST123')
            db.session.add(firm)
            
            # Create test user
            user = User(id=1, name='Test User', role='Admin', firm_id=1)
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
            
            # Create test task with due date for calendar testing
            task = Task(
                id=1,
                title='Test Task',
                project_id=1,
                assignee_id=1,
                firm_id=1,
                status='Not Started',
                priority='Medium',
                due_date=date.today(),
                actual_hours=2.5  # For time tracking testing
            )
            db.session.add(task)
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating test data: {e}")
    
    def test_dashboard_service_methods_exist(self, auth_session):
        """Test that all required dashboard service methods exist and work"""
        from services.dashboard_aggregator_service import DashboardAggregatorService
        
        service = DashboardAggregatorService()
        
        # Test all methods that blueprints expect
        required_methods = [
            'get_dashboard_data',
            'get_time_tracking_report', 
            'get_calendar_data',
            'get_quick_stats',
            'get_advanced_analytics'
        ]
        
        for method_name in required_methods:
            assert hasattr(service, method_name), f"Missing method: {method_name}"
            method = getattr(service, method_name)
            assert callable(method), f"Method {method_name} is not callable"
    
    def test_calendar_page_functional(self, auth_session):
        """Test calendar page functionality beyond HTTP status"""
        response = auth_session.get('/calendar')
        assert response.status_code == 200
        
        # Check that calendar data is actually rendered
        content = response.data.decode('utf-8')
        
        # Should contain calendar-related content
        assert any(word in content.lower() for word in ['calendar', 'month', 'year', 'task']), \
            "Calendar page missing expected calendar content"
        
        # Should not contain actual error messages (not just JavaScript variables named 'error')
        error_indicators = ['attributeerror', 'exception:', 'traceback', 'internal server error', 'error 500']
        for error in error_indicators:
            assert error not in content.lower(), f"Calendar page contains error: {error}"
    
    def test_time_tracking_page_functional(self, auth_session):
        """Test time tracking page functionality beyond HTTP status"""
        response = auth_session.get('/reports/time-tracking')
        assert response.status_code == 200
        
        content = response.data.decode('utf-8')
        
        # Should contain time tracking content
        assert any(word in content.lower() for word in ['time', 'tracking', 'hours', 'report']), \
            "Time tracking page missing expected content"
        
        # Should not contain specific error messages we've seen
        assert 'tasks_with_time' not in content, "Time tracking page shows raw error data"
        assert 'attributeerror' not in content.lower(), "Time tracking page shows AttributeError"
        assert 'internal server error' not in content.lower(), "Time tracking page shows server error"
    
    def test_dashboard_data_structure(self, auth_session):
        """Test that dashboard returns expected data structure"""
        from services.dashboard_aggregator_service import DashboardAggregatorService
        
        service = DashboardAggregatorService()
        data = service.get_dashboard_data(1)
        
        # Check required top-level keys
        required_keys = ['projects', 'tasks', 'clients', 'users', 'recent_tasks', 'recent_projects']
        for key in required_keys:
            assert key in data, f"Dashboard data missing required key: {key}"
        
        # Check data types
        assert isinstance(data['projects'], dict), "Projects data should be a dictionary"
        assert isinstance(data['tasks'], dict), "Tasks data should be a dictionary"
        assert isinstance(data['recent_tasks'], list), "Recent tasks should be a list"
        
        # Check no error in data
        assert 'error' not in data or data.get('error') is None, f"Dashboard data contains error: {data.get('error')}"
    
    def test_calendar_data_structure(self, auth_session):
        """Test that calendar service returns expected data structure"""
        from services.dashboard_aggregator_service import DashboardAggregatorService
        
        service = DashboardAggregatorService()
        calendar_data = service.get_calendar_data(1, 2024, 12)
        
        # Check required keys
        required_keys = ['year', 'month', 'month_name', 'tasks_by_date', 'total_tasks']
        for key in required_keys:
            assert key in calendar_data, f"Calendar data missing required key: {key}"
        
        # Check data types
        assert isinstance(calendar_data['year'], int), "Year should be integer"
        assert isinstance(calendar_data['month'], int), "Month should be integer"
        assert isinstance(calendar_data['tasks_by_date'], dict), "Tasks by date should be dictionary"
        assert isinstance(calendar_data['total_tasks'], int), "Total tasks should be integer"
        
        # Check no error
        assert 'error' not in calendar_data or calendar_data.get('error') is None, \
            f"Calendar data contains error: {calendar_data.get('error')}"
    
    def test_time_tracking_data_structure(self, auth_session):
        """Test that time tracking service returns expected data structure"""
        from services.dashboard_aggregator_service import DashboardAggregatorService
        
        service = DashboardAggregatorService()
        time_data = service.get_time_tracking_report(1)
        
        # Check required top-level keys
        required_keys = ['period', 'summary', 'by_user', 'by_project', 'detailed_tasks']
        for key in required_keys:
            assert key in time_data, f"Time tracking data missing required key: {key}"
        
        # Check summary structure
        summary = time_data['summary']
        summary_keys = ['total_hours', 'billable_hours', 'tasks_with_time']
        for key in summary_keys:
            assert key in summary, f"Time tracking summary missing key: {key}"
        
        # Check data types
        assert isinstance(time_data['detailed_tasks'], list), "Detailed tasks should be a list"
        assert isinstance(summary['tasks_with_time'], (int, float)), "tasks_with_time should be a number"
    
    def test_user_repository_compatibility(self, auth_session):
        """Test that UserRepository works without is_active field"""
        from repositories.user_repository import UserRepository
        
        repo = UserRepository()
        
        # These should not raise AttributeError
        users = repo.get_users_by_firm(1)
        assert isinstance(users, list), "get_users_by_firm should return a list"
        
        search_results = repo.search_by_name(1, 'Test')
        assert isinstance(search_results, list), "search_by_name should return a list"
        
        stats = repo.get_user_statistics(1)
        assert isinstance(stats, dict), "get_user_statistics should return a dict"
        assert 'total' in stats, "Statistics should include total count"
    
    def test_service_method_error_handling(self, auth_session):
        """Test that service methods handle errors gracefully"""
        from services.dashboard_aggregator_service import DashboardAggregatorService
        
        service = DashboardAggregatorService()
        
        # Test with invalid firm_id
        try:
            data = service.get_dashboard_data(99999)
            # Should not raise exception, should return safe fallback
            assert isinstance(data, dict), "Service should return dict even for invalid firm_id"
        except Exception as e:
            pytest.fail(f"Service should handle invalid firm_id gracefully, got: {e}")
        
        # Test calendar with invalid date
        try:
            calendar_data = service.get_calendar_data(1, 2024, 13)  # Invalid month
            assert isinstance(calendar_data, dict), "Calendar should handle invalid month gracefully"
        except Exception as e:
            pytest.fail(f"Calendar service should handle invalid date gracefully, got: {e}")
    
    def test_ajax_endpoints_return_json(self, auth_session):
        """Test that AJAX endpoints return valid JSON"""
        ajax_endpoints = [
            '/api/ai-services/status',
        ]
        
        for endpoint in ajax_endpoints:
            response = auth_session.get(endpoint)
            # Should be 200 or valid error code, but not 500
            assert response.status_code != 500, f"AJAX endpoint {endpoint} returns 500 error"
            
            # Should return valid JSON
            try:
                json.loads(response.data)
            except json.JSONDecodeError:
                pytest.fail(f"AJAX endpoint {endpoint} does not return valid JSON")
    
    def test_template_context_variables(self, auth_session):
        """Test that templates receive all required context variables"""
        # Test dashboard template context
        response = auth_session.get('/dashboard')
        assert response.status_code == 200
        
        # Should not contain undefined template variables
        content = response.data.decode('utf-8')
        undefined_indicators = ['jinja2.exceptions', 'templatenotfound', 'undefined variable']
        
        for indicator in undefined_indicators:
            assert indicator not in content.lower(), \
                f"Template contains error indicator: {indicator}"


class TestErrorRecovery:
    """Test error recovery and graceful degradation"""
    
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
        return client
    
    def test_empty_database_handling(self, auth_session):
        """Test that pages handle empty database gracefully"""
        # With empty database, pages should still load
        response = auth_session.get('/dashboard')
        assert response.status_code == 200
        
        response = auth_session.get('/tasks/', follow_redirects=True)
        assert response.status_code == 200
        
        response = auth_session.get('/projects/', follow_redirects=True)
        assert response.status_code == 200
        
        response = auth_session.get('/clients/', follow_redirects=True)
        assert response.status_code == 200
    
    def test_missing_data_references(self, auth_session):
        """Test handling of missing foreign key references"""
        from services.dashboard_aggregator_service import DashboardAggregatorService
        
        service = DashboardAggregatorService()
        
        # Should handle missing data gracefully
        data = service.get_dashboard_data(99999)  # Non-existent firm
        assert isinstance(data, dict)
        assert data.get('tasks', {}).get('total', 0) == 0


if __name__ == '__main__':
    """Run functional error tests directly"""
    pytest.main([__file__, '-v', '--tb=short'])