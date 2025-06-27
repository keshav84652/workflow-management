"""
Pytest configuration and shared fixtures for the workflow management test suite.
Production-ready test infrastructure with comprehensive mocking and performance tracking.
"""

import pytest
import tempfile
import os
import sys
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from config import TestingConfig

# Import db from centralized db_import module
from core.db_import import db
# Import all models to ensure relationships are properly registered
import models
from models import (
    User, Firm, Client, Project, Task, 
    DocumentChecklist, ChecklistItem, ClientDocument,
    WorkType, TaskStatus, Template, TemplateTask, ActivityLog
)


@pytest.fixture(scope="session")
def app():
    """Create and configure test Flask application."""
    app = Flask(__name__)
    app.config.from_object(TestingConfig)
    
    # Initialize database
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        _create_test_data()
        yield app
        db.drop_all()


@pytest.fixture(scope="function")
def app_context(app):
    """Provide Flask application context for each test."""
    with app.app_context():
        yield app


@pytest.fixture(scope="function")
def client(app):
    """Provide Flask test client."""
    return app.test_client()


@pytest.fixture(scope="function")
def db_session(app_context):
    """Provide database session with automatic rollback."""
    connection = db.engine.connect()
    transaction = connection.begin()
    
    # Configure session to use this connection
    db.session.configure(bind=connection)
    
    yield db.session
    
    # Rollback transaction and close connection
    db.session.remove()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="session")
def test_firm(app):
    """Provide test firm data."""
    with app.app_context():
        return Firm.query.filter_by(access_code="TEST2024").first()


@pytest.fixture(scope="session") 
def test_user(app):
    """Provide test user data."""
    with app.app_context():
        return User.query.filter_by(username="testuser").first()


@pytest.fixture(scope="session")
def test_client_data(app):
    """Provide test client data."""
    with app.app_context():
        return Client.query.filter_by(name="Test Client LLC").first()


@pytest.fixture(scope="session")
def test_project(app):
    """Provide test project data."""
    with app.app_context():
        return Project.query.filter_by(name="Test Tax Return").first()


@pytest.fixture(scope="function")
def mock_redis():
    """Mock Redis client for testing without Redis dependency."""
    mock_redis = Mock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = True
    mock_redis.publish.return_value = 1
    
    with patch('core.redis_client.redis_client', mock_redis):
        yield mock_redis


@pytest.fixture(scope="function")
def mock_ai_services():
    """Mock AI services for testing without external dependencies."""
    with patch('services.ai_service.AIService.is_available', return_value=False):
        yield


@pytest.fixture(scope="function")
def temp_file():
    """Provide temporary file for testing file operations."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tf:
        tf.write(b'%PDF-1.4 test pdf content')
        temp_path = tf.name
    
    yield temp_path
    
    if os.path.exists(temp_path):
        os.unlink(temp_path)


def _create_test_data():
    """Create comprehensive test data for all test suites."""
    # Create firm
    test_firm = Firm(
        name="Test CPA Firm",
        access_code="TEST2024"
    )
    db.session.add(test_firm)
    db.session.flush()  # Get ID without committing
    
    # Create user
    test_user = User(
        username="testuser",
        email="test@example.com",
        role="Admin",
        firm_id=test_firm.id
    )
    db.session.add(test_user)
    
    # Create client
    test_client = Client(
        name="Test Client LLC",
        email="client@example.com",
        firm_id=test_firm.id
    )
    db.session.add(test_client)
    
    # Create work type
    work_type = WorkType(
        name="Tax Return",
        firm_id=test_firm.id
    )
    db.session.add(work_type)
    
    # Create task statuses
    task_statuses = [
        ("Not Started", "#gray"),
        ("In Progress", "#blue"), 
        ("Review", "#orange"),
        ("Completed", "#green")
    ]
    
    for name, color in task_statuses:
        status = TaskStatus(
            name=name,
            color=color,
            firm_id=test_firm.id
        )
        db.session.add(status)
    
    # Note: Project status handling will depend on existing project model structure
    
    db.session.flush()  # Get IDs
    
    # Create test project
    test_project = Project(
        name="Test Tax Return",
        client_id=test_client.id,
        assigned_user_id=test_user.id,
        work_type_id=work_type.id,
        firm_id=test_firm.id
    )
    db.session.add(test_project)
    
    # Create test tasks
    test_task = Task(
        title="Review Documents",
        project_id=test_project.id,
        assigned_user_id=test_user.id,
        status="pending",
        firm_id=test_firm.id
    )
    db.session.add(test_task)
    
    # Create document checklist
    test_checklist = DocumentChecklist(
        name="Tax Documents",
        client_id=test_client.id,
        created_by=test_user.id,
        firm_id=test_firm.id
    )
    db.session.add(test_checklist)
    
    # Create checklist item
    test_checklist_item = ChecklistItem(
        name="W-2 Forms",
        description="Employee W-2 tax forms",
        checklist_id=test_checklist.id,
        status="pending"
    )
    db.session.add(test_checklist_item)
    
    # Create template for testing
    template = Template(
        name="Standard Tax Return",
        description="Standard template for tax returns",
        firm_id=test_firm.id,
        created_by=test_user.id
    )
    db.session.add(template)
    
    db.session.commit()


@pytest.fixture(scope="function")
def performance_tracker():
    """Track performance metrics during tests with benchmarking."""
    class PerformanceTracker:
        def __init__(self):
            self.start_time = None
            self.metrics = {}
            self.benchmarks = {
                'task_creation': 0.1,      # 100ms max
                'event_publishing': 0.05,   # 50ms max
                'repository_query': 0.02,   # 20ms max
                'service_operation': 0.5,   # 500ms max
                'api_request': 1.0          # 1s max
            }
        
        def start(self, operation):
            self.start_time = time.time()
            self.operation = operation
        
        def stop(self):
            if self.start_time:
                duration = time.time() - self.start_time
                self.metrics[self.operation] = duration
                return duration
            return None
        
        def assert_performance(self, operation, max_duration=None):
            """Assert operation meets performance requirements."""
            if operation in self.metrics:
                actual_duration = self.metrics[operation]
                expected_max = max_duration or self.benchmarks.get(operation, 1.0)
                assert actual_duration <= expected_max, \
                    f"{operation} took {actual_duration:.3f}s, expected <= {expected_max:.3f}s"
        
        def get_metrics(self):
            return self.metrics
    
    return PerformanceTracker()


@pytest.fixture(scope="function")
def mock_event_publisher():
    """Mock event publisher for testing event flows."""
    with patch('events.publisher.publish_event') as mock_publish:
        mock_publish.return_value = True
        yield mock_publish


@pytest.fixture(scope="function")
def mock_celery_tasks():
    """Mock Celery background tasks."""
    with patch('workers.ai_worker.analyze_document.delay') as mock_ai, \
         patch('workers.document_worker.process_large_document.delay') as mock_doc, \
         patch('workers.notification_worker.send_email.delay') as mock_email:
        
        mock_ai.return_value.id = 'test-task-id-ai'
        mock_doc.return_value.id = 'test-task-id-doc'
        mock_email.return_value.id = 'test-task-id-email'
        
        yield {
            'ai_worker': mock_ai,
            'document_worker': mock_doc,
            'notification_worker': mock_email
        }


@pytest.fixture(scope="function")
def authenticated_session(client, test_user, test_firm):
    """Provide authenticated session for API testing."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_user.id
        sess['firm_id'] = test_firm.id
        sess['username'] = test_user.username
    return client
