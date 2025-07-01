"""
Remove legacy status field from Task model

This migration removes the legacy 'status' column from the Task table
after all tasks have been migrated to use the new status_id system.

IMPORTANT: Only run this migration AFTER successfully running the 
task status migration script (migrate_task_status.py --execute)

Revision ID: remove_legacy_status
Revises: initial_migration
Create Date: 2024-06-30 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers
revision = 'remove_legacy_status'
down_revision = 'initial_migration'
branch_labels = None
depends_on = None


def upgrade():
    """Remove the legacy status column from Task table"""
    
    # First, verify that all tasks have status_id populated
    connection = op.get_bind()
    
    # Check for tasks without status_id
    result = connection.execute(text(
        "SELECT COUNT(*) FROM task WHERE status_id IS NULL"
    ))
    tasks_without_status_id = result.scalar()
    
    if tasks_without_status_id > 0:
        raise Exception(
            f"Cannot remove legacy status field: {tasks_without_status_id} tasks "
            f"still have NULL status_id. Run the migration script first: "
            f"python migrate_task_status.py --execute"
        )
    
    print(f"✅ All tasks have status_id populated. Proceeding with migration.")
    
    # Make status_id NOT NULL since it's now the primary status field
    op.alter_column('task', 'status_id', nullable=False)
    print("✅ Made status_id column NOT NULL")
    
    # Remove the legacy status column
    op.drop_column('task', 'status')
    print("✅ Removed legacy status column")
    
    # Update the current_status property logic in the application code
    # (This is handled in the model code, not in the migration)
    
    print("🎉 Legacy status field migration completed successfully!")
    print("📝 Note: Update your application code to remove references to task.status")


def downgrade():
    """Restore the legacy status column (emergency rollback)"""
    
    print("⚠️  EMERGENCY ROLLBACK: Restoring legacy status column")
    
    # Add back the legacy status column
    op.add_column('task', sa.Column('status', sa.String(20), nullable=True, default='Not Started'))
    print("✅ Added back legacy status column")
    
    # Populate legacy status from TaskStatus names
    connection = op.get_bind()
    
    # Update legacy status based on current TaskStatus
    connection.execute(text("""
        UPDATE task 
        SET status = (
            SELECT task_status.name 
            FROM task_status 
            WHERE task_status.id = task.status_id
        )
        WHERE status_id IS NOT NULL
    """))
    
    # Set default for any remaining NULL values
    connection.execute(text(
        "UPDATE task SET status = 'Not Started' WHERE status IS NULL"
    ))
    
    # Make status NOT NULL
    op.alter_column('task', 'status', nullable=False)
    print("✅ Populated legacy status from TaskStatus names")
    
    # Make status_id nullable again
    op.alter_column('task', 'status_id', nullable=True)
    print("✅ Made status_id nullable again")
    
    print("🔄 Rollback completed. Legacy status system restored.")
    print("⚠️  Remember to update your application code to use task.status again")


def validate_migration():
    """Validate that the migration can be safely applied"""
    connection = op.get_bind()
    
    # Check that TaskStatus table exists and has data
    try:
        result = connection.execute(text("SELECT COUNT(*) FROM task_status"))
        status_count = result.scalar()
        if status_count == 0:
            raise Exception("TaskStatus table is empty. Create task statuses first.")
    except Exception as e:
        raise Exception(f"TaskStatus table validation failed: {e}")
    
    # Check that all tasks have valid status_id references
    result = connection.execute(text("""
        SELECT COUNT(*) FROM task 
        LEFT JOIN task_status ON task.status_id = task_status.id 
        WHERE task.status_id IS NOT NULL AND task_status.id IS NULL
    """))
    invalid_references = result.scalar()
    
    if invalid_references > 0:
        raise Exception(f"{invalid_references} tasks have invalid status_id references")
    
    return True


if __name__ == '__main__':
    print("This is a migration file. Use Flask-Migrate to run it:")
    print("flask db upgrade")