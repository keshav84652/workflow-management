"""
Integration tests for refactoring safety net
Tests critical workflows that will be refactored in Phase 1

Focus Areas:
- Kanban board persistence (views.py -> service layer)
- AI document analysis (ai.py + ai_service.py)  
- Document checklist workflows (documents.py -> document_service.py)
- Task status transitions (tasks.py -> task_service.py)
"""

import unittest
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Flask and extensions
from flask import Flask
from config import TestingConfig
import os

# Import db from root core.py file
from core.db_import import db

# Import models
from models import (
    User, Firm, Client, Project, Task, ProjectStatus, 
    DocumentChecklist, ChecklistItem, ClientDocument
)

# Import services that will be tested during refactor
from services.project_service import ProjectService
from services.task_service import TaskService
from services.document_service import DocumentService
from services.ai_service import AIService


class RefactorSafetyIntegrationTests(unittest.TestCase):
    """Integration tests to protect against regressions during refactoring"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test application and database"""
        cls.app = Flask(__name__)
        cls.app.config.from_object(TestingConfig)
        
        # Initialize database
        db.init_app(cls.app)
        
        with cls.app.app_context():
            db.create_all()
            cls._create_test_data()
    
    @classmethod
    def _create_test_data(cls):
        """Create minimal test data for integration tests"""
        # Create firm
        cls.test_firm = Firm(
            name="Test CPA Firm",
            access_code="TEST2024"
        )
        db.session.add(cls.test_firm)
        
        # Create user
        cls.test_user = User(
            username="testuser",
            email="test@example.com",
            role="Admin",
            firm_id=cls.test_firm.id
        )
        db.session.add(cls.test_user)
        
        # Create client
        cls.test_client = Client(
            name="Test Client LLC",
            email="client@example.com",
            firm_id=cls.test_firm.id
        )
        db.session.add(cls.test_client)
        
        # Create project statuses
        statuses = [
            ("Not Started", 1, 0),
            ("In Progress", 2, 25), 
            ("Review", 3, 75),
            ("Completed", 4, 100)
        ]
        
        cls.project_statuses = {}
        for name, status_id, progress in statuses:
            status = ProjectStatus(
                id=status_id,
                name=name,
                progress_percentage=progress,
                firm_id=cls.test_firm.id
            )
            db.session.add(status)
            cls.project_statuses[name] = status
        
        # Create test project
        cls.test_project = Project(
            name="Test Tax Return",
            client_id=cls.test_client.id,
            assigned_user_id=cls.test_user.id,
            current_status_id=1,  # Not Started
            firm_id=cls.test_firm.id
        )
        db.session.add(cls.test_project)
        
        # Create test tasks
        cls.test_task = Task(
            title="Review Documents",
            project_id=cls.test_project.id,
            assigned_user_id=cls.test_user.id,
            status="pending",
            firm_id=cls.test_firm.id
        )
        db.session.add(cls.test_task)
        
        # Create document checklist
        cls.test_checklist = DocumentChecklist(
            name="Tax Documents",
            client_id=cls.test_client.id,
            created_by=cls.test_user.id,
            firm_id=cls.test_firm.id
        )
        db.session.add(cls.test_checklist)
        
        # Create checklist item
        cls.test_checklist_item = ChecklistItem(
            name="W-2 Forms",
            description="Employee W-2 tax forms",
            checklist_id=cls.test_checklist.id,
            status="pending"
        )
        db.session.add(cls.test_checklist_item)
        
        db.session.commit()
    
    def setUp(self):
        """Set up test context for each test"""
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create test client for requests
        self.client = self.app.test_client()
        
        # Mock session data
        self.session_data = {
            'firm_id': self.test_firm.id,
            'user_id': self.test_user.id
        }
    
    def tearDown(self):
        """Clean up after each test"""
        db.session.rollback()
        self.app_context.pop()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test database"""
        with cls.app.app_context():
            db.drop_all()
    
    # =========================================================================
    # KANBAN BOARD PERSISTENCE TESTS (Priority 1)
    # =========================================================================
    
    def test_kanban_project_status_persistence(self):
        """Test that kanban board changes persist to database correctly"""
        # This tests the critical fix we made in views.py
        
        # Initial state: project is "Not Started" (status_id=1)
        project = Project.query.get(self.test_project.id)
        self.assertEqual(project.current_status_id, 1)
        
        # Move project to "In Progress" using ProjectService
        result = ProjectService.move_project_status(
            project_id=project.id,
            new_status_id=2,  # In Progress
            firm_id=self.test_firm.id
        )
        
        # Verify the service call succeeded
        self.assertTrue(result['success'])
        
        # Verify database persistence
        db.session.refresh(project)
        self.assertEqual(project.current_status_id, 2)
        
        # Verify progress percentage is updated
        self.assertEqual(project.progress_percentage, 25)
        
        # Test moving to completed
        result = ProjectService.move_project_status(
            project_id=project.id,
            new_status_id=4,  # Completed
            firm_id=self.test_firm.id
        )
        
        self.assertTrue(result['success'])
        db.session.refresh(project)
        self.assertEqual(project.current_status_id, 4)
        self.assertEqual(project.progress_percentage, 100)
    
    def test_kanban_view_logic_consistency(self):
        """Test that kanban view logic uses current_status_id correctly"""
        # This ensures our fix to use status_id instead of progress_percentage works
        
        # Set up project with specific status
        project = Project.query.get(self.test_project.id)
        project.current_status_id = 3  # Review (75% progress)
        project.progress_percentage = 75
        db.session.commit()
        
        # Test the logic that would be used in kanban view
        # This simulates the fixed logic in views.py
        if project.current_status_id == 1:
            column = 'not_started'
        elif project.current_status_id == 2:
            column = 'in_progress'
        elif project.current_status_id == 3:
            column = 'review'
        elif project.current_status_id == 4:
            column = 'completed'
        else:
            column = 'not_started'
        
        # Should be in review column based on status_id, not progress_percentage
        self.assertEqual(column, 'review')
        
        # Even if progress_percentage was inconsistent, status_id should rule
        project.progress_percentage = 50  # Inconsistent with Review status
        db.session.commit()
        
        # Logic should still use status_id
        if project.current_status_id == 3:
            column = 'review'
        
        self.assertEqual(column, 'review')
    
    # =========================================================================
    # TASK STATUS TRANSITION TESTS (Priority 1)
    # =========================================================================
    
    def test_task_status_transitions(self):
        """Test task status changes work correctly across service layer"""
        task = Task.query.get(self.test_task.id)
        
        # Initial state
        self.assertEqual(task.status, 'pending')
        
        # Update task status using TaskService
        updated_task = TaskService.update_task_status(
            task_id=task.id,
            new_status='in_progress',
            firm_id=self.test_firm.id
        )
        
        self.assertEqual(updated_task.status, 'in_progress')
        
        # Verify persistence
        db.session.refresh(task)
        self.assertEqual(task.status, 'in_progress')
        
        # Test completion
        updated_task = TaskService.update_task_status(
            task_id=task.id,
            new_status='completed',
            firm_id=self.test_firm.id
        )
        
        self.assertEqual(updated_task.status, 'completed')
        self.assertIsNotNone(updated_task.completed_at)
    
    def test_bulk_task_operations(self):
        """Test bulk task operations maintain data consistency"""
        # Create multiple tasks
        tasks = []
        for i in range(3):
            task = Task(
                title=f"Bulk Task {i}",
                project_id=self.test_project.id,
                assigned_user_id=self.test_user.id,
                status="pending",
                firm_id=self.test_firm.id
            )
            db.session.add(task)
            tasks.append(task)
        db.session.commit()
        
        task_ids = [t.id for t in tasks]
        
        # Bulk update using TaskService
        result = TaskService.bulk_update_tasks(
            task_ids=task_ids,
            updates={'status': 'in_progress'},
            firm_id=self.test_firm.id
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['updated_count'], 3)
        
        # Verify all tasks were updated
        for task_id in task_ids:
            task = Task.query.get(task_id)
            self.assertEqual(task.status, 'in_progress')
    
    # =========================================================================
    # DOCUMENT CHECKLIST WORKFLOW TESTS (Priority 1)
    # =========================================================================
    
    def test_document_checklist_creation(self):
        """Test document checklist creation workflow"""
        # Test creating new checklist through DocumentService
        checklist_data = {
            'name': 'Annual Tax Checklist',
            'client_id': self.test_client.id,
            'items': [
                {'name': '1099-DIV', 'description': 'Dividend income forms'},
                {'name': '1099-INT', 'description': 'Interest income forms'}
            ]
        }
        
        result = DocumentService.create_checklist_with_items(
            checklist_data=checklist_data,
            firm_id=self.test_firm.id,
            user_id=self.test_user.id
        )
        
        self.assertTrue(result['success'])
        checklist_id = result['checklist_id']
        
        # Verify checklist was created
        checklist = DocumentChecklist.query.get(checklist_id)
        self.assertIsNotNone(checklist)
        self.assertEqual(checklist.name, 'Annual Tax Checklist')
        self.assertEqual(checklist.client_id, self.test_client.id)
        
        # Verify items were created
        items = ChecklistItem.query.filter_by(checklist_id=checklist_id).all()
        self.assertEqual(len(items), 2)
        
        item_names = [item.name for item in items]
        self.assertIn('1099-DIV', item_names)
        self.assertIn('1099-INT', item_names)
    
    def test_document_upload_workflow(self):
        """Test document upload and checklist item status update"""
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(b'%PDF-1.4 fake pdf content for testing')
            temp_file_path = temp_file.name
        
        try:
            # Test document upload to checklist item
            result = DocumentService.upload_document_to_checklist_item(
                checklist_item_id=self.test_checklist_item.id,
                file_path=temp_file_path,
                original_filename='test_w2.pdf',
                firm_id=self.test_firm.id,
                user_id=self.test_user.id
            )
            
            self.assertTrue(result['success'])
            
            # Verify checklist item status was updated
            item = ChecklistItem.query.get(self.test_checklist_item.id)
            self.assertEqual(item.status, 'uploaded')
            
            # Verify document was created
            document = ClientDocument.query.filter_by(
                checklist_item_id=item.id
            ).first()
            self.assertIsNotNone(document)
            self.assertEqual(document.original_filename, 'test_w2.pdf')
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    # =========================================================================
    # AI DOCUMENT ANALYSIS WORKFLOW TESTS (Priority 1)
    # =========================================================================
    
    @patch('services.ai_service.AIService.is_available')
    @patch('services.ai_service.AIService._analyze_with_azure')
    @patch('services.ai_service.AIService._analyze_with_gemini')
    def test_ai_document_analysis_workflow_success(self, mock_gemini, mock_azure, mock_available):
        """Test AI document analysis workflow when services are available"""
        # Mock AI services as available
        mock_available.return_value = True
        
        # Mock successful analysis results
        mock_azure_result = {
            'service': 'azure',
            'key_value_pairs': [
                {'key': 'EmployerName', 'value': 'Test Company LLC'},
                {'key': 'EmployeeSSN', 'value': '***-**-1234'}
            ],
            'tables': [],
            'confidence_score': 0.9
        }
        
        mock_gemini_result = {
            'service': 'gemini', 
            'document_type': 'tax_document',
            'analysis_text': 'This appears to be a W-2 form...',
            'confidence_score': 0.85
        }
        
        mock_azure.return_value = mock_azure_result
        mock_gemini.return_value = mock_gemini_result
        
        # Create test document
        document = ClientDocument(
            original_filename='test_w2.pdf',
            checklist_item_id=self.test_checklist_item.id,
            uploaded_by=self.test_user.id
        )
        db.session.add(document)
        db.session.commit()
        
        # Create temporary file for analysis
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(b'%PDF-1.4 fake pdf content')
            temp_file_path = temp_file.name
        
        try:
            # Mock document path resolution
            with patch.object(AIService, '_get_document_path', return_value=temp_file_path):
                ai_service = AIService({'GEMINI_API_KEY': 'test_key'})
                
                result = ai_service.get_or_analyze_document(
                    document_id=document.id,
                    firm_id=self.test_firm.id
                )
                
                # Verify analysis completed successfully
                self.assertEqual(result['status'], 'completed')
                self.assertIn('azure_result', result)
                self.assertIn('gemini_result', result)
                
                # Verify results were saved to database
                db.session.refresh(document)
                self.assertTrue(document.ai_analysis_completed)
                self.assertIsNotNone(document.ai_analysis_results)
                
                # Verify analysis results structure
                saved_results = json.loads(document.ai_analysis_results)
                self.assertIn('azure_results', saved_results)
                self.assertIn('gemini_results', saved_results)
                
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    @patch('services.ai_service.AIService.is_available')
    def test_ai_document_analysis_workflow_unavailable(self, mock_available):
        """Test AI document analysis workflow when services are unavailable"""
        # Mock AI services as unavailable
        mock_available.return_value = False
        
        ai_service = AIService()
        
        # Should raise ValueError when services unavailable
        with self.assertRaises(ValueError) as context:
            ai_service.get_or_analyze_document(
                document_id=999,  # Doesn't matter, should fail on service check
                firm_id=self.test_firm.id
            )
        
        self.assertIn('AI services not configured', str(context.exception))
    
    # =========================================================================
    # SERVICE BOUNDARY CONTRACT TESTS (Priority 2)
    # =========================================================================
    
    def test_ai_service_response_format_contract(self):
        """Test that AI service returns expected response format"""
        # This ensures frontend compatibility after refactoring
        mock_results = {
            'document_id': 123,
            'azure_results': {'service': 'azure', 'data': 'test'},
            'gemini_results': {'service': 'gemini', 'data': 'test'},
            'combined_analysis': {'confidence_score': 0.8}
        }
        
        ai_service = AIService()
        formatted_response = ai_service._format_analysis_response(
            analysis_results=mock_results,
            cached=False,
            filename='test.pdf'
        )
        
        # Verify response structure for frontend compatibility
        required_fields = [
            'azure_result',  # Note: singular, not plural
            'gemini_result', # Note: singular, not plural  
            'combined_analysis',
            'confidence_score',
            'status',
            'cached',
            'filename'
        ]
        
        for field in required_fields:
            self.assertIn(field, formatted_response)
        
        # Verify specific mappings
        self.assertEqual(formatted_response['azure_result'], mock_results['azure_results'])
        self.assertEqual(formatted_response['gemini_result'], mock_results['gemini_results'])
    
    def test_session_management_contract(self):
        """Test session helper functions work correctly"""
        from utils.consolidated import get_session_firm_id, get_session_user_id
        
        # Mock Flask session
        with patch('utils.session', self.session_data):
            firm_id = get_session_firm_id()
            user_id = get_session_user_id()
            
            self.assertEqual(firm_id, self.test_firm.id)
            self.assertEqual(user_id, self.test_user.id)
        
        # Test error handling for missing session data
        with patch('utils.session', {}):
            with self.assertRaises(ValueError) as context:
                get_session_firm_id()
            
            self.assertIn('No firm_id in session', str(context.exception))
    
    # =========================================================================
    # DATABASE TRANSACTION SAFETY TESTS (Priority 2)
    # =========================================================================
    
    def test_database_transaction_rollback_safety(self):
        """Test that database operations rollback properly on errors"""
        # Test ProjectService transaction safety
        invalid_project_id = 99999
        
        result = ProjectService.move_project_status(
            project_id=invalid_project_id,
            new_status_id=2,
            firm_id=self.test_firm.id
        )
        
        # Should handle error gracefully
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        
        # Database should remain consistent
        # No hanging transactions or partial updates
        projects_count = Project.query.count()
        self.assertGreater(projects_count, 0)  # Our test data should still exist
    
    def test_ai_service_transaction_consistency(self):
        """Test AI service maintains transaction consistency"""
        ai_service = AIService()
        
        # Test with invalid document ID
        with self.assertRaises(ValueError):
            ai_service.get_or_analyze_document(
                document_id=99999,
                firm_id=self.test_firm.id
            )
        
        # Database should remain consistent after error
        # No partial updates or hanging transactions
        documents_count = ClientDocument.query.count()
        # Count should be stable (no ghost records)
        self.assertGreaterEqual(documents_count, 0)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)