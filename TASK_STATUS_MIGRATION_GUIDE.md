# Task Status Migration Guide

This guide walks you through migrating from the legacy string-based task status system to the new TaskStatus foreign key system, eliminating the dual source of truth identified in the forensic analysis.

## 🚨 CRITICAL: Backup Your Database First!

```bash
# For SQLite (default)
cp instance/workflow_management.db instance/workflow_management.db.backup

# For PostgreSQL
pg_dump your_database > backup_$(date +%Y%m%d_%H%M%S).sql

# For MySQL
mysqldump your_database > backup_$(date +%Y%m%d_%H%M%S).sql
```

## Migration Overview

The migration process consists of 4 phases:

1. **Analysis**: Understand current state and identify issues
2. **Preparation**: Create default work types and task statuses
3. **Data Migration**: Map legacy status strings to TaskStatus foreign keys
4. **Schema Cleanup**: Remove the legacy status column

## Phase 1: Analysis

First, analyze your current database state:

```bash
python migrate_task_status.py --analyze-only
```

This will show you:
- How many tasks use legacy vs new status system
- What legacy status values exist
- Which firms need default work types/statuses

## Phase 2: Dry Run

Preview all changes without applying them:

```bash
python migrate_task_status.py --dry-run
```

This will show you exactly what the migration will do:
- Which work types and statuses will be created
- How each task's status will be mapped
- Any potential issues or conflicts

## Phase 3: Execute Migration

⚠️ **Only proceed if the dry run looks correct!**

```bash
python migrate_task_status.py --execute
```

This will:
1. Create default work types for firms that don't have them
2. Create task statuses for all legacy status values
3. Populate `status_id` for all tasks based on their legacy `status`
4. Verify the migration was successful

## Phase 4: Schema Cleanup (Optional)

After verifying the migration worked correctly, you can remove the legacy status column:

```bash
# Initialize Flask-Migrate if not already done
python init_migrations.py

# Create and run the schema migration
flask db migrate -m "Remove legacy task status field"
flask db upgrade
```

## Status Mapping

The migration maps legacy status strings to new TaskStatus records:

| Legacy Status | New Status Properties |
|---------------|----------------------|
| Not Started   | Default: ✅, Terminal: ❌, Color: Gray |
| In Progress   | Default: ❌, Terminal: ❌, Color: Blue |
| Needs Review  | Default: ❌, Terminal: ❌, Color: Orange |
| Review        | Default: ❌, Terminal: ❌, Color: Orange |
| Completed     | Default: ❌, Terminal: ✅, Color: Green |
| Done          | Default: ❌, Terminal: ✅, Color: Green |
| Cancelled     | Default: ❌, Terminal: ✅, Color: Red |
| On Hold       | Default: ❌, Terminal: ❌, Color: Orange |
| Blocked       | Default: ❌, Terminal: ❌, Color: Red |

## Troubleshooting

### Issue: Tasks without status_id after migration

```bash
# Check for tasks that failed to migrate
python migrate_task_status.py --analyze-only
```

Look for tasks with "legacy status only". These need manual attention.

### Issue: Unrecognized legacy status values

The migration will:
1. Try exact name matching first
2. Try fuzzy matching for common variations
3. Fall back to the default status for the firm
4. Log warnings for any unrecognized values

### Issue: Migration verification fails

```bash
# Check the migration log for specific errors
# Fix any data inconsistencies manually
# Re-run verification
python migrate_task_status.py --analyze-only
```

### Emergency Rollback

If something goes wrong, you can rollback to the legacy system:

```bash
# Clear all status_id values (emergency only)
python migrate_task_status.py --rollback --execute

# Restore from backup if needed
cp instance/workflow_management.db.backup instance/workflow_management.db
```

## Post-Migration Verification

After migration, verify everything works:

1. **Check task status display**: Visit task lists and project views
2. **Test status changes**: Try updating task statuses
3. **Verify completion logic**: Check that completed tasks are properly identified
4. **Test filtering**: Use status filters in task views

## Code Changes Required

After successful migration, update your code:

### Before Migration (Dual System)
```python
# This worked with both systems
task.current_status  # Property that checks both fields
task.is_completed    # Property that checks both fields
```

### After Migration (New System Only)
```python
# These will work after removing legacy field
task.task_status_ref.name      # Direct access to TaskStatus
task.task_status_ref.is_terminal  # Check if completed
task.status_id                 # Foreign key to TaskStatus
```

## Benefits After Migration

✅ **Single Source of Truth**: No more confusion about task status  
✅ **Customizable Statuses**: Each firm can define their own workflow  
✅ **Rich Status Properties**: Colors, positions, terminal states  
✅ **Better Performance**: Foreign key lookups vs string comparisons  
✅ **Data Integrity**: Referential integrity constraints  
✅ **Workflow Support**: Kanban boards with custom columns  

## Migration Checklist

- [ ] Database backup created
- [ ] Analysis completed (`--analyze-only`)
- [ ] Dry run successful (`--dry-run`)
- [ ] Migration executed (`--execute`)
- [ ] Verification passed
- [ ] Application tested with new system
- [ ] Legacy status column removed (optional)
- [ ] Code updated to use new system exclusively

## Support

If you encounter issues during migration:

1. Check the migration log output for specific error messages
2. Verify your database backup is complete
3. Run the analysis command to understand current state
4. Consider running a dry run on a copy of your database first

The migration script is designed to be safe and reversible, but always test on a backup first!