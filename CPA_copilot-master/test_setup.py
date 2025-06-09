"""
Quick test script to verify the CPA Copilot setup
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def test_imports():
    """Test that all major imports work."""
    print("Testing imports...")
    
    try:
        from backend.utils.config import settings
        print("✅ Configuration loaded")
        print(f"   Azure Endpoint: {settings.azure_endpoint}")
        print(f"   Upload folder: {settings.upload_folder}")
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False
    
    try:
        from backend.services.azure_service import AzureDocumentService
        print("✅ Azure service imported")
    except Exception as e:
        print(f"❌ Azure service error: {e}")
        return False
    
    try:
        from backend.services.gemini_service import GeminiDocumentService
        print("✅ Gemini service imported")
    except Exception as e:
        print(f"❌ Gemini service error: {e}")
        return False
    
    try:
        from backend.services.document_processor import DocumentProcessor
        print("✅ Document processor imported")
    except Exception as e:
        print(f"❌ Document processor error: {e}")
        return False
    
    try:
        from backend.models.document import ProcessedDocument, FileUpload
        print("✅ Data models imported")
    except Exception as e:
        print(f"❌ Data models error: {e}")
        return False
    
    try:
        from backend.services.enhanced_tax_processor import TaxDocumentProcessor
        print("✅ Tax processor imported")
    except Exception as e:
        print(f"❌ Tax processor error: {e}")
        return False
    
    return True


def test_azure_connection():
    """Test Azure connection (requires valid API key)."""
    print("\nTesting Azure connection...")
    
    try:
        from backend.services.azure_service import AzureDocumentService
        service = AzureDocumentService()
        
        # Just test that client is created
        if service.client:
            print("✅ Azure client initialized")
            print(f"   Supported models: {len(service.get_supported_models())}")
            return True
        else:
            print("❌ Azure client not initialized")
            return False
            
    except Exception as e:
        print(f"❌ Azure connection error: {e}")
        return False


def check_directories():
    """Check that required directories exist."""
    print("\nChecking directories...")
    
    from backend.utils.config import settings
    
    dirs_to_check = [
        settings.upload_folder,
        settings.workpaper_output_folder,
        Path("logs"),
        Path("temp")
    ]
    
    all_exist = True
    for dir_path in dirs_to_check:
        if dir_path.exists():
            print(f"✅ {dir_path} exists")
        else:
            print(f"❌ {dir_path} does not exist")
            all_exist = False
    
    return all_exist


def main():
    """Run all tests."""
    print("🏥 CPA Copilot Health Check")
    print("=" * 50)
    
    results = {
        "Imports": test_imports(),
        "Azure Connection": test_azure_connection(),
        "Directories": check_directories()
    }
    
    print("\n" + "=" * 50)
    print("Summary:")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    if all(results.values()):
        print("\n🎉 All checks passed! The application is ready to run.")
        print("\nTo start the application:")
        print("  streamlit run frontend/streamlit/app.py")
    else:
        print("\n⚠️  Some checks failed. Please review the errors above.")
        print("\nCommon fixes:")
        print("  1. Make sure you have installed all dependencies: pip install -r requirements.txt")
        print("  2. Check that your .env file exists and has the correct API keys")
        print("  3. The application will create missing directories automatically")


if __name__ == "__main__":
    main()
