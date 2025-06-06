#!/usr/bin/env python3

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Initialize Flask app with database
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.abspath("instance/workflow.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy()
db.init_app(app)

def migrate_database():
    """Add recurring task fields to Task table"""
    with app.app_context():
        try:
            print("Starting database migration for integrated recurring tasks...")
            
            # Add recurring task fields to Task table
            print("Adding recurring task fields to task table...")
            with db.engine.connect() as conn:
                # Add is_recurring field
                try:
                    conn.execute(text("ALTER TABLE task ADD COLUMN is_recurring BOOLEAN DEFAULT FALSE NOT NULL;"))
                    print("✓ Added is_recurring column")
                except Exception as e:
                    if "duplicate column name" not in str(e):
                        raise e
                    print("✓ is_recurring column already exists")
                
                # Add recurrence_rule field
                try:
                    conn.execute(text("ALTER TABLE task ADD COLUMN recurrence_rule TEXT;"))
                    print("✓ Added recurrence_rule column")
                except Exception as e:
                    if "duplicate column name" not in str(e):
                        raise e
                    print("✓ recurrence_rule column already exists")
                
                # Add recurrence_interval field
                try:
                    conn.execute(text("ALTER TABLE task ADD COLUMN recurrence_interval INTEGER DEFAULT 1;"))
                    print("✓ Added recurrence_interval column")
                except Exception as e:
                    if "duplicate column name" not in str(e):
                        raise e
                    print("✓ recurrence_interval column already exists")
                
                # Add next_due_date field
                try:
                    conn.execute(text("ALTER TABLE task ADD COLUMN next_due_date DATE;"))
                    print("✓ Added next_due_date column")
                except Exception as e:
                    if "duplicate column name" not in str(e):
                        raise e
                    print("✓ next_due_date column already exists")
                
                # Add last_completed field
                try:
                    conn.execute(text("ALTER TABLE task ADD COLUMN last_completed DATE;"))
                    print("✓ Added last_completed column")
                except Exception as e:
                    if "duplicate column name" not in str(e):
                        raise e
                    print("✓ last_completed column already exists")
                
                # Add master_task_id field
                try:
                    conn.execute(text("ALTER TABLE task ADD COLUMN master_task_id INTEGER REFERENCES task(id);"))
                    print("✓ Added master_task_id column")
                except Exception as e:
                    if "duplicate column name" not in str(e):
                        raise e
                    print("✓ master_task_id column already exists")
                
                conn.commit()
            
            print("\n🎉 Database migration completed successfully!")
            print("\nNew features available:")
            print("• Recurring tasks integrated into regular task creation")
            print("• Tasks can automatically create new instances on completion")
            print("• Support for daily, weekly, monthly, and yearly recurrence")
            print("• Master task tracking for recurring task instances")
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            return False
    
    return True

if __name__ == '__main__':
    if migrate_database():
        print("\n✅ Migration completed successfully!")
        print("Recurring tasks are now integrated with regular task creation.")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)