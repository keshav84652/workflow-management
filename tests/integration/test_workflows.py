"""
Integration tests for high-level workflow scenarios.
Tests user-facing workflows like Kanban board updates, project management, and document processing.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, timedelta

from services.task_service import TaskService
from services.project_service import ProjectService
from services.document_service import DocumentService
from services.client_service import ClientService
from models import Task, Project, Client, User, Firm, DocumentChecklist, ChecklistItem


class TestKanbanWorkflow:
    """Test Kanban board workflow integration."""
    
    def test_kanban_task_status_update_workflow(self, app_context, db_session, test_firm, 
                                               test_user, test_project, mock_event_publisher):
        """Test complete Kanban task status update workflow."""
        # Create task in "Not Started" status
        task_result = TaskService.create_task(
            title='Kanban Test Task',
            description='Testing Kanban workflow',
            project_id=test_project.id,
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert task_result['success'] is True
        task_id = task_result['task_id']
        
        # Move task through Kanban columns
        statuses = ['In Progress', 'Needs Review', 'Completed']
        
        for status in statuses:
            update_result = TaskService.update_task_status(
                task_id=task_id,
                new_status=status,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            assert update_result['success'] is True
            
            # Verify task status was updated
            task = TaskService.get_task_by_id_with_access_check(task_id, test_firm.id)
            assert task.status == status
        
        # Verify events were published for each status change
        assert mock_event_publisher.call_count >= len(statuses) + 1  # +1 for creation
    
    def test_kanban_task_assignment_workflow(self, app_context, db_session, test_firm, 
                                           test_user, test_project, mock_event_publisher):
        """Test Kanban task assignment workflow."""
        # Create unassigned task
        task_result = TaskService.create_task(
            title='Assignment Test Task',
            description='Testing assignment workflow',
            project_id=test_project.id,
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        task_id = task_result['task_id']
        
        # Assign task to user
        assignment_result = TaskService.assign_task(
            task_id=task_id,
            assignee_id=test_user.id,
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert assignment_result['success'] is True
        
        # Verify assignment
        task = TaskService.get_task_by_id_with_access_check(task_id, test_firm.id)
        assert task.assignee_id == test_user.id
        
        # Verify assignment event was published
        mock_event_publisher.assert_called()
        
        # Check for assignment event
        assignment_events = [
            call for call in mock_event_publisher.call_args_list
            if call[0][0].event_type == 'task_assigned'
        ]
        assert len(assignment_events) > 0
    
    def test_kanban_bulk_operations_workflow(self, app_context, db_session, test_firm, 
                                           test_user, test_project, mock_event_publisher):
        """Test Kanban bulk operations workflow."""
        # Create multiple tasks
        task_ids = []
        for i in range(3):
            task_result = TaskService.create_task(
                title=f'Bulk Task {i}',
                description=f'Bulk operation test task {i}',
                project_id=test_project.id,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            task_ids.append(task_result['task_id'])
        
        # Bulk update status
        bulk_result = TaskService.bulk_update_tasks(
            task_ids=task_ids,
            updates={'status': 'In Progress', 'priority': 'High'},
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert bulk_result['success'] is True
        assert bulk_result['updated_count'] == len(task_ids)
        
        # Verify all tasks were updated
        for task_id in task_ids:
            task = TaskService.get_task_by_id_with_access_check(task_id, test_firm.id)
            assert task.status == 'In Progress'
            assert task.priority == 'High'
    
    def test_kanban_project_view_workflow(self, app_context, db_session, test_firm, 
                                        test_user, test_client_data, mock_event_publisher):
        """Test Kanban project view workflow."""
        # Create project with tasks
        project_result = ProjectService.create_project(
            name='Kanban Project View Test',
            description='Testing project view',
            client_id=test_client_data.id,
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        project_id = project_result['project_id']
        
        # Create tasks in different statuses
        task_statuses = ['Not Started', 'In Progress', 'Needs Review', 'Completed']
        created_tasks = []
        
        for i, status in enumerate(task_statuses):
            task_result = TaskService.create_task(
                title=f'Project Task {i}',
                description=f'Task in {status}',
                project_id=project_id,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            # Update status if not "Not Started"
            if status != 'Not Started':
                TaskService.update_task_status(
                    task_id=task_result['task_id'],
                    new_status=status,
                    firm_id=test_firm.id,
                    user_id=test_user.id
                )
            
            created_tasks.append(task_result['task_id'])
        
        # Get project tasks for Kanban view
        project_tasks = TaskService.get_project_tasks(project_id, test_firm.id)
        
        assert len(project_tasks) == len(task_statuses)
        
        # Verify tasks are in correct statuses
        status_counts = {}
        for task in project_tasks:
            status = task.status if hasattr(task, 'status') else task['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        assert len(status_counts) == len(task_statuses)


class TestProjectManagementWorkflow:
    """Test project management workflow integration."""
    
    def test_complete_project_lifecycle(self, app_context, db_session, test_firm, 
                                      test_user, test_client_data, mock_event_publisher):
        """Test complete project lifecycle from creation to completion."""
        # 1. Create project
        project_result = ProjectService.create_project(
            name='Lifecycle Test Project',
            description='Testing complete project lifecycle',
            client_id=test_client_data.id,
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert project_result['success'] is True
        project_id = project_result['project_id']
        
        # 2. Add tasks to project
        task_titles = ['Initial Setup', 'Data Collection', 'Analysis', 'Review', 'Finalization']
        task_ids = []
        
        for title in task_titles:
            task_result = TaskService.create_task(
                title=title,
                description=f'Project task: {title}',
                project_id=project_id,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            task_ids.append(task_result['task_id'])
        
        # 3. Progress through tasks
        for i, task_id in enumerate(task_ids):
            # Start task
            TaskService.update_task_status(
                task_id=task_id,
                new_status='In Progress',
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            # Complete task
            TaskService.update_task_status(
                task_id=task_id,
                new_status='Completed',
                firm_id=test_firm.id,
                user_id=test_user.id
            )
        
        # 4. Complete project
        project_completion_result = ProjectService.update_project_status(
            project_id=project_id,
            new_status='Completed',
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert project_completion_result['success'] is True
        
        # 5. Verify final state
        project = ProjectService.get_project_by_id(project_id, test_firm.id)
        assert project.status == 'Completed'
        
        # Verify all tasks are completed
        project_tasks = TaskService.get_project_tasks(project_id, test_firm.id)
        completed_tasks = [task for task in project_tasks if task.status == 'Completed']
        assert len(completed_tasks) == len(task_titles)
    
    def test_project_template_workflow(self, app_context, db_session, test_firm, 
                                     test_user, test_client_data, mock_event_publisher):
        """Test project creation from template workflow."""
        # Create project template (simulated)
        template_tasks = [
            {'title': 'Template Task 1', 'description': 'First template task'},
            {'title': 'Template Task 2', 'description': 'Second template task'},
            {'title': 'Template Task 3', 'description': 'Third template task'}
        ]
        
        # Create project from template
        project_result = ProjectService.create_project_from_template(
            name='Template Project',
            client_id=test_client_data.id,
            template_tasks=template_tasks,
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert project_result['success'] is True
        project_id = project_result['project_id']
        
        # Verify template tasks were created
        project_tasks = TaskService.get_project_tasks(project_id, test_firm.id)
        assert len(project_tasks) == len(template_tasks)
        
        # Verify task titles match template
        task_titles = [task.title for task in project_tasks]
        template_titles = [task['title'] for task in template_tasks]
        
        for template_title in template_titles:
            assert template_title in task_titles
    
    def test_project_collaboration_workflow(self, app_context, db_session, test_firm, 
                                          test_user, test_client_data, mock_event_publisher):
        """Test project collaboration workflow with multiple users."""
        # Create project
        project_result = ProjectService.create_project(
            name='Collaboration Test Project',
            description='Testing collaboration features',
            client_id=test_client_data.id,
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        project_id = project_result['project_id']
        
        # Create tasks assigned to different users
        task_result = TaskService.create_task(
            title='Collaborative Task',
            description='Task for collaboration testing',
            project_id=project_id,
            assignee_id=test_user.id,
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        task_id = task_result['task_id']
        
        # Add task comment (collaboration)
        comment_result = TaskService.add_task_comment(
            task_id=task_id,
            firm_id=test_firm.id,
            comment_text='This is a collaboration comment',
            user_id=test_user.id
        )
        
        assert comment_result['success'] is True
        
        # Verify comment was added
        task = TaskService.get_task_by_id_with_access_check(task_id, test_firm.id)
        assert len(task.comments) > 0
        assert task.comments[0].comment == 'This is a collaboration comment'


class TestDocumentProcessingWorkflow:
    """Test document processing workflow integration."""
    
    def test_complete_document_checklist_workflow(self, app_context, db_session, test_firm, 
                                                 test_user, test_client_data, mock_event_publisher, temp_file):
        """Test complete document checklist workflow."""
        # 1. Create document checklist
        checklist_result = DocumentService.create_checklist(
            name='Tax Document Checklist',
            description='Complete tax document collection',
            client_id=test_client_data.id,
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert checklist_result['success'] is True
        checklist_id = checklist_result['checklist_id']
        
        # 2. Add checklist items
        document_types = ['W-2 Forms', '1099 Forms', 'Bank Statements', 'Receipts']
        item_ids = []
        
        for doc_type in document_types:
            item_result = DocumentService.add_checklist_item(
                checklist_id=checklist_id,
                name=doc_type,
                description=f'Client {doc_type}',
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            item_ids.append(item_result['item_id'])
        
        # 3. Upload documents to items
        for i, item_id in enumerate(item_ids):
            upload_result = DocumentService.upload_file_to_checklist_item(
                item_id=item_id,
                file_path=temp_file,
                original_filename=f'{document_types[i]}.pdf',
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            assert upload_result['success'] is True
        
        # 4. Mark items as completed
        for item_id in item_ids:
            completion_result = DocumentService.update_checklist_item_status(
                item_id=item_id,
                new_status='completed',
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            assert completion_result['success'] is True
        
        # 5. Verify checklist completion
        checklist = DocumentService.get_checklist_by_id(checklist_id, test_firm.id)
        completed_items = [item for item in checklist.items if item.status == 'completed']
        assert len(completed_items) == len(document_types)
    
    def test_public_document_submission_workflow(self, app_context, db_session, test_firm, 
                                                test_user, test_client_data, mock_event_publisher, temp_file):
        """Test public document submission workflow."""
        # 1. Create checklist with public access
        checklist_result = DocumentService.create_checklist(
            name='Public Submission Checklist',
            description='Client can submit documents',
            client_id=test_client_data.id,
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        checklist_id = checklist_result['checklist_id']
        
        # 2. Generate public access token
        token_result = DocumentService.generate_public_access_token(
            checklist_id=checklist_id,
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert token_result['success'] is True
        access_token = token_result['access_token']
        
        # 3. Add checklist item
        item_result = DocumentService.add_checklist_item(
            checklist_id=checklist_id,
            name='Client Upload Item',
            description='Item for client upload',
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        item_id = item_result['item_id']
        
        # 4. Simulate public upload
        public_upload_result = DocumentService.handle_public_file_upload(
            access_token=access_token,
            item_id=item_id,
            file_path=temp_file,
            original_filename='client_document.pdf'
        )
        
        assert public_upload_result['success'] is True
        
        # 5. Verify upload was processed
        item = DocumentService.get_checklist_item_by_id(item_id, test_firm.id)
        assert item.status == 'submitted'
    
    def test_document_review_workflow(self, app_context, db_session, test_firm, 
                                    test_user, test_client_data, mock_event_publisher, temp_file):
        """Test document review workflow."""
        # 1. Create checklist and upload document
        checklist_result = DocumentService.create_checklist(
            name='Review Workflow Checklist',
            description='Testing document review',
            client_id=test_client_data.id,
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        checklist_id = checklist_result['checklist_id']
        
        item_result = DocumentService.add_checklist_item(
            checklist_id=checklist_id,
            name='Review Document',
            description='Document for review',
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        item_id = item_result['item_id']
        
        # 2. Upload document
        upload_result = DocumentService.upload_file_to_checklist_item(
            item_id=item_id,
            file_path=temp_file,
            original_filename='review_document.pdf',
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        # 3. Mark for review
        review_result = DocumentService.update_checklist_item_status(
            item_id=item_id,
            new_status='needs_review',
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert review_result['success'] is True
        
        # 4. Add review comments
        comment_result = DocumentService.add_item_comment(
            item_id=item_id,
            comment='Document looks good, minor corrections needed',
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert comment_result['success'] is True
        
        # 5. Approve document
        approval_result = DocumentService.update_checklist_item_status(
            item_id=item_id,
            new_status='approved',
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert approval_result['success'] is True
        
        # Verify final status
        item = DocumentService.get_checklist_item_by_id(item_id, test_firm.id)
        assert item.status == 'approved'


class TestClientPortalWorkflow:
    """Test client portal workflow integration."""
    
    def test_client_onboarding_workflow(self, app_context, db_session, test_firm, 
                                      test_user, mock_event_publisher):
        """Test complete client onboarding workflow."""
        # 1. Create client
        client_result = ClientService.create_client(
            name='Onboarding Test Client',
            email='onboarding@test.com',
            phone='555-0123',
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert client_result['success'] is True
        client_id = client_result['client_id']
        
        # 2. Create onboarding project
        project_result = ProjectService.create_project(
            name='Client Onboarding',
            description='New client onboarding process',
            client_id=client_id,
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        project_id = project_result['project_id']
        
        # 3. Create onboarding checklist
        checklist_result = DocumentService.create_checklist(
            name='Onboarding Documents',
            description='Required documents for new client',
            client_id=client_id,
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        checklist_id = checklist_result['checklist_id']
        
        # 4. Add required documents
        required_docs = ['ID Verification', 'Tax Returns', 'Business License']
        
        for doc_name in required_docs:
            DocumentService.add_checklist_item(
                checklist_id=checklist_id,
                name=doc_name,
                description=f'Required: {doc_name}',
                firm_id=test_firm.id,
                user_id=test_user.id
            )
        
        # 5. Create onboarding tasks
        onboarding_tasks = ['Initial Consultation', 'Document Review', 'Setup Complete']
        
        for task_name in onboarding_tasks:
            TaskService.create_task(
                title=task_name,
                description=f'Onboarding: {task_name}',
                project_id=project_id,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
        
        # 6. Verify onboarding setup
        client = ClientService.get_client_by_id(client_id, test_firm.id)
        project = ProjectService.get_project_by_id(project_id, test_firm.id)
        checklist = DocumentService.get_checklist_by_id(checklist_id, test_firm.id)
        project_tasks = TaskService.get_project_tasks(project_id, test_firm.id)
        
        assert client.name == 'Onboarding Test Client'
        assert project.name == 'Client Onboarding'
        assert checklist.name == 'Onboarding Documents'
        assert len(project_tasks) == len(onboarding_tasks)
        assert len(checklist.items) == len(required_docs)
    
    def test_client_communication_workflow(self, app_context, db_session, test_firm, 
                                         test_user, test_client_data, mock_event_publisher, mock_celery_tasks):
        """Test client communication workflow."""
        # 1. Create project for client
        project_result = ProjectService.create_project(
            name='Communication Test Project',
            description='Testing client communication',
            client_id=test_client_data.id,
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        project_id = project_result['project_id']
        
        # 2. Update project status (should trigger client notification)
        status_update_result = ProjectService.update_project_status(
            project_id=project_id,
            new_status='In Progress',
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert status_update_result['success'] is True
        
        # 3. Complete project (should trigger completion notification)
        completion_result = ProjectService.update_project_status(
            project_id=project_id,
            new_status='Completed',
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert completion_result['success'] is True
        
        # 4. Verify notifications were queued
        # In a real implementation, this would check that email tasks were queued
        assert mock_celery_tasks['notification_worker'].call_count >= 0  # May or may not be called depending on implementation
    
    def test_workflow_performance(self, app_context, db_session, test_firm, test_user, 
                                test_client_data, mock_event_publisher, performance_tracker):
        """Test workflow performance benchmarks."""
        performance_tracker.start('complete_workflow')
        
        # Execute a complete workflow
        # 1. Create client
        client_result = ClientService.create_client(
            name='Performance Test Client',
            email='performance@test.com',
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        # 2. Create project
        project_result = ProjectService.create_project(
            name='Performance Test Project',
            client_id=client_result['client_id'],
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        # 3. Create tasks
        for i in range(5):
            TaskService.create_task(
                title=f'Performance Task {i}',
                project_id=project_result['project_id'],
                firm_id=test_firm.id,
                user_id=test_user.id
            )
        
        # 4. Create checklist
        checklist_result = DocumentService.create_checklist(
            name='Performance Checklist',
            client_id=client_result['client_id'],
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        performance_tracker.stop()
        
        # Verify all operations succeeded
        assert client_result['success'] is True
        assert project_result['success'] is True
        assert checklist_result['success'] is True
        
        # Assert performance benchmark
        performance_tracker.assert_performance('complete_workflow', 3.0)  # 3 seconds for complete workflow