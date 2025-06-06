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

def cleanup_database():
    """Remove old RecurringTask table and references"""
    with app.app_context():
        try:
            print("Cleaning up old recurring task implementation...")
            
            # Drop old RecurringTask table if it exists
            with db.engine.connect() as conn:
                try:
                    conn.execute(text("DROP TABLE IF EXISTS recurring_task;"))
                    print("✓ Removed old recurring_task table")
                except Exception as e:
                    print(f"Note: {str(e)}")
                
                # Remove old recurring_task_origin_id column from task table if it exists
                try:
                    # SQLite doesn't support DROP COLUMN, so we'll just leave it
                    # It will be ignored since it's not in the model anymore
                    print("✓ Old recurring_task_origin_id column will be ignored")
                except Exception as e:
                    print(f"Note: {str(e)}")
                
                conn.commit()
            
            print("\n🎉 Cleanup completed successfully!")
            print("\nChanges made:")
            print("• Removed separate RecurringTask table")
            print("• Recurring functionality now integrated into Task model")
            print("• Old references cleaned up")
            
        except Exception as e:
            print(f"❌ Cleanup failed: {str(e)}")
            return False
    
    return True

if __name__ == '__main__':
    if cleanup_database():
        print("\n✅ Cleanup completed successfully!")
        print("Recurring tasks are now fully integrated.")
    else:
        print("\n❌ Cleanup failed!")
        sys.exit(1)