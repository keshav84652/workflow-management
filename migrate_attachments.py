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
    """Add file attachment table to the database"""
    with app.app_context():
        try:
            print("Starting database migration for file attachments...")
            
            # Create attachment table
            print("Creating attachment table...")
            with db.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS attachment (
                        id INTEGER PRIMARY KEY,
                        filename VARCHAR(255) NOT NULL,
                        original_filename VARCHAR(255) NOT NULL,
                        file_path VARCHAR(500) NOT NULL,
                        file_size INTEGER NOT NULL,
                        mime_type VARCHAR(100),
                        task_id INTEGER,
                        project_id INTEGER,
                        uploaded_by INTEGER NOT NULL,
                        uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        firm_id INTEGER NOT NULL,
                        FOREIGN KEY (task_id) REFERENCES task (id) ON DELETE CASCADE,
                        FOREIGN KEY (project_id) REFERENCES project (id) ON DELETE CASCADE,
                        FOREIGN KEY (uploaded_by) REFERENCES user (id),
                        FOREIGN KEY (firm_id) REFERENCES firm (id),
                        CONSTRAINT check_attachment_type CHECK (
                            (task_id IS NOT NULL AND project_id IS NULL) OR
                            (task_id IS NULL AND project_id IS NOT NULL)
                        )
                    );
                """))
                conn.commit()
                print("✓ attachment table created successfully")
            
            # Create uploads directory
            uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)
                print("✓ uploads directory created")
            else:
                print("✓ uploads directory already exists")
            
            print("\n🎉 Database migration completed successfully!")
            print("\nNew features available:")
            print("• File attachments for tasks and projects")
            print("• Secure file upload with type validation")
            print("• File download and preview capabilities")
            print("• Per-firm file isolation")
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            return False
    
    return True

if __name__ == '__main__':
    if migrate_database():
        print("\n✅ Migration completed successfully!")
        print("You can now upload files to tasks and projects.")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)