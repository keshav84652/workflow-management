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
    """Add enhanced time tracking fields to Task table"""
    with app.app_context():
        try:
            print("Starting database migration for enhanced time tracking...")
            
            # Add enhanced time tracking fields to Task table
            print("Adding time tracking fields to task table...")
            with db.engine.connect() as conn:
                # Add hourly_rate field
                try:
                    conn.execute(text("ALTER TABLE task ADD COLUMN hourly_rate REAL;"))
                    print("✓ Added hourly_rate column")
                except Exception as e:
                    if "duplicate column name" not in str(e):
                        raise e
                    print("✓ hourly_rate column already exists")
                
                # Add is_billable field
                try:
                    conn.execute(text("ALTER TABLE task ADD COLUMN is_billable BOOLEAN DEFAULT TRUE;"))
                    print("✓ Added is_billable column")
                except Exception as e:
                    if "duplicate column name" not in str(e):
                        raise e
                    print("✓ is_billable column already exists")
                
                # Add timer_start field
                try:
                    conn.execute(text("ALTER TABLE task ADD COLUMN timer_start DATETIME;"))
                    print("✓ Added timer_start column")
                except Exception as e:
                    if "duplicate column name" not in str(e):
                        raise e
                    print("✓ timer_start column already exists")
                
                # Add timer_running field
                try:
                    conn.execute(text("ALTER TABLE task ADD COLUMN timer_running BOOLEAN DEFAULT FALSE;"))
                    print("✓ Added timer_running column")
                except Exception as e:
                    if "duplicate column name" not in str(e):
                        raise e
                    print("✓ timer_running column already exists")
                
                conn.commit()
            
            print("\n🎉 Database migration completed successfully!")
            print("\nNew features available:")
            print("• Enhanced time tracking with start/stop timer")
            print("• Billing rates and billable amount calculation")
            print("• Time variance tracking (estimated vs actual)")
            print("• Time tracking reports and analytics")
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            return False
    
    return True

if __name__ == '__main__':
    if migrate_database():
        print("\n✅ Migration completed successfully!")
        print("Enhanced time tracking is now available.")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)