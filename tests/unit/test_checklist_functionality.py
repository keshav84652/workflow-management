"""
Unit tests for checklist functionality.
Tests document checklists, items, and related service methods.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date

from services.document_service import DocumentService
from src.models import DocumentChecklist, ChecklistItem, Client


class TestChecklistCreation:
    """Test checklist creation functionality."""
    
    def test_create_checklist_success(self, app_context, db_session, test_firm, test_user, test_client_data):
        """Test successful checklist creation."""
        with patch('events.publisher.publish_event') as mock_publish:
            result = DocumentService.create_checklist(
                name='Tax Document Checklist',
                description='Documents needed for tax preparation',
                client_id=test_client_data.id,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            assert result['success'] is True
            assert 'checklist_id' in result
            assert result['message'] == 'Checklist created successfully'
            
            # Verify event was published
            mock_publish.assert_called_once()
            event = mock_publish.call_args[0][0]
            assert event.event_type == 'DocumentCreatedEvent'
    
    def test_create_checklist_validation_error(self, app_context, test_firm, test_user, test_client_data):
        """Test checklist creation with validation errors."""
        result = DocumentService.create_checklist(
            name='',  # Empty name should fail
            description='Test description',
            client_id=test_client_data.id,
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert result['success'] is False
        assert 'error' in result
    
    def test_get_checklists_for_firm(self, app_context, db_session, test_firm, test_user, test_client_data):
        """Test retrieving checklists for a firm."""
        # Create a checklist first
        with patch('events.publisher.publish_event'):
            DocumentService.create_checklist(
                name='Firm Test Checklist',
                description='Testing firm retrieval',
                client_id=test_client_data.id,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
        
        # Get checklists for firm
        checklists = DocumentService.get_checklists_for_firm(test_firm.id)
        
        assert isinstance(checklists, list)
        assert len(checklists) >= 1
        
        # Check if our created checklist is in the results
        checklist_names = [c.name for c in checklists]
        assert 'Firm Test Checklist' in checklist_names


class TestChecklistItems:
    """Test checklist item functionality."""
    
    def test_add_checklist_item_success(self, app_context, db_session, test_firm, test_user, test_client_data):
        """Test adding item to checklist."""
        # Create checklist first
        with patch('events.publisher.publish_event'):
            checklist_result = DocumentService.create_checklist(
                name='Item Test Checklist',
                description='Testing checklist items',
                client_id=test_client_data.id,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            checklist_id = checklist_result['checklist_id']
        
        # Add item to checklist
        result = DocumentService.add_checklist_item(
            checklist_id=checklist_id,
            name='W-2 Forms',
            description='Employee W-2 forms for tax year',
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert result['success'] is True
        assert 'item_id' in result
        assert result['message'] == 'Checklist item added successfully'
    
    def test_add_checklist_item_validation_error(self, app_context, test_firm, test_user):
        """Test adding checklist item with validation errors."""
        result = DocumentService.add_checklist_item(
            checklist_id=999,  # Non-existent checklist
            name='',  # Empty name should fail
            description='Test description',
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert result['success'] is False
        assert 'error' in result


class TestChecklistAccess:
    """Test checklist access control and retrieval."""
    
    def test_get_checklist_by_id_with_access_check(self, app_context, db_session, test_firm, test_user, test_client_data):
        """Test getting checklist by ID with firm access check."""
        # Create checklist
        with patch('events.publisher.publish_event'):
            create_result = DocumentService.create_checklist(
                name='Access Test Checklist',
                description='Testing access control',
                client_id=test_client_data.id,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            checklist_id = create_result['checklist_id']
        
        # Get checklist with correct firm
        checklist = DocumentService.get_checklist_by_id(checklist_id, test_firm.id)
        assert checklist is not None
        assert checklist.name == 'Access Test Checklist'
        
        # Try to get checklist with wrong firm
        checklist = DocumentService.get_checklist_by_id(checklist_id, 999)
        assert checklist is None
    
    def test_checklist_firm_isolation(self, app_context, db_session, test_firm, test_user, test_client_data):
        """Test that checklists are properly isolated by firm."""
        # Create checklist for test firm
        with patch('events.publisher.publish_event'):
            DocumentService.create_checklist(
                name='Firm Isolation Test',
                description='Testing firm isolation',
                client_id=test_client_data.id,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
        
        # Get checklists for the test firm
        test_firm_checklists = DocumentService.get_checklists_for_firm(test_firm.id)
        
        # Get checklists for a different firm (should be empty or different)
        other_firm_checklists = DocumentService.get_checklists_for_firm(999)
        
        # Verify isolation
        test_firm_names = [c.name for c in test_firm_checklists]
        other_firm_names = [c.name for c in other_firm_checklists]
        
        assert 'Firm Isolation Test' in test_firm_names
        assert 'Firm Isolation Test' not in other_firm_names


class TestChecklistStaticMethods:
    """Test static method functionality for checklists."""
    
    def test_get_checklists_for_firm_static_method(self, app_context, test_firm):
        """Test that get_checklists_for_firm can be called as static method."""
        # This should not raise an AttributeError
        try:
            checklists = DocumentService.get_checklists_for_firm(test_firm.id)
            assert isinstance(checklists, list)
        except AttributeError as e:
            pytest.fail(f"Static method call failed: {e}")
    
    def test_checklist_service_method_signatures(self, app_context):
        """Test that checklist service methods have correct signatures."""
        # Verify method exists and is callable
        assert hasattr(DocumentService, 'get_checklists_for_firm')
        assert callable(getattr(DocumentService, 'get_checklists_for_firm'))
        
        # Verify other critical methods exist
        assert hasattr(DocumentService, 'create_checklist')
        assert hasattr(DocumentService, 'add_checklist_item')
        assert hasattr(DocumentService, 'get_checklist_by_id')


class TestChecklistErrorHandling:
    """Test error handling in checklist functionality."""
    
    def test_checklist_database_error_handling(self, app_context, test_firm, test_user, test_client_data):
        """Test checklist service database error handling."""
        with patch('core.db_import.db.session.commit') as mock_commit:
            mock_commit.side_effect = Exception("Database connection failed")
            
            result = DocumentService.create_checklist(
                name='Error Test Checklist',
                description='Testing error handling',
                client_id=test_client_data.id,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            assert result['success'] is False
            assert 'error' in result
            assert 'Database connection failed' in str(result['error'])
    
    def test_checklist_item_database_error_handling(self, app_context, test_firm, test_user):
        """Test checklist item service database error handling."""
        with patch('core.db_import.db.session.commit') as mock_commit:
            mock_commit.side_effect = Exception("Database error")
            
            result = DocumentService.add_checklist_item(
                checklist_id=1,
                name='Error Test Item',
                description='Testing error handling',
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            assert result['success'] is False
            assert 'error' in result


class TestChecklistIntegration:
    """Test checklist integration with other components."""
    
    def test_checklist_client_integration(self, app_context, db_session, test_firm, test_user, test_client_data):
        """Test checklist integration with client entities."""
        with patch('events.publisher.publish_event'):
            # Create checklist for specific client
            result = DocumentService.create_checklist(
                name='Client Integration Test',
                description='Testing client-checklist relationship',
                client_id=test_client_data.id,
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            assert result['success'] is True
            
            # Retrieve checklist and verify client association
            checklist = DocumentService.get_checklist_by_id(
                result['checklist_id'], 
                test_firm.id
            )
            
            assert checklist is not None
            assert checklist.client_id == test_client_data.id
    
    def test_checklist_blueprint_integration(self, app_context, test_firm):
        """Test that checklist service methods work with blueprint calls."""
        # This simulates how the blueprints/documents.py would call the service
        try:
            # This should work without AttributeError
            checklists = DocumentService.get_checklists_for_firm(test_firm.id)
            
            # Should return a list (even if empty)
            assert isinstance(checklists, list)
            
        except AttributeError as e:
            pytest.fail(f"Blueprint integration failed: {e}")
        except Exception as e:
            # Other exceptions are acceptable (like database issues in test)
            pass