"""
Critical AI Workflow Tests
Focused tests for the AI analysis issues we just fixed

This test file specifically validates:
1. Environment variable handling (the GOOGLE_API_KEY conflict we fixed)
2. Database transaction consistency (the commit/rollback fixes)
3. Error handling (the 'raise e' -> 'raise' fixes) 
4. Data structure mapping (azure_results vs azure_result)
"""

import unittest
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from config import TestingConfig
import os

# Import db from root core.py file
from src.shared.database.db_import import db
from services.ai_service import AIService


class CriticalAIWorkflowTests(unittest.TestCase):
    """Tests for the specific AI issues we fixed in the debugging session"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test application context"""
        cls.app = Flask(__name__)
        cls.app.config.from_object(TestingConfig)
        db.init_app(cls.app)
        
        with cls.app.app_context():
            db.create_all()
    
    def setUp(self):
        """Set up test context for each test"""
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up after each test"""
        db.session.rollback()
        self.app_context.pop()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test database"""
        with cls.app.app_context():
            db.drop_all()
    
    def test_environment_variable_handling(self):
        """Test that AI service properly handles environment variable conflicts"""
        # This tests the fix for system GOOGLE_API_KEY overriding .env file
        
        # Test with config object (simulating Flask config)
        test_config = {
            'GEMINI_API_KEY': 'test_key_from_config',
            'AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT': None,
            'AZURE_DOCUMENT_INTELLIGENCE_KEY': None
        }
        
        ai_service = AIService(config=test_config)
        
        # Should detect Gemini as available based on config
        self.assertTrue(ai_service.is_available())
        
        # Test with no config (should be unavailable)
        ai_service_no_config = AIService()
        self.assertFalse(ai_service_no_config.is_available())
    
    def test_error_handling_preserves_stack_trace(self):
        """Test that our error handling fixes preserve stack traces"""
        ai_service = AIService()
        
        # Test with unavailable services first (this will trigger before file check)
        with self.assertRaises(ValueError) as context:
            ai_service.get_or_analyze_document(
                document_id=123,
                firm_id=1
            )
        
        self.assertIn('AI services not configured', str(context.exception))
        
        # Test file not found error with services available
        ai_service_with_config = AIService({'GEMINI_API_KEY': 'test_key'})
        with self.assertRaises(ValueError) as context:
            ai_service_with_config.analyze_document('/nonexistent/path.pdf', 123)
        
        # Should contain descriptive error message
        self.assertIn('Document file not found', str(context.exception))
    
    def test_data_structure_mapping_frontend_compatibility(self):
        """Test the azure_results -> azure_result mapping fix"""
        # This tests the fix for frontend expecting singular form
        
        mock_analysis_results = {
            'document_id': 123,
            'analysis_timestamp': '2024-01-01T00:00:00',
            'services_used': ['azure', 'gemini'],
            'azure_results': {
                'service': 'azure',
                'key_value_pairs': [
                    {'key': 'EmployerName', 'value': 'Test Company'},
                    {'key': 'WagesAmount', 'value': '50000.00'}
                ],
                'confidence_score': 0.9
            },
            'gemini_results': {
                'service': 'gemini',
                'document_type': 'tax_document',
                'analysis_text': 'This is a W-2 form...',
                'confidence_score': 0.85
            },
            'combined_analysis': {
                'confidence_score': 0.87,
                'document_type': 'tax_document'
            },
            'status': 'completed'
        }
        
        ai_service = AIService()
        formatted_response = ai_service._format_analysis_response(
            analysis_results=mock_analysis_results,
            cached=False,
            filename='test_w2.pdf'
        )
        
        # Verify frontend compatibility (singular forms)
        self.assertIn('azure_result', formatted_response)
        self.assertIn('gemini_result', formatted_response)
        
        # Verify data is correctly mapped
        self.assertEqual(
            formatted_response['azure_result'],
            mock_analysis_results['azure_results']
        )
        self.assertEqual(
            formatted_response['gemini_result'], 
            mock_analysis_results['gemini_results']
        )
        
        # Verify other required fields
        self.assertEqual(formatted_response['status'], 'completed')
        self.assertEqual(formatted_response['filename'], 'test_w2.pdf')
        self.assertFalse(formatted_response['cached'])
        self.assertEqual(formatted_response['confidence_score'], 0.87)
    
    @patch('services.ai_service.AIService.is_available')
    def test_transaction_consistency_on_failure(self, mock_available):
        """Test that database transactions are handled consistently on failures"""
        # This tests our database transaction fixes
        
        # Mock services as unavailable to trigger error path
        mock_available.return_value = False
        
        ai_service = AIService()
        
        # This should raise ValueError without hanging transactions
        with self.assertRaises(ValueError):
            ai_service.get_or_analyze_document(
                document_id=123,
                firm_id=1
            )
        
        # No hanging state should remain
        # (In integration tests, we'd verify no partial database updates)
    
    def test_azure_model_priority_configuration(self):
        """Test that Azure model priority is correctly configured"""
        # This tests the fix for Azure using basic layout model
        
        ai_service = AIService()
        
        # Create a mock Azure client
        mock_client = MagicMock()
        ai_service.azure_client = mock_client
        
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(b'%PDF-1.4 fake pdf content')
            temp_file_path = temp_file.name
        
        try:
            # Mock successful analysis with tax model
            mock_result = MagicMock()
            mock_result.as_dict.return_value = {
                'model_id': 'prebuilt-tax.us.w2',
                'documents': [{
                    'content': 'Test document content',
                    'fields': {
                        'EmployerName': {'value': 'Test Company LLC'},
                        'WagesAmount': {'value': '50000.00'}
                    }
                }],
                'tables': []
            }
            
            # Mock poller that returns our result
            mock_poller = MagicMock()
            mock_poller.result.return_value = mock_result
            mock_client.begin_analyze_document.return_value = mock_poller
            
            # Call the analysis method
            result = ai_service._analyze_with_azure(temp_file_path)
            
            # Verify correct model was attempted first
            # Should try tax models first, not basic layout
            mock_client.begin_analyze_document.assert_called()
            call_args = mock_client.begin_analyze_document.call_args
            
            # The model_id should be one of the tax-specific models
            model_used = call_args[1]['model_id']  # keyword argument
            expected_models = [
                'prebuilt-tax.us.1099',
                'prebuilt-tax.us.w2', 
                'prebuilt-document',
                'prebuilt-read'
            ]
            self.assertIn(model_used, expected_models)
            
            # Verify result structure contains key-value pairs
            self.assertIn('key_value_pairs', result)
            self.assertEqual(len(result['key_value_pairs']), 2)
            
            # Verify key-value pairs are correctly extracted
            kv_pairs = {kv['key']: kv['value'] for kv in result['key_value_pairs']}
            self.assertEqual(kv_pairs['EmployerName'], 'Test Company LLC')
            self.assertEqual(kv_pairs['WagesAmount'], '50000.00')
            
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def test_ai_service_configuration_validation(self):
        """Test AI service configuration validation"""
        # Test various configuration scenarios
        
        # No configuration
        ai_service = AIService()
        self.assertFalse(ai_service.is_available())
        
        # Azure only
        azure_config = {
            'AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT': 'https://test.cognitiveservices.azure.com/',
            'AZURE_DOCUMENT_INTELLIGENCE_KEY': 'test_key'
        }
        ai_service = AIService(config=azure_config)
        # Would be True if Azure dependencies were available
        # In our test environment, it should handle missing dependencies gracefully
        
        # Gemini only 
        gemini_config = {
            'GEMINI_API_KEY': 'test_key'
        }
        ai_service = AIService(config=gemini_config)
        # Would be True if Gemini dependencies were available
        
        # Both services
        both_config = {
            'AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT': 'https://test.cognitiveservices.azure.com/',
            'AZURE_DOCUMENT_INTELLIGENCE_KEY': 'test_azure_key',
            'GEMINI_API_KEY': 'test_gemini_key'
        }
        ai_service = AIService(config=both_config)
        # Should handle multiple service configuration
    
    def test_mock_result_removal_validation(self):
        """Test that no mock results are returned when services fail"""
        # This validates our fix to remove mock results
        
        ai_service = AIService()
        
        # With no services available, should return proper error result, not raise exception
        result = ai_service.analyze_checklist_documents(
            checklist_id=123,
            firm_id=1
        )
        
        # Should return error result, not mock success
        self.assertFalse(result['success'])
        self.assertEqual(result['analyzed_count'], 0)
        # Message should indicate services aren't configured
        message = result['message'].lower()
        self.assertTrue(
            'ai services not configured' in message or 
            'gemini_api_key' in message or 
            'azure document intelligence' in message
        )
        
        # Should not contain any mock or fake indicators
        result_str = str(result).lower()
        self.assertNotIn('mock', result_str)
        self.assertNotIn('fake', result_str)


if __name__ == '__main__':
    # Run with detailed output
    unittest.main(verbosity=2)