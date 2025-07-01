#!/usr/bin/env python3
"""
Task Status Migration Script for CPA WorkflowPilot

This script migrates tasks from the legacy string-based status system 
to the new TaskStatus foreign key system, eliminating the dual source of truth.

CRITICAL: This script modifies the database schema and data. 
Always backup your database before running this migration!

Usage:
    python migrate_task_status.py --dry-run    # Preview changes without applying
    python migrate_task_status.py --execute    # Apply the migration
    python migrate_task_status.py --rollback   # Rollback to legacy system (emergency)
"""

import sys
import os
import argparse
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Flask app and models
from src.app import create_app
from src.shared.database.db_import import db
from src.models import Task, TaskStatus, WorkType, Firm, Project


class TaskStatusMigrator:
    """Handles the migration from legacy status strings to TaskStatus foreign keys"""
    
    def __init__(self, app):
        self.app = app
        self.migration_log = []
        
        # Legacy status to new status mapping
        self.legacy_status_mapping = {
            'Not Started': {'is_default': True, 'is_terminal': False, 'color': '#6b7280'},
            'In Progress': {'is_default': False, 'is_terminal': False, 'color': '#3b82f6'},
            'Needs Review': {'is_default': False, 'is_terminal': False, 'color': '#f59e0b'},
            'Review': {'is_default': False, 'is_terminal': False, 'color': '#f59e0b'},
            'Completed': {'is_default': False, 'is_terminal': True, 'color': '#10b981'},
            'Done': {'is_default': False, 'is_terminal': True, 'color': '#10b981'},
            'Cancelled': {'is_default': False, 'is_terminal': True, 'color': '#ef4444'},
            'On Hold': {'is_default': False, 'is_terminal': False, 'color': '#f97316'},
            'Blocked': {'is_default': False, 'is_terminal': False, 'color': '#dc2626'},
        }
    
    def log(self, message, level='INFO'):
        """Log migration steps"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {level}: {message}"
        print(log_entry)
        self.migration_log.append(log_entry)
    
    def analyze_current_state(self):
        """Analyze the current state of tasks and status usage"""
        with self.app.app_context():
            self.log("=== ANALYZING CURRENT STATE ===")
            
            # Count tasks by status type
            total_tasks = Task.query.count()
            tasks_with_legacy_only = Task.query.filter(
                Task.status_id.is_(None),
                Task.status.isnot(None)
            ).count()
            tasks_with_new_only = Task.query.filter(
                Task.status_id.isnot(None),
                Task.status.is_(None)
            ).count()
            tasks_with_both = Task.query.filter(
                Task.status_id.isnot(None),
                Task.status.isnot(None)
            ).count()
            
            self.log(f"Total tasks: {total_tasks}")
            self.log(f"Tasks with legacy status only: {tasks_with_legacy_only}")
            self.log(f"Tasks with new status only: {tasks_with_new_only}")
            self.log(f"Tasks with both status types: {tasks_with_both}")
            
            # Analyze legacy status values
            legacy_statuses = db.session.query(Task.status, db.func.count(Task.id)).group_by(Task.status).all()
            self.log("\nLegacy status distribution:")
            for status, count in legacy_statuses:
                self.log(f"  '{status}': {count} tasks")
            
            # Analyze firms and work types
            firms = Firm.query.all()
            self.log(f"\nFirms: {len(firms)}")
            for firm in firms:
                work_types = WorkType.query.filter_by(firm_id=firm.id).count()
                task_statuses = TaskStatus.query.filter_by(firm_id=firm.id).count()
                self.log(f"  {firm.name}: {work_types} work types, {task_statuses} task statuses")
            
            return {
                'total_tasks': total_tasks,
                'legacy_only': tasks_with_legacy_only,
                'new_only': tasks_with_new_only,
                'both': tasks_with_both,
                'legacy_statuses': dict(legacy_statuses)
            }
    
    def create_default_work_types_and_statuses(self, dry_run=True):
        """Create default work types and task statuses for firms that don't have them"""
        with self.app.app_context():
            self.log("=== CREATING DEFAULT WORK TYPES AND STATUSES ===")
            
            firms = Firm.query.all()
            changes_made = 0
            
            for firm in firms:
                # Check if firm has any work types
                existing_work_types = WorkType.query.filter_by(firm_id=firm.id).count()
                
                if existing_work_types == 0:
                    self.log(f"Creating default work type for firm: {firm.name}")
                    
                    if not dry_run:
                        # Create default work type
                        default_work_type = WorkType(
                            firm_id=firm.id,
                            name="General Tasks",
                            description="Default work type for task migration",
                            color="#3b82f6",
                            is_active=True,
                            position=0
                        )
                        db.session.add(default_work_type)
                        db.session.flush()  # Get the ID
                        
                        # Create default task statuses
                        position = 1
                        for status_name, config in self.legacy_status_mapping.items():
                            task_status = TaskStatus(
                                firm_id=firm.id,
                                work_type_id=default_work_type.id,
                                name=status_name,
                                color=config['color'],
                                position=position,
                                is_default=config['is_default'],
                                is_terminal=config['is_terminal']
                            )
                            db.session.add(task_status)
                            position += 1
                        
                        changes_made += 1
                        self.log(f"  Created work type and {len(self.legacy_status_mapping)} statuses")
                    else:
                        self.log(f"  [DRY RUN] Would create work type and {len(self.legacy_status_mapping)} statuses")
                        changes_made += 1
                else:
                    # Check if firm has task statuses
                    existing_statuses = TaskStatus.query.filter_by(firm_id=firm.id).count()
                    if existing_statuses == 0:
                        self.log(f"Firm {firm.name} has work types but no task statuses - creating defaults")
                        
                        if not dry_run:
                            # Use the first work type for default statuses
                            first_work_type = WorkType.query.filter_by(firm_id=firm.id).first()
                            
                            position = 1
                            for status_name, config in self.legacy_status_mapping.items():
                                task_status = TaskStatus(
                                    firm_id=firm.id,
                                    work_type_id=first_work_type.id,
                                    name=status_name,
                                    color=config['color'],
                                    position=position,
                                    is_default=config['is_default'],
                                    is_terminal=config['is_terminal']
                                )
                                db.session.add(task_status)
                                position += 1
                            
                            changes_made += 1
                            self.log(f"  Created {len(self.legacy_status_mapping)} statuses for existing work type")
                        else:
                            self.log(f"  [DRY RUN] Would create {len(self.legacy_status_mapping)} statuses")
                            changes_made += 1
            
            if not dry_run and changes_made > 0:
                db.session.commit()
                self.log(f"Committed changes for {changes_made} firms")
            
            return changes_made
    
    def migrate_task_statuses(self, dry_run=True):
        """Migrate tasks from legacy status strings to TaskStatus foreign keys"""
        with self.app.app_context():
            self.log("=== MIGRATING TASK STATUSES ===")
            
            # Get all tasks that need migration (have legacy status but no status_id)
            tasks_to_migrate = Task.query.filter(
                Task.status_id.is_(None),
                Task.status.isnot(None)
            ).all()
            
            self.log(f"Found {len(tasks_to_migrate)} tasks to migrate")
            
            migrated_count = 0
            error_count = 0
            
            for task in tasks_to_migrate:
                try:
                    # Find appropriate TaskStatus for this task
                    target_status = self._find_matching_status(task)
                    
                    if target_status:
                        if not dry_run:
                            task.status_id = target_status.id
                            # Keep the legacy status for now as backup
                            migrated_count += 1
                        else:
                            self.log(f"  [DRY RUN] Task {task.id} '{task.title}': '{task.status}' -> TaskStatus {target_status.id} '{target_status.name}'")
                            migrated_count += 1
                    else:
                        self.log(f"  ERROR: Could not find matching status for task {task.id} with status '{task.status}'", 'ERROR')
                        error_count += 1
                
                except Exception as e:
                    self.log(f"  ERROR: Failed to migrate task {task.id}: {e}", 'ERROR')
                    error_count += 1
            
            if not dry_run and migrated_count > 0:
                db.session.commit()
                self.log(f"Successfully migrated {migrated_count} tasks")
            
            if error_count > 0:
                self.log(f"Encountered {error_count} errors during migration", 'WARNING')
            
            return migrated_count, error_count
    
    def _find_matching_status(self, task):
        """Find the best matching TaskStatus for a task's legacy status"""
        # Get the firm for this task
        firm_id = task.firm_id
        
        # Try to find exact match first
        exact_match = TaskStatus.query.filter_by(
            firm_id=firm_id,
            name=task.status
        ).first()
        
        if exact_match:
            return exact_match
        
        # Try fuzzy matching for common variations
        status_variations = {
            'Not Started': ['not started', 'new', 'todo', 'pending'],
            'In Progress': ['in progress', 'working', 'active', 'started'],
            'Needs Review': ['needs review', 'review', 'pending review'],
            'Completed': ['completed', 'done', 'finished', 'complete'],
            'Cancelled': ['cancelled', 'canceled', 'cancelled'],
            'On Hold': ['on hold', 'hold', 'paused', 'waiting'],
            'Blocked': ['blocked', 'stuck', 'blocked']
        }
        
        task_status_lower = task.status.lower().strip()
        
        for canonical_status, variations in status_variations.items():
            if task_status_lower in variations or task_status_lower == canonical_status.lower():
                match = TaskStatus.query.filter_by(
                    firm_id=firm_id,
                    name=canonical_status
                ).first()
                if match:
                    return match
        
        # Fallback: use default status for the firm
        default_status = TaskStatus.query.filter_by(
            firm_id=firm_id,
            is_default=True
        ).first()
        
        if default_status:
            self.log(f"  Using default status for task {task.id} with unrecognized status '{task.status}'", 'WARNING')
            return default_status
        
        # Last resort: use any status from the firm
        any_status = TaskStatus.query.filter_by(firm_id=firm_id).first()
        if any_status:
            self.log(f"  Using first available status for task {task.id}", 'WARNING')
            return any_status
        
        return None
    
    def verify_migration(self):
        """Verify that the migration was successful"""
        with self.app.app_context():
            self.log("=== VERIFYING MIGRATION ===")
            
            # Check for tasks without status_id
            tasks_without_status_id = Task.query.filter(Task.status_id.is_(None)).count()
            
            # Check for orphaned status_id references
            tasks_with_invalid_status = db.session.query(Task).outerjoin(TaskStatus).filter(
                Task.status_id.isnot(None),
                TaskStatus.id.is_(None)
            ).count()
            
            # Check consistency between legacy and new status
            inconsistent_tasks = []
            tasks_with_both = Task.query.filter(
                Task.status_id.isnot(None),
                Task.status.isnot(None)
            ).all()
            
            for task in tasks_with_both:
                if task.task_status_ref:
                    legacy_completed = task.status == 'Completed'
                    new_completed = task.task_status_ref.is_terminal
                    if legacy_completed != new_completed:
                        inconsistent_tasks.append(task)
            
            self.log(f"Tasks without status_id: {tasks_without_status_id}")
            self.log(f"Tasks with invalid status_id: {tasks_with_invalid_status}")
            self.log(f"Tasks with inconsistent completion status: {len(inconsistent_tasks)}")
            
            if tasks_without_status_id == 0 and tasks_with_invalid_status == 0 and len(inconsistent_tasks) == 0:
                self.log("✅ Migration verification PASSED", 'SUCCESS')
                return True
            else:
                self.log("❌ Migration verification FAILED", 'ERROR')
                return False
    
    def remove_legacy_status_field(self, dry_run=True):
        """Remove the legacy status field after successful migration"""
        with self.app.app_context():
            self.log("=== REMOVING LEGACY STATUS FIELD ===")
            
            if dry_run:
                self.log("[DRY RUN] Would remove the legacy 'status' column from Task table")
                return True
            
            try:
                # This requires an actual database migration
                self.log("To remove the legacy status field, you need to:")
                self.log("1. Create a Flask-Migrate migration file")
                self.log("2. Remove the 'status' column from the Task model")
                self.log("3. Run 'flask db migrate' to generate the migration")
                self.log("4. Run 'flask db upgrade' to apply the migration")
                self.log("")
                self.log("This step is not automated to prevent accidental data loss.")
                return True
            except Exception as e:
                self.log(f"Error in legacy field removal: {e}", 'ERROR')
                return False
    
    def rollback_migration(self, dry_run=True):
        """Emergency rollback: clear status_id fields to revert to legacy system"""
        with self.app.app_context():
            self.log("=== EMERGENCY ROLLBACK ===")
            
            tasks_with_status_id = Task.query.filter(Task.status_id.isnot(None)).count()
            self.log(f"Found {tasks_with_status_id} tasks with status_id to rollback")
            
            if not dry_run:
                # Clear all status_id fields
                Task.query.update({Task.status_id: None})
                db.session.commit()
                self.log(f"Rolled back {tasks_with_status_id} tasks to legacy status system")
            else:
                self.log(f"[DRY RUN] Would rollback {tasks_with_status_id} tasks")
            
            return tasks_with_status_id
    
    def run_full_migration(self, dry_run=True):
        """Run the complete migration process"""
        self.log("🚀 STARTING TASK STATUS MIGRATION")
        self.log(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
        self.log("=" * 50)
        
        try:
            # Step 1: Analyze current state
            analysis = self.analyze_current_state()
            
            # Step 2: Create default work types and statuses if needed
            created_count = self.create_default_work_types_and_statuses(dry_run)
            
            # Step 3: Migrate task statuses
            migrated_count, error_count = self.migrate_task_statuses(dry_run)
            
            # Step 4: Verify migration (only if not dry run)
            if not dry_run:
                verification_passed = self.verify_migration()
                if not verification_passed:
                    self.log("Migration verification failed! Consider rollback.", 'ERROR')
                    return False
            
            # Step 5: Instructions for removing legacy field
            if not dry_run and migrated_count > 0:
                self.remove_legacy_status_field(dry_run=True)  # Always dry run for this step
            
            self.log("=" * 50)
            self.log("✅ MIGRATION COMPLETED SUCCESSFULLY")
            self.log(f"Summary: Created {created_count} work types, migrated {migrated_count} tasks")
            
            return True
            
        except Exception as e:
            self.log(f"❌ MIGRATION FAILED: {e}", 'ERROR')
            return False


def main():
    parser = argparse.ArgumentParser(description='Migrate task status from legacy to new system')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying them')
    parser.add_argument('--execute', action='store_true', help='Execute the migration')
    parser.add_argument('--rollback', action='store_true', help='Rollback to legacy system (emergency)')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze current state')
    
    args = parser.parse_args()
    
    if not any([args.dry_run, args.execute, args.rollback, args.analyze_only]):
        print("Error: You must specify one of --dry-run, --execute, --rollback, or --analyze-only")
        sys.exit(1)
    
    if args.execute and args.dry_run:
        print("Error: Cannot specify both --execute and --dry-run")
        sys.exit(1)
    
    # Create Flask app
    app = create_app()
    migrator = TaskStatusMigrator(app)
    
    try:
        if args.analyze_only:
            migrator.analyze_current_state()
        elif args.rollback:
            migrator.rollback_migration(dry_run=args.dry_run)
        else:
            migrator.run_full_migration(dry_run=args.dry_run)
            
    except KeyboardInterrupt:
        print("\n\nMigration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()