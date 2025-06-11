#!/usr/bin/env python3
"""
Migration to add task_dependency_mode flag to templates and set all existing templates and projects as sequential
"""

import sqlite3
from datetime import datetime

def migrate_sequential_flag():
    """Add task_dependency_mode to templates and update existing data"""
    
    # Connect to database
    conn = sqlite3.connect('instance/workflow.db')
    cursor = conn.cursor()
    
    try:
        print("Starting migration for sequential workflow flags...")
        
        # 1. Add task_dependency_mode column to template table if it doesn't exist
        try:
            cursor.execute("ALTER TABLE template ADD COLUMN task_dependency_mode BOOLEAN DEFAULT 1")
            print("✅ Added task_dependency_mode column to template table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️  task_dependency_mode column already exists in template table")
            else:
                raise e
        
        # 2. Set all existing templates to sequential (task_dependency_mode = True)
        cursor.execute("UPDATE template SET task_dependency_mode = 1 WHERE task_dependency_mode IS NULL")
        affected_templates = cursor.rowcount
        print(f"✅ Updated {affected_templates} templates to be sequential")
        
        # 3. Set all existing projects to sequential (task_dependency_mode = True)
        cursor.execute("UPDATE project SET task_dependency_mode = 1 WHERE task_dependency_mode IS NULL OR task_dependency_mode = 0")
        affected_projects = cursor.rowcount
        print(f"✅ Updated {affected_projects} projects to be sequential")
        
        # 4. Verify the changes
        cursor.execute("SELECT COUNT(*) FROM template WHERE task_dependency_mode = 1")
        sequential_templates = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM project WHERE task_dependency_mode = 1")
        sequential_projects = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM template")
        total_templates = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM project")
        total_projects = cursor.fetchone()[0]
        
        print(f"\n📊 Migration Results:")
        print(f"   Templates: {sequential_templates}/{total_templates} are sequential")
        print(f"   Projects: {sequential_projects}/{total_projects} are sequential")
        
        # Commit the changes
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_sequential_flag()