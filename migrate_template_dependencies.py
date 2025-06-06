#!/usr/bin/env python3
"""
Database migration script to add template task status mapping and dependencies
"""
import os
import sys
from sqlalchemy import text

# Add the current directory to path so we can import our models
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, TemplateTask, Task
from app import app

def migrate_database():
    """Add new columns for template task status mapping and dependencies"""
    with app.app_context():
        try:
            # Add default_status_id column to template_task table
            with db.engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE template_task 
                    ADD COLUMN default_status_id INTEGER REFERENCES task_status(id);
                """))
                conn.commit()
            print("✅ Added default_status_id column to template_task")
            
            # Add dependencies column to template_task table  
            with db.engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE template_task 
                    ADD COLUMN dependencies VARCHAR(500);
                """))
                conn.commit()
            print("✅ Added dependencies column to template_task")
            
            # Add dependencies column to task table
            with db.engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE task 
                    ADD COLUMN dependencies VARCHAR(500);
                """))
                conn.commit()
            print("✅ Added dependencies column to task")
            
            print("🎉 Database migration completed successfully!")
            
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("ℹ️  Columns already exist, skipping migration")
            else:
                print(f"❌ Migration error: {e}")
                raise

if __name__ == '__main__':
    migrate_database()