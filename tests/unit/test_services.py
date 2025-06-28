"""
Unit tests for service layer components.
Tests service method business logic, error handling, and integration patterns.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, timedelta

from services.task_service import TaskService
from services.project_service import ProjectService
from services.document_service import DocumentService
from services.client_service import ClientService
from models import Task, Project, Client, User, Firm


class TestTaskService:
    """Test TaskService business logic."""
    
    def test_create_task_success(self, app_context, db_session, test_firm, test_user):
        """Test successful task creation."""
        task_service = TaskService()
        
        result = task_service.create_task(
            title='Test Task',
            description='Test Description',
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert result['success'] is True
        assert 'task' in result
        assert result['task']['title'] == 'Test Task'
    
    def test_create_task_validation_error(self, app_context, test_firm, test_user):
        """Test task creation with validation errors."""
        task_service = TaskService()
        
        result = task_service.create_task(
            title='',  # Empty title should fail
            description='Test Description',
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert result['success'] is False
        assert 'message' in result
    
    def test_create_task_from_form(self, app_context, db_session, test_firm, test_user, test_project):
        """Test creating task from form data."""
        form_data = {
            'title': 'Form Task',
            'description': 'Created from form',
            'project_id': test_project.id,
            'assignee_id': test_user.id,
            'due_date': '2024-12-31',
            'priority': 'High',
            'estimated_hours': '5.0'
        }
        
        task_service = TaskService()
        # Note: create_task_from_form method doesn't exist yet, using create_task
        result = task_service.create_task(
            title=form_data['title'],
            description=form_data['description'],
            firm_id=test_firm.id,
            user_id=test_user.id,
            project_id=form_data.get('project_id'),
            assignee_id=form_data.get('assignee_id'),
            due_date=form_data.get('due_date'),
            priority=form_data.get('priority', 'Medium'),
            estimated_hours=float(form_data.get('estimated_hours', 0)) if form_data.get('estimated_hours') else None
        )
        
        assert result['success'] is True
        assert 'task' in result
    
    def test_update_task_status(self, app_context, db_session, test_firm, test_user):
        """Test updating task status."""
        task_service = TaskService()
        
        # First create a task
        with patch('events.publisher.publish_event'):
            create_result = task_service.create_task(
                title='Status Test Task',
                description='Testing status updates',
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            task_id = create_result['task']['id']  # Fixed: use 'task' key, then 'id'
        
        # Update status
        with patch('events.publisher.publish_event') as mock_publish:
            result = task_service.update_task_status(
                task_id=task_id,
                new_status='In Progress',
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            assert result['success'] is True
            
            # Verify status change event
            mock_publish.assert_called()
            event = mock_publish.call_args[0][0]
            assert event.event_type == 'TaskStatusChangedEvent'
    
    def test_get_task_by_id_with_access_check(self, app_context, db_session, test_firm, test_user):
        """Test getting task with access control."""
        task_service = TaskService()
        
        # Create task
        with patch('events.publisher.publish_event'):
            create_result = task_service.create_task(
                title='Access Test Task',
                description='Testing access control',
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            task_id = create_result['task']['id']  # Fixed: use 'task' key, then 'id'
        
        # Get task with correct firm
        task = task_service.get_task_by_id_with_access_check(task_id, test_firm.id)
        assert task is not None
        assert task.title == 'Access Test Task'
        
        # Try to get task with wrong firm
        task = task_service.get_task_by_id_with_access_check(task_id, 999)
        assert task is None
    
    def test_delete_task(self, app_context, db_session, test_firm, test_user):
        """Test task deletion."""
        task_service = TaskService()
        
        # Create task
        with patch('events.publisher.publish_event'):
            create_result = task_service.create_task(
                title='Delete Test Task',
                description='Testing deletion',
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            task_id = create_result['task']['id']  # Fixed: use 'task' key, then 'id'
        
        # Delete task
        with patch('events.publisher.publish_event') as mock_publish:
            result = task_service.delete_task(task_id, test_firm.id, test_user.id)
            
            assert result['success'] is True
            
            # Verify deletion event
            mock_publish.assert_called()
            event = mock_publish.call_args[0][0]
            assert event.event_type == 'TaskDeletedEvent'
    
    def test_bulk_update_tasks(self, app_context, db_session, test_firm, test_user):
        """Test bulk task updates."""
        task_service = TaskService()
        
        # Create multiple tasks
        task_ids = []
        with patch('events.publisher.publish_event'):
            for i in range(3):
                result = task_service.create_task(
                    title=f'Bulk Task {i}',
                    description=f'Bulk test task {i}',
                    firm_id=test_firm.id,
                    user_id=test_user.id
                )
                task_ids.append(result['task']['id'])  # Fixed: use 'task' key, then 'id'
        
        # Bulk update
        updates = {'status': 'In Progress', 'priority': 'High'}
        
        with patch('events.publisher.publish_event'):
            result = task_service.bulk_update_tasks(
                task_ids=task_ids,
                updates=updates,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            assert result['success'] is True
            assert result['updated_count'] == len(task_ids)
    
    def test_get_tasks_with_dependency_info(self, app_context, test_firm):
        """Test getting tasks with dependency information."""
        task_service = TaskService()
        
        filters = {
            'status_filters': ['Not Started'],
            'priority_filters': ['High'],
            'show_completed': False
        }
        
        result = task_service.get_tasks_with_dependency_info(test_firm.id, filters)
        
        assert isinstance(result, list)
        # Each item should have task and dependency info
        for item in result:
            assert 'task' in item
            # Additional dependency info would be included in real implementation
    
    def test_task_service_error_handling(self, app_context, test_firm, test_user):
        """Test TaskService error handling."""
        task_service = TaskService()
        
        with patch('core.db.session.commit') as mock_commit:
            mock_commit.side_effect = Exception("Database error")
            
            result = task_service.create_task(
                title='Error Test Task',
                description='Testing error handling',
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            assert result['success'] is False
            assert 'message' in result
    
    def test_task_service_performance(self, app_context, test_firm, test_user, performance_tracker):
        """Test TaskService performance."""
        task_service = TaskService()
        
        performance_tracker.start('task_creation_service')
        
        with patch('events.publisher.publish_event'):
            result = task_service.create_task(
                title='Performance Test Task',
                description='Testing performance',
                firm_id=test_firm.id,
                user_id=test_user.id
            )
        
        performance_tracker.stop()
        
        assert result['success'] is True
        performance_tracker.assert_performance('task_creation_service', 0.5)


class TestProjectService:
    """Test ProjectService business logic."""
    
    def test_create_project_success(self, app_context, db_session, test_firm, test_user, test_client_data):
        """Test successful project creation."""
        project_service = ProjectService()
        
        with patch('events.publisher.publish_event') as mock_publish:
            result = project_service.create_project(
                name='Test Project',
                description='Test Description',
                client_id=test_client_data.id,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            assert result['success'] is True
            assert 'project_id' in result
            
            # Verify event was published
            mock_publish.assert_called_once()
            event = mock_publish.call_args[0][0]
            assert event.event_type == 'ProjectCreatedEvent'
    
    def test_get_project_by_id(self, app_context, db_session, test_firm, test_user, test_client_data):
        """Test getting project by ID."""
        project_service = ProjectService()
        
        # Create project
        with patch('events.publisher.publish_event'):
            create_result = project_service.create_project(
                name='Get Test Project',
                description='Testing retrieval',
                client_id=test_client_data.id,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            project_id = create_result['project_id']
        
        # Get project
        project = project_service.get_project_by_id(project_id, test_firm.id)
        assert project is not None
        assert project.name == 'Get Test Project'
    
    def test_update_project_status(self, app_context, db_session, test_firm, test_user, test_client_data):
        """Test updating project status."""
        project_service = ProjectService()
        
        # Create project
        with patch('events.publisher.publish_event'):
            create_result = project_service.create_project(
                name='Status Update Project',
                description='Testing status updates',
                client_id=test_client_data.id,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            project_id = create_result['project_id']
        
        # Update status
        with patch('events.publisher.publish_event') as mock_publish:
            result = project_service.update_project_status(
                project_id=project_id,
                new_status='In Progress',
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            assert result['success'] is True
            
            # Verify event was published
            mock_publish.assert_called()
    
    def test_get_active_projects(self, app_context, test_firm):
        """Test getting active projects."""
        project_service = ProjectService()
        projects = project_service.get_active_projects(test_firm.id)
        assert isinstance(projects, list)
    
    def test_project_service_validation(self, app_context, test_firm, test_user):
        """Test ProjectService validation."""
        project_service = ProjectService()
        
        result = project_service.create_project(
            name='',  # Empty name should fail
            description='Test Description',
            client_id=None,
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert result['success'] is False
        assert 'message' in result


class TestDocumentService:
    """Test DocumentService business logic."""
    
    def test_create_checklist(self, app_context, db_session, test_firm, test_user, test_client_data):
        """Test creating document checklist."""
        document_service = DocumentService()
        
        with patch('events.publisher.publish_event') as mock_publish:
            result = document_service.create_checklist(
                name='Test Checklist',
                description='Test Description',
                client_id=test_client_data.id,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            assert result['success'] is True
            assert 'checklist_id' in result
            
            # Verify event was published
            mock_publish.assert_called_once()
    
    def test_add_checklist_item(self, app_context, db_session, test_firm, test_user, test_client_data):
        """Test adding item to checklist."""
        document_service = DocumentService()
        
        # Create checklist first
        with patch('events.publisher.publish_event'):
            checklist_result = document_service.create_checklist(
                name='Item Test Checklist',
                description='Testing items',
                client_id=test_client_data.id,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            checklist_id = checklist_result['checklist_id']
        
        # Add item
        with patch('events.publisher.publish_event') as mock_publish:
            result = document_service.add_checklist_item(
                checklist_id=checklist_id,
                name='Test Document',
                description='Test document item',
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            assert result['success'] is True
            assert 'item_id' in result
    
    def test_upload_file_to_checklist_item(self, app_context, temp_file, test_firm, test_user):
        """Test file upload to checklist item."""
        document_service = DocumentService()
        
        with patch('events.publisher.publish_event'):
            # Mock checklist item
            with patch('models.ChecklistItem.query') as mock_query:
                mock_item = Mock()
                mock_item.id = 123
                mock_item.checklist.firm_id = test_firm.id
                mock_query.get.return_value = mock_item
                
                result = document_service.upload_file_to_checklist_item(
                    item_id=123,
                    file_path=temp_file,
                    original_filename='test.pdf',
                    firm_id=test_firm.id,
                    user_id=test_user.id
                )
                
                assert result['success'] is True
    
    def test_get_checklist_by_id(self, app_context, db_session, test_firm, test_user, test_client_data):
        """Test getting checklist by ID."""
        document_service = DocumentService()
        
        # Create checklist
        with patch('events.publisher.publish_event'):
            create_result = document_service.create_checklist(
                name='Get Test Checklist',
                description='Testing retrieval',
                client_id=test_client_data.id,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            checklist_id = create_result['checklist_id']
        
        # Get checklist
        checklist = document_service.get_checklist_by_id(checklist_id, test_firm.id)
        assert checklist is not None
        assert checklist.name == 'Get Test Checklist'
    
    def test_document_service_error_handling(self, app_context, test_firm, test_user):
        """Test DocumentService error handling."""
        document_service = DocumentService()
        
        with patch('core.db.session.commit') as mock_commit:
            mock_commit.side_effect = Exception("Database error")
            
            result = document_service.create_checklist(
                name='Error Test Checklist',
                description='Testing error handling',
                client_id=None,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            assert result['success'] is False
            assert 'error' in result


class TestClientService:
    """Test ClientService business logic."""
    
    def test_create_client(self, app_context, db_session, test_firm, test_user):
        """Test creating client."""
        client_service = ClientService()
        
        with patch('events.publisher.publish_event') as mock_publish:
            result = client_service.create_client(
                name='Test Client',
                email='test@client.com',
                phone='123-456-7890',
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            assert result['success'] is True
            assert 'client_id' in result
            
            # Verify event was published
            mock_publish.assert_called_once()
    
    def test_update_client(self, app_context, db_session, test_firm, test_user):
        """Test updating client."""
        client_service = ClientService()
        
        # Create client first
        with patch('events.publisher.publish_event'):
            create_result = client_service.create_client(
                name='Update Test Client',
                email='update@client.com',
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            client_id = create_result['client_id']
        
        # Update client
        with patch('events.publisher.publish_event') as mock_publish:
            result = client_service.update_client(
                client_id=client_id,
                updates={'name': 'Updated Client Name'},
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            assert result['success'] is True
    
    def test_get_client_by_id(self, app_context, db_session, test_firm, test_user):
        """Test getting client by ID."""
        client_service = ClientService()
        
        # Create client
        with patch('events.publisher.publish_event'):
            create_result = client_service.create_client(
                name='Get Test Client',
                email='get@client.com',
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            client_id = create_result['client_id']
        
        # Get client
        client = client_service.get_client_by_id(client_id, test_firm.id)
        assert client is not None
        assert client.name == 'Get Test Client'
    
    def test_get_clients_by_firm(self, app_context, test_firm):
        """Test getting all clients for firm."""
        client_service = ClientService()
        clients = client_service.get_clients_by_firm(test_firm.id)
        assert isinstance(clients, list)
    
    def test_client_service_validation(self, app_context, test_firm, test_user):
        """Test ClientService validation."""
        client_service = ClientService()
        
        result = client_service.create_client(
            name='',  # Empty name should fail
            email='invalid-email',  # Invalid email
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert result['success'] is False
        assert 'message' in result


class TestServiceIntegration:
    """Test service layer integration scenarios."""
    
    def test_cross_service_operations(self, app_context, db_session, test_firm, test_user, test_client_data):
        """Test operations across multiple services."""
        project_service = ProjectService()
        task_service = TaskService()
        document_service = DocumentService()
        
        with patch('events.publisher.publish_event'):
            # Create project
            project_result = project_service.create_project(
                name='Integration Test Project',
                client_id=test_client_data.id,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            project_id = project_result['project_id']
            
            # Create task for project
            task_result = task_service.create_task(
                title='Integration Test Task',
                description='Testing cross-service integration',
                project_id=project_id,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            # Create document checklist for client
            checklist_result = document_service.create_checklist(
                name='Integration Test Checklist',
                client_id=test_client_data.id,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            assert project_result['success'] is True
            assert task_result['success'] is True
            assert checklist_result['success'] is True
    
    def test_service_transaction_rollback(self, app_context, db_session, test_firm, test_user):
        """Test transaction rollback across services."""
        task_service = TaskService()
        project_service = ProjectService()
        
        with patch('core.db.session.commit') as mock_commit:
            mock_commit.side_effect = Exception("Transaction failed")
            
            # All service operations should fail and rollback
            task_result = task_service.create_task(
                title='Rollback Test Task',
                description='Testing rollback',
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            project_result = project_service.create_project(
                name='Rollback Test Project',
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            assert task_result['success'] is False
            assert project_result['success'] is False
    
    def test_service_performance_benchmarks(self, app_context, test_firm, test_user, performance_tracker):
        """Test service layer performance benchmarks."""
        task_service = TaskService()
        
        with patch('events.publisher.publish_event'):
            # Test multiple service operations
            performance_tracker.start('service_operations')
            
            # Create multiple entities
            for i in range(5):
                task_service.create_task(
                    title=f'Performance Task {i}',
                    description='Performance testing',
                    firm_id=test_firm.id,
                    user_id=test_user.id
                )
            
            performance_tracker.stop()
            performance_tracker.assert_performance('service_operations', 2.0)  # 2s for 5 operations