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
    """Update database to support template-driven workflow"""
    with app.app_context():
        try:
            print("Starting database migration for template-driven workflow...")
            
            # Add current_status_id to Project table to track workflow progress
            print("Adding current_status_id to project table...")
            with db.engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE project 
                    ADD COLUMN current_status_id INTEGER REFERENCES task_status(id);
                """))
                conn.commit()
                print("✓ current_status_id column added to project table")
            
            # Add auto_create_work_type flag to Template table
            print("Adding auto_create_work_type flag to template table...")
            with db.engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE template 
                    ADD COLUMN auto_create_work_type BOOLEAN DEFAULT TRUE;
                """))
                conn.commit()
                print("✓ auto_create_work_type column added to template table")
            
            # Add workflow_order to TemplateTask to define kanban column order
            print("Adding workflow_order to template_task table...")
            with db.engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE template_task 
                    ADD COLUMN workflow_order INTEGER DEFAULT 0;
                """))
                conn.commit()
                print("✓ workflow_order column added to template_task table")
            
            print("\n🎉 Database migration completed successfully!")
            print("\nNew features available:")
            print("• Templates automatically create work types")
            print("• Template tasks become kanban column headers")
            print("• Projects move through workflow stages")
            print("• Kanban shows projects as cards instead of individual tasks")
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            return False
    
    return True

if __name__ == '__main__':
    if migrate_database():
        print("\n✅ Migration completed successfully!")
        print("Templates will now drive the kanban workflow.")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)