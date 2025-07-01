#!/usr/bin/env python3
"""
Sample Data Initialization Script for CPA WorkflowPilot
Creates basic data for testing and demonstration purposes.
"""

import sys
from pathlib import Path
from datetime import date, timedelta, datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.app import create_app
from src.shared.database.db_import import db
from src.models.auth import Firm, User
from src.modules.client.models import Client
from src.modules.project.models import Project, Task, WorkType, TaskStatus
from src.modules.project.models import Template, TemplateTask

def init_sample_data():
    """Initialize sample data for the demo"""
    app = create_app()
    
    with app.app_context():
        print("🔄 Initializing sample data...")
        
        # Get the demo firm (should already exist)
        firm = Firm.query.filter_by(name="Demo CPA Firm").first()
        if not firm:
            print("❌ Demo firm not found. Please run authentication first.")
            return
        
        print(f"✅ Using firm: {firm.name}")
        
        # Create sample work types if they don't exist
        work_types_data = [
            {"name": "Tax Preparation", "description": "Individual and business tax returns", "color": "#3b82f6"},
            {"name": "Bookkeeping", "description": "Monthly bookkeeping services", "color": "#10b981"},
            {"name": "Audit", "description": "Financial statement audits", "color": "#f59e0b"},
            {"name": "Consulting", "description": "Business advisory services", "color": "#8b5cf6"},
        ]
        
        work_types = {}
        for wt_data in work_types_data:
            work_type = WorkType.query.filter_by(name=wt_data["name"], firm_id=firm.id).first()
            if not work_type:
                work_type = WorkType(
                    name=wt_data["name"],
                    description=wt_data["description"],
                    color=wt_data["color"],
                    firm_id=firm.id
                )
                db.session.add(work_type)
                db.session.flush()
                print(f"✅ Created work type: {work_type.name}")
            work_types[wt_data["name"]] = work_type
        
        # Create task statuses for each work type
        status_templates = [
            {"name": "Not Started", "color": "#6b7280", "order": 1},
            {"name": "In Progress", "color": "#3b82f6", "order": 2},
            {"name": "Review", "color": "#f59e0b", "order": 3},
            {"name": "Completed", "color": "#10b981", "order": 4},
        ]
        
        for work_type in work_types.values():
            for status_data in status_templates:
                status = TaskStatus.query.filter_by(
                    name=status_data["name"], 
                    work_type_id=work_type.id
                ).first()
                if not status:
                    status = TaskStatus(
                        name=status_data["name"],
                        color=status_data["color"],
                        work_type_id=work_type.id,
                        firm_id=firm.id,
                        position=status_data["order"]
                    )
                    db.session.add(status)
        
        # Create sample clients if they don't exist
        sample_clients = [
            {"name": "ABC Corporation", "email": "contact@abc-corp.com", "entity_type": "Corporation"},
            {"name": "John Smith", "email": "john.smith@email.com", "entity_type": "Individual"},
            {"name": "Smith & Partners LLC", "email": "info@smithpartners.com", "entity_type": "LLC"},
            {"name": "Tech Startup Inc", "email": "admin@techstartup.com", "entity_type": "Corporation"},
            {"name": "Jane Doe", "email": "jane.doe@email.com", "entity_type": "Individual"},
        ]
        
        clients = {}
        for client_data in sample_clients:
            client = Client.query.filter_by(name=client_data["name"], firm_id=firm.id).first()
            if not client:
                client = Client(
                    name=client_data["name"],
                    email=client_data["email"],
                    entity_type=client_data["entity_type"],
                    firm_id=firm.id,
                    is_active=True
                )
                db.session.add(client)
                db.session.flush()
                print(f"✅ Created client: {client.name}")
            clients[client_data["name"]] = client
        
        # Create sample projects
        sample_projects = [
            {
                "name": "2024 Tax Return - ABC Corp",
                "client": "ABC Corporation",
                "work_type": "Tax Preparation",
                "status": "Active",
                "priority": "High",
                "due_date": date.today() + timedelta(days=30)
            },
            {
                "name": "Monthly Bookkeeping - Smith LLC",
                "client": "Smith & Partners LLC", 
                "work_type": "Bookkeeping",
                "status": "Active",
                "priority": "Medium",
                "due_date": date.today() + timedelta(days=15)
            },
            {
                "name": "2023 Audit - Tech Startup",
                "client": "Tech Startup Inc",
                "work_type": "Audit", 
                "status": "Active",
                "priority": "High",
                "due_date": date.today() + timedelta(days=45)
            },
            {
                "name": "Tax Planning - John Smith",
                "client": "John Smith",
                "work_type": "Consulting",
                "status": "Active", 
                "priority": "Low",
                "due_date": date.today() + timedelta(days=60)
            },
            {
                "name": "Personal Tax Return - Jane Doe",
                "client": "Jane Doe",
                "work_type": "Tax Preparation",
                "status": "Active",
                "priority": "Medium", 
                "due_date": date.today() + timedelta(days=20)
            }
        ]
        
        projects = {}
        for proj_data in sample_projects:
            project = Project.query.filter_by(name=proj_data["name"], firm_id=firm.id).first()
            if not project:
                project = Project(
                    name=proj_data["name"],
                    client_id=clients[proj_data["client"]].id,
                    work_type_id=work_types[proj_data["work_type"]].id,
                    status=proj_data["status"],
                    priority=proj_data["priority"],
                    start_date=date.today(),
                    due_date=proj_data["due_date"],
                    firm_id=firm.id
                )
                db.session.add(project)
                db.session.flush()
                print(f"✅ Created project: {project.name}")
            projects[proj_data["name"]] = project
        
        # Create sample tasks for each project
        sample_tasks = [
            # ABC Corp Tax Return
            {"project": "2024 Tax Return - ABC Corp", "title": "Gather Financial Documents", "status": "Completed", "priority": "High"},
            {"project": "2024 Tax Return - ABC Corp", "title": "Review Income Statements", "status": "In Progress", "priority": "High"},
            {"project": "2024 Tax Return - ABC Corp", "title": "Prepare Tax Forms", "status": "Not Started", "priority": "High"},
            {"project": "2024 Tax Return - ABC Corp", "title": "Client Review", "status": "Not Started", "priority": "Medium"},
            
            # Smith LLC Bookkeeping
            {"project": "Monthly Bookkeeping - Smith LLC", "title": "Reconcile Bank Statements", "status": "Completed", "priority": "High"},
            {"project": "Monthly Bookkeeping - Smith LLC", "title": "Enter Transactions", "status": "In Progress", "priority": "High"},
            {"project": "Monthly Bookkeeping - Smith LLC", "title": "Generate Reports", "status": "Not Started", "priority": "Medium"},
            
            # Tech Startup Audit  
            {"project": "2023 Audit - Tech Startup", "title": "Planning and Risk Assessment", "status": "Completed", "priority": "High"},
            {"project": "2023 Audit - Tech Startup", "title": "Test Internal Controls", "status": "In Progress", "priority": "High"},
            {"project": "2023 Audit - Tech Startup", "title": "Substantive Testing", "status": "Not Started", "priority": "High"},
            {"project": "2023 Audit - Tech Startup", "title": "Draft Audit Report", "status": "Not Started", "priority": "Medium"},
            
            # John Smith Consulting
            {"project": "Tax Planning - John Smith", "title": "Financial Analysis", "status": "In Progress", "priority": "Medium"},
            {"project": "Tax Planning - John Smith", "title": "Strategy Development", "status": "Not Started", "priority": "Medium"},
            
            # Jane Doe Tax Return
            {"project": "Personal Tax Return - Jane Doe", "title": "Collect W-2s and 1099s", "status": "Completed", "priority": "Medium"},
            {"project": "Personal Tax Return - Jane Doe", "title": "Prepare Return", "status": "In Progress", "priority": "Medium"},
        ]
        
        # Get users for task assignment
        users = User.query.filter_by(firm_id=firm.id).all()
        
        for task_data in sample_tasks:
            # Check if task already exists
            project = projects[task_data["project"]]
            task = Task.query.filter_by(title=task_data["title"], project_id=project.id).first()
            if not task:
                task = Task(
                    title=task_data["title"],
                    description=f"Task for {project.name}",
                    project_id=project.id,
                    status=task_data["status"],
                    priority=task_data["priority"],
                    assignee_id=users[0].id if users else None,
                    due_date=date.today() + timedelta(days=7),
                    firm_id=firm.id
                )
                db.session.add(task)
        
        # Commit all changes
        db.session.commit()
        
        # Print summary
        print("\n📊 Sample Data Summary:")
        print(f"   Work Types: {WorkType.query.filter_by(firm_id=firm.id).count()}")
        print(f"   Task Statuses: {TaskStatus.query.filter_by(firm_id=firm.id).count()}")  
        print(f"   Clients: {Client.query.filter_by(firm_id=firm.id).count()}")
        print(f"   Projects: {Project.query.filter_by(firm_id=firm.id).count()}")
        print(f"   Tasks: {Task.query.filter_by(firm_id=firm.id).count()}")
        
        print("\n✅ Sample data initialization completed!")

if __name__ == '__main__':
    init_sample_data()