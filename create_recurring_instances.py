#!/usr/bin/env python3

import os
import sys
from datetime import date, datetime
from flask import Flask

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the app and models
from app import app
from models import db, Task

def create_due_recurring_instances():
    """Create new instances of recurring tasks that are due"""
    with app.app_context():
        try:
            print("Checking for recurring tasks that need new instances...")
            
            # Find recurring master tasks that need new instances
            recurring_masters = Task.query.filter(
                Task.is_recurring == True,
                Task.master_task_id.is_(None),  # Only master tasks
                Task.next_due_date <= date.today()  # Due for next instance
            ).all()
            
            instances_created = 0
            
            for master_task in recurring_masters:
                print(f"Processing recurring task: {master_task.title}")
                
                # Create the next instance
                next_instance = master_task.create_next_instance()
                if next_instance:
                    db.session.add(next_instance)
                    
                    # Update master task's next due date
                    master_task.next_due_date = master_task.calculate_next_due_date(
                        from_date=next_instance.due_date
                    )
                    
                    instances_created += 1
                    print(f"  → Created instance for {next_instance.due_date}")
                else:
                    print(f"  → Failed to create instance")
            
            if instances_created > 0:
                db.session.commit()
                print(f"\n✅ Created {instances_created} recurring task instances")
            else:
                print("\n✅ No recurring task instances needed")
            
            return instances_created
            
        except Exception as e:
            print(f"❌ Failed to create recurring instances: {str(e)}")
            db.session.rollback()
            return 0

if __name__ == '__main__':
    count = create_due_recurring_instances()
    print(f"\nProcessed recurring tasks: {count} instances created")