#!/usr/bin/env python3

"""
Migration script to add task_dependency_mode flag to Project table
This flag determines if tasks in a project must be completed sequentially
"""

import sqlite3
import sys
import os

def migrate_project_table():
    db_path = 'instance/workflow.db'
    
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current schema
        cursor.execute('PRAGMA table_info(project)')
        columns = cursor.fetchall()
        existing_columns = [col[1] for col in columns]
        
        print(f"Current project table columns: {len(existing_columns)} columns")
        
        # Add missing column
        if 'task_dependency_mode' not in existing_columns:
            print("Adding 'task_dependency_mode' column...")
            cursor.execute('ALTER TABLE project ADD COLUMN task_dependency_mode BOOLEAN DEFAULT FALSE')
            print("Successfully added task_dependency_mode column")
        else:
            print("task_dependency_mode column already exists")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error migrating database: {e}")
        return False

if __name__ == '__main__':
    print("Migrating project table to add task dependency mode...")
    success = migrate_project_table()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
        sys.exit(1)