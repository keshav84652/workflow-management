#!/usr/bin/env python3
"""
Database migration script to add stored_progress_percentage field to Project model
Run this after implementing the unified project state management system
"""

from app import app
from src.shared.database.db_import import db
from models import Project

def add_stored_progress_field():
    """Add the stored_progress_percentage field and populate it"""
    
    with app.app_context():
        print("🔄 Adding stored_progress_percentage field to Project model...")
        
        try:
            # Check if the field already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('project')]
            
            if 'stored_progress_percentage' not in columns:
                print("   Adding column to database...")
                # Add the column
                db.engine.execute('ALTER TABLE project ADD COLUMN stored_progress_percentage FLOAT DEFAULT 0.0 NOT NULL')
                print("   ✅ Column added successfully")
            else:
                print("   ✅ Column already exists")
            
            # Populate the field with calculated values
            print("🔄 Populating stored progress values...")
            projects = Project.query.all()
            
            for project in projects:
                if project.tasks:
                    completed_tasks = len([t for t in project.tasks if t.status == 'Completed'])
                    progress = round((completed_tasks / len(project.tasks)) * 100, 1)
                else:
                    progress = 0.0
                
                # Update the stored value
                db.engine.execute(
                    'UPDATE project SET stored_progress_percentage = ? WHERE id = ?',
                    (progress, project.id)
                )
                print(f"   Updated {project.name}: {progress}%")
            
            db.session.commit()
            print("✅ Migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()

if __name__ == '__main__':
    add_stored_progress_field()