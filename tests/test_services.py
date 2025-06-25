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
        # Test with no API keys
        config = TestingConfig()
        self.assertFalse(config.AI_SERVICES_AVAILABLE)
        
        # Test with Azure keys
        config.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = "https://test.cognitiveservices.azure.com/"
        config.AZURE_DOCUMENT_INTELLIGENCE_KEY = "test_key"
        self.assertTrue(config.AI_SERVICES_AVAILABLE)
        
        # Test with Gemini key
        config = TestingConfig()
        config.GEMINI_API_KEY = "test_gemini_key"
        self.assertTrue(config.AI_SERVICES_AVAILABLE)
    
    def test_testing_config_setup(self):
        """Verify testing configuration is properly set up"""
        self.assertTrue(self.config.TESTING)
        self.assertEqual(self.config.SQLALCHEMY_DATABASE_URI, 'sqlite:///:memory:')
        self.assertFalse(self.config.WTF_CSRF_ENABLED)


if __name__ == '__main__':
    unittest.main()