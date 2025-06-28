#!/usr/bin/env python3
"""
Quick Page Load Test Runner for CPA WorkflowPilot
Runs basic page load tests to catch runtime errors quickly.
"""

import sys
import os
import pytest
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def run_page_load_tests():
    """Run page load tests with detailed output"""
    print("🔍 RUNNING PAGE LOAD TESTS")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Project Root: {project_root}")
    print()
    
    # Test configuration
    test_file = os.path.join(project_root, 'tests', 'integration', 'test_page_loads.py')
    
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False
    
    # Run pytest with specific configuration
    pytest_args = [
        test_file,
        '-v',                    # Verbose output
        '--tb=short',           # Short traceback format
        '--disable-warnings',   # Reduce noise
        '-x',                   # Stop on first failure
        '--color=yes'           # Colored output
    ]
    
    print("🚀 Starting page load tests...")
    print(f"Command: pytest {' '.join(pytest_args[1:])}")
    print()
    
    try:
        # Run the tests
        exit_code = pytest.main(pytest_args)
        
        print()
        print("=" * 60)
        
        if exit_code == 0:
            print("✅ ALL PAGE LOAD TESTS PASSED!")
            print("   - No runtime errors detected")
            print("   - All major pages load successfully") 
            print("   - Architectural refactoring successful")
            return True
        else:
            print("❌ SOME PAGE LOAD TESTS FAILED")
            print("   - Check output above for specific errors")
            print("   - Fix issues and re-run tests")
            return False
            
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def run_quick_import_test():
    """Quick test of critical imports"""
    print("🔍 QUICK IMPORT TEST")
    print("=" * 30)
    
    critical_imports = [
        ('Flask App', 'app'),
        ('User Model', 'models.auth'),
        ('Dashboard Service', 'services.dashboard_aggregator_service'),
        ('AI Service', 'services.ai_service'),
        ('Event Registry', 'events.registry'),
    ]
    
    all_passed = True
    
    for name, module_path in critical_imports:
        try:
            __import__(module_path)
            print(f"✅ {name}: OK")
        except Exception as e:
            print(f"❌ {name}: FAILED - {e}")
            all_passed = False
    
    print()
    return all_passed

if __name__ == '__main__':
    """Main execution"""
    print("CPA WORKFLOWPILOT - PAGE LOAD TESTING")
    print("=" * 60)
    print()
    
    # Step 1: Quick import test
    import_success = run_quick_import_test()
    
    if not import_success:
        print("❌ Critical import failures detected. Fix imports before running page tests.")
        sys.exit(1)
    
    print("✅ All critical imports successful")
    print()
    
    # Step 2: Full page load tests
    test_success = run_page_load_tests()
    
    if test_success:
        print()
        print("🎉 COMPREHENSIVE PAGE LOAD TESTING COMPLETE")
        print("   Your architectural refactoring is working correctly!")
        sys.exit(0)
    else:
        print()
        print("⚠️  Some page load issues detected.")
        print("   Check the test output above for specific problems.")
        sys.exit(1)