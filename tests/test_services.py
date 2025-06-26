"""
Basic test infrastructure for service layer
MVP-focused tests for core business logic
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import TestingConfig


class TestServiceLayer(unittest.TestCase):
    """Basic tests for service layer functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = TestingConfig()
    
    def test_config_ai_services_detection(self):
        """Test AI services auto-detection in config"""
        # Test logic of AI_SERVICES_AVAILABLE property
        config = TestingConfig()
        
        # Clear any existing keys for clean test
        config.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = None
        config.AZURE_DOCUMENT_INTELLIGENCE_KEY = None
        config.GEMINI_API_KEY = None
        
        # Should be False with no keys
        self.assertFalse(config.AI_SERVICES_AVAILABLE)
        
        # Test with Azure keys
        config.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = "https://test.cognitiveservices.azure.com/"
        config.AZURE_DOCUMENT_INTELLIGENCE_KEY = "test_key"
        self.assertTrue(config.AI_SERVICES_AVAILABLE)
        
        # Test with Gemini key only
        config.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = None
        config.AZURE_DOCUMENT_INTELLIGENCE_KEY = None
        config.GEMINI_API_KEY = "test_gemini_key"
        self.assertTrue(config.AI_SERVICES_AVAILABLE)
    
    def test_testing_config_setup(self):
        """Verify testing configuration is properly set up"""
        self.assertTrue(self.config.TESTING)
        self.assertEqual(self.config.SQLALCHEMY_DATABASE_URI, 'sqlite:///:memory:')
        self.assertFalse(self.config.WTF_CSRF_ENABLED)
    
    def test_activity_service_basic_functionality(self):
        """Test ActivityService basic operations"""
        from services.activity_service import ActivityService
        
        # Test that the service can be imported and has expected methods
        self.assertTrue(hasattr(ActivityService, 'create_activity_log'))
        self.assertTrue(hasattr(ActivityService, 'get_recent_activity'))
        self.assertTrue(callable(ActivityService.create_activity_log))
        self.assertTrue(callable(ActivityService.get_recent_activity))
    
    def test_attachment_service_basic_functionality(self):
        """Test AttachmentService basic operations"""
        from services.attachment_service import AttachmentService
        
        # Test service instantiation and basic methods
        service = AttachmentService()
        self.assertTrue(hasattr(service, 'is_allowed_file'))
        self.assertTrue(hasattr(service, 'upload_file'))
        self.assertTrue(callable(service.is_allowed_file))
        self.assertTrue(callable(service.upload_file))
        
        # Test file extension validation
        self.assertFalse(service.is_allowed_file('test.exe'))
        self.assertTrue(service.is_allowed_file('test.pdf'))
        self.assertTrue(service.is_allowed_file('test.jpg'))
    
    def test_task_service_utility_functions(self):
        """Test TaskService utility functions"""
        from services.task_service import TaskService
        from datetime import date, timedelta
        
        # Test calculate_next_due_date
        today = date.today()
        
        # Test daily recurrence
        next_date = TaskService.calculate_next_due_date('daily', today)
        self.assertEqual(next_date, today + timedelta(days=1))
        
        # Test weekly recurrence
        next_date = TaskService.calculate_next_due_date('weekly', today)
        self.assertEqual(next_date, today + timedelta(weeks=1))
        
        # Test invalid recurrence
        next_date = TaskService.calculate_next_due_date('invalid', today)
        self.assertIsNone(next_date)
    
    def test_client_service_basic_functionality(self):
        """Test ClientService basic operations"""
        from services.client_service import ClientService
        
        # Test that the service has expected methods
        self.assertTrue(hasattr(ClientService, 'find_or_create_client'))
        self.assertTrue(hasattr(ClientService, 'get_client_statistics'))
        self.assertTrue(callable(ClientService.find_or_create_client))
        self.assertTrue(callable(ClientService.get_client_statistics))
    
    def test_ai_service_basic_functionality(self):
        """Test AIService basic operations"""
        from services.ai_service import AIService
        
        # Test service instantiation and basic methods
        service = AIService()
        self.assertTrue(hasattr(service, 'get_or_analyze_document'))
        self.assertTrue(hasattr(service, 'analyze_checklist_documents'))
        self.assertTrue(callable(service.get_or_analyze_document))
        self.assertTrue(callable(service.analyze_checklist_documents))


if __name__ == '__main__':
    unittest.main()