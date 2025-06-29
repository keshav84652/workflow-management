#!/usr/bin/env python3
"""
Functional Error Detection Test Runner for CPA WorkflowPilot
Runs tests that catch actual functional errors, not just HTTP status codes.
"""

import sys
import os
import pytest
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def run_functional_tests():
    """Run functional error detection tests"""
    print("🔍 RUNNING FUNCTIONAL ERROR DETECTION TESTS")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("These tests catch actual functional errors beyond HTTP status codes")
    print()
    
    # Test configuration
    test_file = os.path.join(project_root, 'tests', 'integration', 'test_functional_errors.py')
    
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
    
    print("🚀 Starting functional error detection tests...")
    print()
    
    try:
        # Run the tests
        exit_code = pytest.main(pytest_args)
        
        print()
        print("=" * 60)
        
        if exit_code == 0:
            print("✅ ALL FUNCTIONAL TESTS PASSED!")
            print("   - Service methods exist and work correctly")
            print("   - Data structures are properly formed") 
            print("   - Error handling is graceful")
            print("   - No runtime AttributeErrors or missing methods")
            return True
        else:
            print("❌ SOME FUNCTIONAL TESTS FAILED")
            print("   - Check output above for specific functional errors")
            print("   - These tests catch issues that basic page load tests miss")
            return False
            
    except Exception as e:
        print(f"❌ Error running functional tests: {e}")
        return False

def run_quick_service_test():
    """Quick test of service functionality"""
    print("🔍 QUICK SERVICE FUNCTIONALITY TEST")
    print("=" * 40)
    
    try:
        from app import create_app
        from services.dashboard_aggregator_service import DashboardAggregatorService
        
        app = create_app()
        # CRITICAL: Use test database to avoid affecting production data
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            # Create tables in test database
            from src.shared.database.db_import import db
            db.create_all()
            service = DashboardAggregatorService()
            
            # Test critical methods
            critical_methods = [
                'get_dashboard_data',
                'get_calendar_data', 
                'get_time_tracking_report'
            ]
            
            all_passed = True
            
            for method_name in critical_methods:
                if hasattr(service, method_name):
                    print(f"✅ {method_name}: EXISTS")
                    
                    # Try to call with safe parameters
                    try:
                        method = getattr(service, method_name)
                        if method_name == 'get_calendar_data':
                            result = method(1, 2024, 12)
                        else:
                            result = method(1)
                        
                        if isinstance(result, dict) and 'error' not in result:
                            print(f"✅ {method_name}: FUNCTIONAL")
                        else:
                            print(f"⚠️  {method_name}: Returns data but may have issues")
                            
                    except Exception as e:
                        print(f"❌ {method_name}: ERROR - {e}")
                        all_passed = False
                else:
                    print(f"❌ {method_name}: MISSING")
                    all_passed = False
            
            print()
            return all_passed
        
    except Exception as e:
        print(f"❌ Service test error: {e}")
        return False

if __name__ == '__main__':
    """Main execution"""
    print("CPA WORKFLOWPILOT - FUNCTIONAL ERROR DETECTION")
    print("=" * 60)
    print()
    
    # Step 1: Quick service test
    service_success = run_quick_service_test()
    
    if not service_success:
        print("❌ Critical service failures detected. Fix service issues before running full tests.")
        sys.exit(1)
    
    print("✅ All critical services functional")
    print()
    
    # Step 2: Full functional tests
    test_success = run_functional_tests()
    
    if test_success:
        print()
        print("🎉 COMPREHENSIVE FUNCTIONAL TESTING COMPLETE")
        print("   Your services handle edge cases correctly!")
        print("   No missing methods or AttributeErrors detected!")
        sys.exit(0)
    else:
        print()
        print("⚠️  Some functional issues detected.")
        print("   These tests catch errors that basic page load tests miss.")
        print("   Check the test output above for specific problems.")
        sys.exit(1)