#!/usr/bin/env python3
"""
Test script for Task Status Migration

This script creates test data and validates the migration logic
without affecting the real database.
"""

import sys
import os
import tempfile
import sqlite3
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.app import create_app
from src.shared.database.db_import import db
from src.models import Task, TaskStatus, WorkType, Firm, Project, User
from migrate_task_status import TaskStatusMigrator


def create_test_database():
    """Create a temporary database with test data"""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    
    # Configure app to use test database
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['TESTING'] = True
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create test firm
        firm = Firm(
            name="Test CPA Firm",
            access_code="TEST2024",
            is_active=True
        )
        db.session.add(firm)
        db.session.flush()
        
        # Create test user
        user = User(
            name="Test User",
            role="Admin",
            firm_id=firm.id
        )
        db.session.add(user)
        db.session.flush()
        
        # Create test project
        project = Project(
            name="Test Project",
            firm_id=firm.id,
            client_id=1,  # Assume client exists
            status="Active"
        )
        db.session.add(project)
        db.session.flush()
        
        # Create test tasks with various legacy statuses
        test_statuses = [
            'Not Started',
            'In Progress', 
            'Needs Review',
            'Completed',
            'On Hold',
            'Cancelled',
            'Custom Status',  # This should trigger fallback logic
            'done',  # Lowercase variation
            'BLOCKED'  # Uppercase variation
        ]
        
        for i, status in enumerate(test_statuses):
            task = Task(
                title=f"Test Task {i+1}",
                description=f"Task with status: {status}",
                status=status,  # Legacy status
                status_id=None,  # No new status yet
                firm_id=firm.id,
                project_id=project.id,
                assignee_id=user.id,
                priority="Medium"
            )
            db.session.add(task)
        
        db.session.commit()
        
        print(f"✅ Created test database with {len(test_statuses)} tasks")
        print(f"Database path: {db_path}")
        
    return app, db_path


def run_migration_test():
    """Test the migration process"""
    print("🧪 TESTING TASK STATUS MIGRATION")
    print("=" * 50)
    
    # Create test database
    app, db_path = create_test_database()
    
    try:
        # Initialize migrator
        migrator = TaskStatusMigrator(app)
        
        # Test analysis
        print("\n📊 Testing Analysis...")
        analysis = migrator.analyze_current_state()
        assert analysis['total_tasks'] == 9, f"Expected 9 tasks, got {analysis['total_tasks']}"
        assert analysis['legacy_only'] == 9, f"Expected 9 legacy-only tasks, got {analysis['legacy_only']}"
        print("✅ Analysis test passed")
        
        # Test dry run
        print("\n🔍 Testing Dry Run...")
        created_count = migrator.create_default_work_types_and_statuses(dry_run=True)
        migrated_count, error_count = migrator.migrate_task_statuses(dry_run=True)
        assert created_count == 1, f"Expected to create 1 work type, got {created_count}"
        assert migrated_count == 9, f"Expected to migrate 9 tasks, got {migrated_count}"
        assert error_count == 0, f"Expected 0 errors, got {error_count}"
        print("✅ Dry run test passed")
        
        # Test actual migration
        print("\n⚡ Testing Actual Migration...")
        created_count = migrator.create_default_work_types_and_statuses(dry_run=False)
        migrated_count, error_count = migrator.migrate_task_statuses(dry_run=False)
        assert created_count == 1, f"Expected to create 1 work type, got {created_count}"
        assert migrated_count == 9, f"Expected to migrate 9 tasks, got {migrated_count}"
        print("✅ Migration execution test passed")
        
        # Test verification
        print("\n✅ Testing Verification...")
        verification_passed = migrator.verify_migration()
        assert verification_passed, "Migration verification failed"
        print("✅ Verification test passed")
        
        # Test specific mappings
        print("\n🔍 Testing Status Mappings...")
        with app.app_context():
            # Check that all tasks now have status_id
            tasks_without_status_id = Task.query.filter(Task.status_id.is_(None)).count()
            assert tasks_without_status_id == 0, f"Found {tasks_without_status_id} tasks without status_id"
            
            # Check specific mappings
            completed_task = Task.query.filter(Task.status == 'Completed').first()
            assert completed_task.task_status_ref.is_terminal, "Completed task should have terminal status"
            
            not_started_task = Task.query.filter(Task.status == 'Not Started').first()
            assert not_started_task.task_status_ref.is_default, "Not Started task should have default status"
            
            # Check fuzzy matching
            done_task = Task.query.filter(Task.status == 'done').first()
            assert done_task.task_status_ref.name == 'Completed', "Lowercase 'done' should map to 'Completed'"
            
        print("✅ Status mapping test passed")
        
        # Test rollback
        print("\n🔄 Testing Rollback...")
        rollback_count = migrator.rollback_migration(dry_run=False)
        assert rollback_count == 9, f"Expected to rollback 9 tasks, got {rollback_count}"
        
        with app.app_context():
            tasks_with_status_id = Task.query.filter(Task.status_id.isnot(None)).count()
            assert tasks_with_status_id == 0, f"Found {tasks_with_status_id} tasks still with status_id after rollback"
        
        print("✅ Rollback test passed")
        
        print("\n🎉 ALL TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up test database
        try:
            os.unlink(db_path)
            print(f"\n🧹 Cleaned up test database: {db_path}")
        except:
            pass


def test_edge_cases():
    """Test edge cases and error conditions"""
    print("\n🧪 TESTING EDGE CASES")
    print("=" * 30)
    
    app, db_path = create_test_database()
    
    try:
        with app.app_context():
            # Test task with NULL status
            null_task = Task(
                title="Task with NULL status",
                description="This task has no status",
                status=None,
                status_id=None,
                firm_id=1,
                project_id=1,
                assignee_id=1,
                priority="Low"
            )
            db.session.add(null_task)
            
            # Test task with empty string status
            empty_task = Task(
                title="Task with empty status",
                description="This task has empty status",
                status="",
                status_id=None,
                firm_id=1,
                project_id=1,
                assignee_id=1,
                priority="Low"
            )
            db.session.add(empty_task)
            
            db.session.commit()
            
            # Test migration with edge cases
            migrator = TaskStatusMigrator(app)
            migrator.create_default_work_types_and_statuses(dry_run=False)
            migrated_count, error_count = migrator.migrate_task_statuses(dry_run=False)
            
            print(f"Migrated {migrated_count} tasks with {error_count} errors")
            
            # Verify edge cases were handled
            null_task_after = Task.query.filter(Task.title == "Task with NULL status").first()
            empty_task_after = Task.query.filter(Task.title == "Task with empty status").first()
            
            # These should have been assigned default status
            assert null_task_after.status_id is not None, "NULL status task should get default status_id"
            assert empty_task_after.status_id is not None, "Empty status task should get default status_id"
            
        print("✅ Edge case tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Edge case test failed: {e}")
        return False
        
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


if __name__ == '__main__':
    print("🚀 STARTING MIGRATION TESTS")
    print("=" * 50)
    
    success = True
    
    # Run main migration test
    if not run_migration_test():
        success = False
    
    # Run edge case tests
    if not test_edge_cases():
        success = False
    
    if success:
        print("\n🎉 ALL MIGRATION TESTS PASSED!")
        print("The migration script is ready for production use.")
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("Review the errors before using the migration script.")
        sys.exit(1)