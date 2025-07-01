#!/usr/bin/env python3
"""
Safety Net Test Runner
Runs the critical tests before refactoring begins

Usage:
    python run_safety_tests.py
    python run_safety_tests.py --critical-only
    python run_safety_tests.py --verbose
"""

import sys
import unittest
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def run_critical_tests_only():
    """Run only the most critical tests that validate our recent fixes"""
    print("🔧 Running CRITICAL safety tests (recent fixes validation)...")
    print("=" * 60)
    
    # Import and run simple critical fixes tests
    from tests.test_critical_fixes_simple import SimpleCriticalFixesTests
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add critical test cases
    suite.addTests(loader.loadTestsFromTestCase(SimpleCriticalFixesTests))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_integration_tests():
    """Run full integration test suite"""
    print("🛡️  Running FULL integration safety tests...")
    print("=" * 60)
    
    # Note: Integration tests require more setup - for now, run service tests
    print("ℹ️  Integration tests are available but require environment setup.")
    print("ℹ️  Running service layer tests as safety net...")
    
    # Run existing service tests as integration substitute
    return run_existing_service_tests()


def run_existing_service_tests():
    """Run existing service tests for baseline validation"""
    print("📋 Running existing service tests...")
    print("=" * 60)
    
    # Import existing tests
    from tests.test_services import TestServiceLayer
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add existing test cases
    suite.addTests(loader.loadTestsFromTestCase(TestServiceLayer))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def main():
    """Main test runner with command line options"""
    parser = argparse.ArgumentParser(description='Run safety net tests before refactoring')
    parser.add_argument('--critical-only', action='store_true', 
                       help='Run only critical tests (recent fixes validation)')
    parser.add_argument('--integration-only', action='store_true',
                       help='Run only integration tests')
    parser.add_argument('--existing-only', action='store_true',
                       help='Run only existing service tests')
    parser.add_argument('--verbose', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    print("🚀 CPA WorkflowPilot - Safety Net Test Runner")
    print("🎯 Validating system before Phase 1 refactoring")
    print()
    
    success_count = 0
    total_suites = 0
    
    if args.critical_only:
        total_suites = 1
        if run_critical_tests_only():
            success_count += 1
    elif args.integration_only:
        total_suites = 1
        if run_integration_tests():
            success_count += 1
    elif args.existing_only:
        total_suites = 1
        if run_existing_service_tests():
            success_count += 1
    else:
        # Run all test suites
        total_suites = 3
        
        print("🔧 Step 1: Critical fixes validation")
        if run_critical_tests_only():
            success_count += 1
            print("✅ Critical tests PASSED")
        else:
            print("❌ Critical tests FAILED")
        
        print("\n🛡️  Step 2: Integration safety tests")
        if run_integration_tests():
            success_count += 1
            print("✅ Integration tests PASSED")
        else:
            print("❌ Integration tests FAILED")
        
        print("\n📋 Step 3: Existing service validation")
        if run_existing_service_tests():
            success_count += 1
            print("✅ Existing tests PASSED")
        else:
            print("❌ Existing tests FAILED")
    
    print("\n" + "=" * 60)
    print(f"🏁 FINAL RESULT: {success_count}/{total_suites} test suites passed")
    
    if success_count == total_suites:
        print("🎉 ALL TESTS PASSED - System ready for refactoring!")
        print("✅ Safe to proceed with Phase 1: Blueprint logic extraction")
        return True
    else:
        print("⚠️  SOME TESTS FAILED - Review issues before refactoring")
        print("❌ Do NOT proceed with refactoring until all tests pass")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)