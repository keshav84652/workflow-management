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
    """Add subtask functionality to the database"""
    with app.app_context():
        try:
            print("Starting database migration for subtasks...")
            
            # Add parent_task_id column to Task table for subtask relationships
            print("Adding parent_task_id column to task table...")
            with db.engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE task 
                    ADD COLUMN parent_task_id INTEGER REFERENCES task(id) ON DELETE CASCADE;
                """))
                conn.commit()
                print("✓ parent_task_id column added successfully")
            
            # Add subtask display order column
            print("Adding subtask_order column...")
            with db.engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE task 
                    ADD COLUMN subtask_order INTEGER DEFAULT 0;
                """))
                conn.commit()
                print("✓ subtask_order column added successfully")
            
            print("\n🎉 Database migration completed successfully!")
            print("\nNew features available:")
            print("• Subtask creation and management")
            print("• Hierarchical task relationships")
            print("• Parent task progress calculation based on subtasks")
            print("• Nested task views with drag-and-drop ordering")
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            return False
    
    return True

if __name__ == '__main__':
    if migrate_database():
        print("\n✅ Migration completed successfully!")
        print("You can now create subtasks for complex workflows.")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)