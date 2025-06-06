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
    """Add recurring task tables to the database"""
    with app.app_context():
        try:
            print("Starting database migration for recurring tasks...")
            
            # Create recurring_task table
            print("Creating recurring_task table...")
            with db.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS recurring_task (
                        id INTEGER PRIMARY KEY,
                        firm_id INTEGER NOT NULL,
                        title VARCHAR(200) NOT NULL,
                        description TEXT,
                        recurrence_rule VARCHAR(100) NOT NULL,
                        priority VARCHAR(10) NOT NULL DEFAULT 'Medium',
                        estimated_hours FLOAT,
                        default_assignee_id INTEGER,
                        client_id INTEGER,
                        status_id INTEGER,
                        work_type_id INTEGER,
                        is_active BOOLEAN NOT NULL DEFAULT 1,
                        next_due_date DATE NOT NULL,
                        last_generated DATE,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (firm_id) REFERENCES firm (id),
                        FOREIGN KEY (default_assignee_id) REFERENCES user (id),
                        FOREIGN KEY (client_id) REFERENCES client (id),
                        FOREIGN KEY (status_id) REFERENCES task_status (id),
                        FOREIGN KEY (work_type_id) REFERENCES work_type (id)
                    );
                """))
                conn.commit()
                print("✓ recurring_task table created successfully")
            
            # Add recurring_task_origin_id to task table
            print("Adding recurring_task_origin_id to task table...")
            with db.engine.connect() as conn:
                # Check if column already exists
                result = conn.execute(text("PRAGMA table_info(task)"))
                columns = [row[1] for row in result.fetchall()]
                
                if 'recurring_task_origin_id' not in columns:
                    conn.execute(text("""
                        ALTER TABLE task 
                        ADD COLUMN recurring_task_origin_id INTEGER 
                        REFERENCES recurring_task(id);
                    """))
                    conn.commit()
                    print("✓ recurring_task_origin_id column added to task table")
                else:
                    print("✓ recurring_task_origin_id column already exists")
            
            print("\n🎉 Database migration completed successfully!")
            print("\nNew features available:")
            print("• Standalone recurring tasks")
            print("• Automatic task generation based on schedules")
            print("• Client and work type association for recurring tasks")
            print("• Recurring task management interface")
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            return False
    
    return True

if __name__ == '__main__':
    if migrate_database():
        print("\n✅ Migration completed successfully!")
        print("You can now use recurring tasks in the application.")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)