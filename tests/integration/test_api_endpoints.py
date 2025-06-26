"""
Integration tests for HTTP API endpoints.
Tests API endpoints with real Flask test client, authentication, and data validation.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, timedelta

from models import Task, Project, Client, User, Firm


class TestTaskAPIEndpoints:
    """Test Task-related API endpoints."""
    
    def test_create_task_api(self, authenticated_session, test_firm, test_user, test_project):
        """Test task creation via API."""
        task_data = {
            'title': 'API Test Task',
            'description': 'Created via API',
            'project_id': test_project.id,
            'assignee_id': test_user.id,
            'due_date': '2024-12-31',
            'priority': 'High',
            'estimated_hours': 5.0
        }
        
        with patch('events.publisher.publish_event'):
            response = authenticated_session.post(
                '/api/tasks',
                data=json.dumps(task_data),
                content_type='application/json'
            )
        
        assert response.status_code == 201
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'task_id' in response_data
        assert response_data['message'] == 'Task created successfully'
    
    def test_get_task_api(self, authenticated_session, test_firm, test_user):
        """Test getting task via API."""
        # First create a task
        with patch('events.publisher.publish_event'):
            create_response = authenticated_session.post(
                '/api/tasks',
                data=json.dumps({
                    'title': 'Get Test Task',
                    'description': 'Testing GET endpoint'
                }),
                content_type='application/json'
            )
        
        create_data = json.loads(create_response.data)
        task_id = create_data['task_id']
        
        # Get the task
        response = authenticated_session.get(f'/api/tasks/{task_id}')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['id'] == task_id
        assert response_data['title'] == 'Get Test Task'
    
    def test_update_task_api(self, authenticated_session, test_firm, test_user):
        """Test updating task via API."""
        # Create task first
        with patch('events.publisher.publish_event'):
            create_response = authenticated_session.post(
                '/api/tasks',
                data=json.dumps({
                    'title': 'Update Test Task',
                    'description': 'Testing UPDATE endpoint'
                }),
                content_type='application/json'
            )
        
        create_data = json.loads(create_response.data)
        task_id = create_data['task_id']
        
        # Update the task
        update_data = {
            'title': 'Updated Task Title',
            'status': 'In Progress',
            'priority': 'High'
        }
        
        with patch('events.publisher.publish_event'):
            response = authenticated_session.put(
                f'/api/tasks/{task_id}',
                data=json.dumps(update_data),
                content_type='application/json'
            )
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
    
    def test_delete_task_api(self, authenticated_session, test_firm, test_user):
        """Test deleting task via API."""
        # Create task first
        with patch('events.publisher.publish_event'):
            create_response = authenticated_session.post(
                '/api/tasks',
                data=json.dumps({
                    'title': 'Delete Test Task',
                    'description': 'Testing DELETE endpoint'
                }),
                content_type='application/json'
            )
        
        create_data = json.loads(create_response.data)
        task_id = create_data['task_id']
        
        # Delete the task
        with patch('events.publisher.publish_event'):
            response = authenticated_session.delete(f'/api/tasks/{task_id}')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        
        # Verify task is deleted
        get_response = authenticated_session.get(f'/api/tasks/{task_id}')
        assert get_response.status_code == 404
    
    def test_list_tasks_api(self, authenticated_session, test_firm, test_user):
        """Test listing tasks via API."""
        # Create multiple tasks
        task_titles = ['List Task 1', 'List Task 2', 'List Task 3']
        
        with patch('events.publisher.publish_event'):
            for title in task_titles:
                authenticated_session.post(
                    '/api/tasks',
                    data=json.dumps({
                        'title': title,
                        'description': 'Testing list endpoint'
                    }),
                    content_type='application/json'
                )
        
        # Get task list
        response = authenticated_session.get('/api/tasks')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert isinstance(response_data, list)
        
        # Check that our created tasks are in the list
        task_titles_in_response = [task['title'] for task in response_data]
        for title in task_titles:
            assert title in task_titles_in_response
    
    def test_bulk_update_tasks_api(self, authenticated_session, test_firm, test_user):
        """Test bulk updating tasks via API."""
        # Create multiple tasks
        task_ids = []
        with patch('events.publisher.publish_event'):
            for i in range(3):
                response = authenticated_session.post(
                    '/api/tasks',
                    data=json.dumps({
                        'title': f'Bulk Task {i}',
                        'description': 'Testing bulk update'
                    }),
                    content_type='application/json'
                )
                data = json.loads(response.data)
                task_ids.append(data['task_id'])
        
        # Bulk update
        bulk_data = {
            'task_ids': task_ids,
            'updates': {
                'status': 'In Progress',
                'priority': 'High'
            }
        }
        
        with patch('events.publisher.publish_event'):
            response = authenticated_session.post(
                '/api/tasks/bulk-update',
                data=json.dumps(bulk_data),
                content_type='application/json'
            )
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert response_data['updated_count'] == len(task_ids)
    
    def test_task_api_validation(self, authenticated_session, test_firm, test_user):
        """Test API validation for task endpoints."""
        # Test missing required fields
        response = authenticated_session.post(
            '/api/tasks',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert 'error' in response_data
    
    def test_task_api_authentication(self, client, test_firm, test_user):
        """Test API authentication requirements."""
        # Test without authentication
        response = client.post(
            '/api/tasks',
            data=json.dumps({
                'title': 'Unauthorized Task',
                'description': 'Should fail'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 401
    
    def test_task_api_firm_isolation(self, authenticated_session, test_firm, test_user):
        """Test firm-level data isolation in API."""
        # Create task
        with patch('events.publisher.publish_event'):
            create_response = authenticated_session.post(
                '/api/tasks',
                data=json.dumps({
                    'title': 'Isolation Test Task',
                    'description': 'Testing firm isolation'
                }),
                content_type='application/json'
            )
        
        create_data = json.loads(create_response.data)
        task_id = create_data['task_id']
        
        # Try to access with different firm (simulate by changing session)
        with authenticated_session.session_transaction() as sess:
            original_firm_id = sess['firm_id']
            sess['firm_id'] = 999  # Different firm
        
        response = authenticated_session.get(f'/api/tasks/{task_id}')
        assert response.status_code == 404  # Should not find task from different firm
        
        # Restore original firm
        with authenticated_session.session_transaction() as sess:
            sess['firm_id'] = original_firm_id


class TestProjectAPIEndpoints:
    """Test Project-related API endpoints."""
    
    def test_create_project_api(self, authenticated_session, test_firm, test_user, test_client_data):
        """Test project creation via API."""
        project_data = {
            'name': 'API Test Project',
            'description': 'Created via API',
            'client_id': test_client_data.id,
            'assigned_user_id': test_user.id
        }
        
        with patch('events.publisher.publish_event'):
            response = authenticated_session.post(
                '/api/projects',
                data=json.dumps(project_data),
                content_type='application/json'
            )
        
        assert response.status_code == 201
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'project_id' in response_data
    
    def test_get_project_api(self, authenticated_session, test_firm, test_user, test_client_data):
        """Test getting project via API."""
        # Create project first
        with patch('events.publisher.publish_event'):
            create_response = authenticated_session.post(
                '/api/projects',
                data=json.dumps({
                    'name': 'Get Test Project',
                    'description': 'Testing GET endpoint',
                    'client_id': test_client_data.id
                }),
                content_type='application/json'
            )
        
        create_data = json.loads(create_response.data)
        project_id = create_data['project_id']
        
        # Get the project
        response = authenticated_session.get(f'/api/projects/{project_id}')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['id'] == project_id
        assert response_data['name'] == 'Get Test Project'
    
    def test_list_projects_api(self, authenticated_session, test_firm, test_user, test_client_data):
        """Test listing projects via API."""
        # Create multiple projects
        project_names = ['List Project 1', 'List Project 2']
        
        with patch('events.publisher.publish_event'):
            for name in project_names:
                authenticated_session.post(
                    '/api/projects',
                    data=json.dumps({
                        'name': name,
                        'description': 'Testing list endpoint',
                        'client_id': test_client_data.id
                    }),
                    content_type='application/json'
                )
        
        # Get project list
        response = authenticated_session.get('/api/projects')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert isinstance(response_data, list)
        
        # Check that our created projects are in the list
        project_names_in_response = [project['name'] for project in response_data]
        for name in project_names:
            assert name in project_names_in_response
    
    def test_update_project_status_api(self, authenticated_session, test_firm, test_user, test_client_data):
        """Test updating project status via API."""
        # Create project first
        with patch('events.publisher.publish_event'):
            create_response = authenticated_session.post(
                '/api/projects',
                data=json.dumps({
                    'name': 'Status Update Project',
                    'description': 'Testing status update',
                    'client_id': test_client_data.id
                }),
                content_type='application/json'
            )
        
        create_data = json.loads(create_response.data)
        project_id = create_data['project_id']
        
        # Update status
        with patch('events.publisher.publish_event'):
            response = authenticated_session.patch(
                f'/api/projects/{project_id}/status',
                data=json.dumps({'status': 'In Progress'}),
                content_type='application/json'
            )
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True


class TestDocumentAPIEndpoints:
    """Test Document-related API endpoints."""
    
    def test_create_checklist_api(self, authenticated_session, test_firm, test_user, test_client_data):
        """Test checklist creation via API."""
        checklist_data = {
            'name': 'API Test Checklist',
            'description': 'Created via API',
            'client_id': test_client_data.id
        }
        
        with patch('events.publisher.publish_event'):
            response = authenticated_session.post(
                '/api/checklists',
                data=json.dumps(checklist_data),
                content_type='application/json'
            )
        
        assert response.status_code == 201
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'checklist_id' in response_data
    
    def test_add_checklist_item_api(self, authenticated_session, test_firm, test_user, test_client_data):
        """Test adding checklist item via API."""
        # Create checklist first
        with patch('events.publisher.publish_event'):
            checklist_response = authenticated_session.post(
                '/api/checklists',
                data=json.dumps({
                    'name': 'Item Test Checklist',
                    'description': 'Testing item addition',
                    'client_id': test_client_data.id
                }),
                content_type='application/json'
            )
        
        checklist_data = json.loads(checklist_response.data)
        checklist_id = checklist_data['checklist_id']
        
        # Add item
        item_data = {
            'name': 'API Test Item',
            'description': 'Added via API'
        }
        
        with patch('events.publisher.publish_event'):
            response = authenticated_session.post(
                f'/api/checklists/{checklist_id}/items',
                data=json.dumps(item_data),
                content_type='application/json'
            )
        
        assert response.status_code == 201
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'item_id' in response_data
    
    def test_upload_file_api(self, authenticated_session, test_firm, test_user, test_client_data, temp_file):
        """Test file upload via API."""
        # Create checklist and item first
        with patch('events.publisher.publish_event'):
            checklist_response = authenticated_session.post(
                '/api/checklists',
                data=json.dumps({
                    'name': 'Upload Test Checklist',
                    'client_id': test_client_data.id
                }),
                content_type='application/json'
            )
            
            checklist_data = json.loads(checklist_response.data)
            checklist_id = checklist_data['checklist_id']
            
            item_response = authenticated_session.post(
                f'/api/checklists/{checklist_id}/items',
                data=json.dumps({
                    'name': 'Upload Test Item',
                    'description': 'Testing file upload'
                }),
                content_type='application/json'
            )
            
            item_data = json.loads(item_response.data)
            item_id = item_data['item_id']
        
        # Upload file
        with open(temp_file, 'rb') as f:
            with patch('events.publisher.publish_event'):
                response = authenticated_session.post(
                    f'/api/checklist-items/{item_id}/upload',
                    data={'file': (f, 'test.pdf')},
                    content_type='multipart/form-data'
                )
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
    
    def test_get_checklist_api(self, authenticated_session, test_firm, test_user, test_client_data):
        """Test getting checklist via API."""
        # Create checklist first
        with patch('events.publisher.publish_event'):
            create_response = authenticated_session.post(
                '/api/checklists',
                data=json.dumps({
                    'name': 'Get Test Checklist',
                    'description': 'Testing GET endpoint',
                    'client_id': test_client_data.id
                }),
                content_type='application/json'
            )
        
        create_data = json.loads(create_response.data)
        checklist_id = create_data['checklist_id']
        
        # Get the checklist
        response = authenticated_session.get(f'/api/checklists/{checklist_id}')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['id'] == checklist_id
        assert response_data['name'] == 'Get Test Checklist'


class TestClientAPIEndpoints:
    """Test Client-related API endpoints."""
    
    def test_create_client_api(self, authenticated_session, test_firm, test_user):
        """Test client creation via API."""
        client_data = {
            'name': 'API Test Client',
            'email': 'api@test.com',
            'phone': '555-0123',
            'address': '123 Test St'
        }
        
        with patch('events.publisher.publish_event'):
            response = authenticated_session.post(
                '/api/clients',
                data=json.dumps(client_data),
                content_type='application/json'
            )
        
        assert response.status_code == 201
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'client_id' in response_data
    
    def test_get_client_api(self, authenticated_session, test_firm, test_user):
        """Test getting client via API."""
        # Create client first
        with patch('events.publisher.publish_event'):
            create_response = authenticated_session.post(
                '/api/clients',
                data=json.dumps({
                    'name': 'Get Test Client',
                    'email': 'get@test.com'
                }),
                content_type='application/json'
            )
        
        create_data = json.loads(create_response.data)
        client_id = create_data['client_id']
        
        # Get the client
        response = authenticated_session.get(f'/api/clients/{client_id}')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['id'] == client_id
        assert response_data['name'] == 'Get Test Client'
    
    def test_list_clients_api(self, authenticated_session, test_firm, test_user):
        """Test listing clients via API."""
        # Create multiple clients
        client_names = ['List Client 1', 'List Client 2']
        
        with patch('events.publisher.publish_event'):
            for name in client_names:
                authenticated_session.post(
                    '/api/clients',
                    data=json.dumps({
                        'name': name,
                        'email': f'{name.lower().replace(" ", "")}@test.com'
                    }),
                    content_type='application/json'
                )
        
        # Get client list
        response = authenticated_session.get('/api/clients')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert isinstance(response_data, list)
        
        # Check that our created clients are in the list
        client_names_in_response = [client['name'] for client in response_data]
        for name in client_names:
            assert name in client_names_in_response


class TestAPIErrorHandling:
    """Test API error handling scenarios."""
    
    def test_api_404_handling(self, authenticated_session):
        """Test 404 error handling."""
        response = authenticated_session.get('/api/tasks/99999')
        assert response.status_code == 404
        
        response_data = json.loads(response.data)
        assert 'error' in response_data
    
    def test_api_400_validation_errors(self, authenticated_session):
        """Test 400 validation error handling."""
        # Send invalid data
        response = authenticated_session.post(
            '/api/tasks',
            data=json.dumps({
                'title': '',  # Empty title should fail validation
                'invalid_field': 'should be ignored'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert 'error' in response_data
    
    def test_api_500_server_errors(self, authenticated_session):
        """Test 500 server error handling."""
        with patch('services.task_service.TaskService.create_task') as mock_create:
            mock_create.side_effect = Exception("Database error")
            
            response = authenticated_session.post(
                '/api/tasks',
                data=json.dumps({
                    'title': 'Error Test Task',
                    'description': 'Should cause server error'
                }),
                content_type='application/json'
            )
            
            assert response.status_code == 500
            response_data = json.loads(response.data)
            assert 'error' in response_data
    
    def test_api_rate_limiting(self, authenticated_session):
        """Test API rate limiting (if implemented)."""
        # This would test rate limiting if implemented
        # For now, just ensure multiple requests work
        for i in range(5):
            response = authenticated_session.get('/api/tasks')
            assert response.status_code in [200, 429]  # 429 if rate limited


class TestAPIPerformance:
    """Test API performance benchmarks."""
    
    def test_api_response_times(self, authenticated_session, performance_tracker):
        """Test API response time benchmarks."""
        performance_tracker.start('api_request')
        
        response = authenticated_session.get('/api/tasks')
        
        performance_tracker.stop()
        
        assert response.status_code == 200
        performance_tracker.assert_performance('api_request', 1.0)  # 1 second max
    
    def test_api_bulk_operations_performance(self, authenticated_session, test_firm, test_user, performance_tracker):
        """Test bulk API operations performance."""
        # Create multiple tasks first
        task_ids = []
        with patch('events.publisher.publish_event'):
            for i in range(10):
                response = authenticated_session.post(
                    '/api/tasks',
                    data=json.dumps({
                        'title': f'Bulk Performance Task {i}',
                        'description': 'Performance testing'
                    }),
                    content_type='application/json'
                )
                data = json.loads(response.data)
                task_ids.append(data['task_id'])
        
        # Test bulk update performance
        performance_tracker.start('bulk_api_operation')
        
        bulk_data = {
            'task_ids': task_ids,
            'updates': {'status': 'In Progress'}
        }
        
        with patch('events.publisher.publish_event'):
            response = authenticated_session.post(
                '/api/tasks/bulk-update',
                data=json.dumps(bulk_data),
                content_type='application/json'
            )
        
        performance_tracker.stop()
        
        assert response.status_code == 200
        performance_tracker.assert_performance('bulk_api_operation', 2.0)  # 2 seconds for 10 tasks
    
    def test_api_concurrent_requests(self, authenticated_session, performance_tracker):
        """Test API handling of concurrent requests."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_api_request():
            try:
                response = authenticated_session.get('/api/tasks')
                results.put(('success', response.status_code))
            except Exception as e:
                results.put(('error', str(e)))
        
        performance_tracker.start('concurrent_api_requests')
        
        # Make concurrent requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_api_request)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        performance_tracker.stop()
        
        # Check results
        success_count = 0
        while not results.empty():
            result_type, result_data = results.get()
            if result_type == 'success' and result_data == 200:
                success_count += 1
        
        assert success_count >= 3  # At least 3 should succeed
        performance_tracker.assert_performance('concurrent_api_requests', 3.0)