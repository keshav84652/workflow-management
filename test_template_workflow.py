#!/usr/bin/env python3

import os
import sys
from flask import Flask

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the app and models
from app import app
from models import db, Template, WorkType, TaskStatus

def test_template_workflow():
    """Test template-to-work-type auto-creation"""
    with app.app_context():
        try:
            print("Testing template workflow auto-creation...")
            
            # Get all templates
            templates = Template.query.all()
            print(f"Found {len(templates)} templates:")
            
            for template in templates:
                print(f"\nTemplate: {template.name}")
                print(f"  Firm ID: {template.firm_id}")
                print(f"  Work Type ID: {template.work_type_id}")
                print(f"  Auto-create Work Type: {template.auto_create_work_type}")
                print(f"  Template Tasks: {len(template.template_tasks)}")
                
                # List template tasks
                for i, task in enumerate(template.template_tasks):
                    print(f"    Task {i+1}: {task.title}")
                
                # If template doesn't have a work type, create one
                if not template.work_type_id and template.auto_create_work_type:
                    print(f"  → Creating work type for template '{template.name}'...")
                    work_type_id = template.create_work_type_from_template()
                    print(f"  → Work type created with ID: {work_type_id}")
                
                # Show work type and statuses
                if template.work_type_id:
                    work_type = WorkType.query.get(template.work_type_id)
                    if work_type:
                        statuses = TaskStatus.query.filter_by(work_type_id=work_type.id).order_by(TaskStatus.position).all()
                        print(f"  Work Type: {work_type.name} ({len(statuses)} statuses)")
                        for status in statuses:
                            default_marker = " (DEFAULT)" if status.is_default else ""
                            terminal_marker = " (TERMINAL)" if status.is_terminal else ""
                            print(f"    Status {status.position}: {status.name}{default_marker}{terminal_marker}")
                    else:
                        print(f"  ❌ Work Type ID {template.work_type_id} not found!")
                else:
                    print(f"  No work type associated")
            
            print("\n✅ Template workflow test completed!")
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == '__main__':
    test_template_workflow()