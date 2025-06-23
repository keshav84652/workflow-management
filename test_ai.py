#!/usr/bin/env python3
"""
Test script for AI service functionality
"""

from app import app
from services.ai_service import AIService
import tempfile
import os

def test_ai_service():
    """Test AI service with mock configuration"""
    
    with app.app_context():
        print("🧪 Testing AI Service...")
        
        # Test 1: No configuration (should use mock)
        print("\n1. Testing without API keys (should use mock):")
        ai_service = AIService({})
        print(f"   Available: {ai_service.is_available()}")
        
        # Create a test text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a test invoice for tax purposes.\nTotal: $1,234.56\nDate: 2024-01-15")
            test_file = f.name
        
        try:
            results = ai_service.analyze_document(test_file, 999)
            print(f"   Analysis completed: {results['status']}")
            print(f"   Document type: {results.get('document_type', 'N/A')}")
            print(f"   Confidence: {results.get('confidence_score', 0):.2f}")
            print(f"   Services used: {results.get('services_used', [])}")
        finally:
            os.unlink(test_file)
        
        # Test 2: With fake API keys (should attempt real analysis but gracefully fall back)
        print("\n2. Testing with fake API keys:")
        fake_config = {
            'AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT': 'https://fake.cognitiveservices.azure.com/',
            'AZURE_DOCUMENT_INTELLIGENCE_KEY': 'fake_key_12345',
            'GEMINI_API_KEY': 'fake_gemini_key_67890'
        }
        
        ai_service_with_config = AIService(fake_config)
        print(f"   Available: {ai_service_with_config.is_available()}")
        
        # Create another test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Tax Form 1040\nAdjusted Gross Income: $75,000\nTax Year: 2024")
            test_file = f.name
        
        try:
            results = ai_service_with_config.analyze_document(test_file, 998)
            print(f"   Analysis completed: {results['status']}")
            print(f"   Document type: {results.get('document_type', 'N/A')}")
            print(f"   Services used: {results.get('services_used', [])}")
        except Exception as e:
            print(f"   Expected error with fake keys: {e}")
        finally:
            os.unlink(test_file)
        
        print("\n✅ AI Service tests completed!")

if __name__ == "__main__":
    test_ai_service()