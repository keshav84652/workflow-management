#!/usr/bin/env python3
"""
CPA WorkflowPilot Database Initialization Script v2.0
Creates a fresh database with work types, custom statuses, and demo data
"""

from app import app
from models import db, Firm, User, Template, TemplateTask, Project, Task, ActivityLog, Client, TaskComment, WorkType, TaskStatus, Contact, ClientContact
from utils import generate_access_code, create_activity_log
from datetime import datetime, date, timedelta
import random

def clear_database():
    """Drop all tables and recreate them"""
    print("🗑️  Dropping existing tables...")
    db.drop_all()
    
    print("🔨 Creating new database schema...")
    db.create_all()
    
    print("✅ Database schema updated successfully!")

def create_default_work_types_and_statuses(firm_id):
    """Create default CPA work types with their specific status workflows"""
    
    work_types_data = [
        {
            'name': 'Tax Preparation',
            'description': 'Individual and business tax return preparation',
            'color': '#dc2626',  # Red
            'statuses': [
                {'name': 'Awaiting Documents', 'color': '#6b7280', 'position': 1, 'is_default': True},
                {'name': 'In Preparation', 'color': '#3b82f6', 'position': 2},
                {'name': 'In Review', 'color': '#f59e0b', 'position': 3},
                {'name': 'Ready for Filing', 'color': '#8b5cf6', 'position': 4},
                {'name': 'Filed', 'color': '#10b981', 'position': 5},
                {'name': 'Completed', 'color': '#059669', 'position': 6, 'is_terminal': True}
            ]
        },
        {
            'name': 'Monthly Bookkeeping',
            'description': 'Regular bookkeeping and financial statement preparation',
            'color': '#059669',  # Green
            'statuses': [
                {'name': 'Awaiting Bank Info', 'color': '#6b7280', 'position': 1, 'is_default': True},
                {'name': 'Data Entry', 'color': '#3b82f6', 'position': 2},
                {'name': 'Reconciliation', 'color': '#f59e0b', 'position': 3},
                {'name': 'Manager Review', 'color': '#8b5cf6', 'position': 4},
                {'name': 'Completed', 'color': '#059669', 'position': 5, 'is_terminal': True}
            ]
        },
        {
            'name': 'Payroll Processing',
            'description': 'Payroll calculation, processing, and filing',
            'color': '#3b82f6',  # Blue
            'statuses': [
                {'name': 'Data Collection', 'color': '#6b7280', 'position': 1, 'is_default': True},
                {'name': 'Processing', 'color': '#3b82f6', 'position': 2},
                {'name': 'Review & Approval', 'color': '#f59e0b', 'position': 3},
                {'name': 'Submitted', 'color': '#10b981', 'position': 4},
                {'name': 'Completed', 'color': '#059669', 'position': 5, 'is_terminal': True}
            ]
        },
        {
            'name': 'Advisory Services',
            'description': 'Business consulting and advisory engagements',
            'color': '#8b5cf6',  # Purple
            'statuses': [
                {'name': 'Planning', 'color': '#6b7280', 'position': 1, 'is_default': True},
                {'name': 'Research', 'color': '#3b82f6', 'position': 2},
                {'name': 'Client Meeting', 'color': '#f59e0b', 'position': 3},
                {'name': 'Report Preparation', 'color': '#8b5cf6', 'position': 4},
                {'name': 'Delivered', 'color': '#059669', 'position': 5, 'is_terminal': True}
            ]
        }
    ]
    
    created_work_types = []
    
    for wt_data in work_types_data:
        # Create work type
        work_type = WorkType(
            firm_id=firm_id,
            name=wt_data['name'],
            description=wt_data['description'],
            color=wt_data['color'],
            position=len(created_work_types) + 1
        )
        db.session.add(work_type)
        db.session.flush()  # Get the ID
        
        # Create statuses for this work type
        for status_data in wt_data['statuses']:
            status = TaskStatus(
                firm_id=firm_id,
                work_type_id=work_type.id,
                name=status_data['name'],
                color=status_data['color'],
                position=status_data['position'],
                is_terminal=status_data.get('is_terminal', False),
                is_default=status_data.get('is_default', False)
            )
            db.session.add(status)
        
        created_work_types.append(work_type)
        print(f"   ✅ Created {wt_data['name']} with {len(wt_data['statuses'])} statuses")
    
    db.session.commit()
    return created_work_types

def create_sample_contacts():
    """Create sample contacts for demonstration"""
    contacts_data = [
        {'first_name': 'John', 'last_name': 'Smith', 'email': 'john.smith@abccorp.com', 'phone': '555-0101', 'title': 'CEO'},
        {'first_name': 'Sarah', 'last_name': 'Johnson', 'email': 'sarah.j@techstartup.com', 'phone': '555-0102', 'title': 'Founder'},
        {'first_name': 'Michael', 'last_name': 'Brown', 'email': 'mbrown@retailbiz.com', 'phone': '555-0103', 'title': 'Owner'},
        {'first_name': 'Emily', 'last_name': 'Davis', 'email': 'emily.davis@restaurant.com', 'phone': '555-0104', 'title': 'Manager'},
        {'first_name': 'David', 'last_name': 'Wilson', 'email': 'dwilson@consulting.com', 'phone': '555-0105', 'title': 'Partner'},
        {'first_name': 'Lisa', 'last_name': 'Anderson', 'email': 'lisa.a@freelance.com', 'phone': '555-0106', 'title': 'Freelancer'},
        {'first_name': 'Robert', 'last_name': 'Taylor', 'email': 'robert.taylor@construction.com', 'phone': '555-0107', 'title': 'Contractor'},
        {'first_name': 'Jennifer', 'last_name': 'Martinez', 'email': 'jen.martinez@healthcare.com', 'phone': '555-0108', 'title': 'Administrator'}
    ]
    
    contacts = []
    for contact_data in contacts_data:
        contact = Contact(**contact_data)
        db.session.add(contact)
        contacts.append(contact)
    
    db.session.commit()
    return contacts

def initialize_database():
    """Main initialization function"""
    
    with app.app_context():
        # Clear existing database
        clear_database()
        
        # Create firm
        print("🏢 Creating demo firm...")
        access_code = generate_access_code()
        firm = Firm(
            name="Demo CPA Firm",
            access_code=access_code,
            is_active=True
        )
        db.session.add(firm)
        db.session.commit()
        
        # Create work types and statuses
        print("🎯 Creating work types and custom statuses...")
        work_types = create_default_work_types_and_statuses(firm.id)
        
        # Create users
        print("👥 Creating demo users...")
        users_data = [
            {'name': 'Sarah Johnson', 'role': 'Admin'},
            {'name': 'Michael Chen', 'role': 'Admin'},
            {'name': 'Emily Rodriguez', 'role': 'Member'},
            {'name': 'David Park', 'role': 'Member'}
        ]
        
        users = []
        for user_data in users_data:
            user = User(
                name=user_data['name'],
                role=user_data['role'],
                firm_id=firm.id
            )
            db.session.add(user)
            users.append(user)
        
        db.session.commit()
        
        # Create sample contacts
        print("📞 Creating sample contacts...")
        contacts = create_sample_contacts()
        
        # Create clients with contact associations
        print("👔 Creating demo clients...")
        clients_data = [
            {'name': 'ABC Corporation', 'entity_type': 'C-Corp', 'tax_id': '12-3456789', 'contact_idx': [0]},
            {'name': 'Tech Startup LLC', 'entity_type': 'LLC', 'tax_id': '98-7654321', 'contact_idx': [1]},
            {'name': 'Retail Business Inc', 'entity_type': 'S-Corp', 'tax_id': '11-2233445', 'contact_idx': [2]},
            {'name': 'Local Restaurant', 'entity_type': 'Partnership', 'tax_id': '33-4455667', 'contact_idx': [3]},
            {'name': 'Consulting Group', 'entity_type': 'LLC', 'tax_id': '55-6677889', 'contact_idx': [4]},
            {'name': 'Individual Client', 'entity_type': 'Individual', 'tax_id': '123-45-6789', 'contact_idx': [5, 6]},  # Multiple contacts
            {'name': 'Construction Co', 'entity_type': 'LLC', 'tax_id': '77-8899001', 'contact_idx': [6]},
            {'name': 'Healthcare Practice', 'entity_type': 'Professional Corp', 'tax_id': '99-0011223', 'contact_idx': [7]}
        ]
        
        clients = []
        for client_data in clients_data:
            client = Client(
                name=client_data['name'],
                entity_type=client_data['entity_type'],
                tax_id=client_data['tax_id'],
                firm_id=firm.id,
                is_active=True
            )
            db.session.add(client)
            db.session.flush()  # Get the ID
            
            # Associate contacts with client
            for contact_idx in client_data['contact_idx']:
                client_contact = ClientContact(
                    client_id=client.id,
                    contact_id=contacts[contact_idx].id,
                    is_primary=(contact_idx == client_data['contact_idx'][0]),  # First contact is primary
                    relationship_type='Primary Contact' if contact_idx == client_data['contact_idx'][0] else 'Secondary Contact'
                )
                db.session.add(client_contact)
            
            clients.append(client)
        
        db.session.commit()
        
        # Create templates for each work type
        print("📋 Creating work type-specific templates...")
        templates_data = [
            {
                'name': 'Individual Tax Return (1040)',
                'description': 'Standard individual tax return preparation',
                'work_type': 'Tax Preparation',
                'tasks': [
                    {'title': 'Collect client documents', 'days_from_start': 0, 'estimated_hours': 0.5},
                    {'title': 'Review prior year return', 'days_from_start': 1, 'estimated_hours': 1.0},
                    {'title': 'Prepare tax return', 'days_from_start': 3, 'estimated_hours': 4.0},
                    {'title': 'Manager review', 'days_from_start': 5, 'estimated_hours': 1.0},
                    {'title': 'Client review and signature', 'days_from_start': 7, 'estimated_hours': 0.5},
                    {'title': 'E-file return', 'days_from_start': 10, 'estimated_hours': 0.25}
                ]
            },
            {
                'name': 'Monthly Bookkeeping Package',
                'description': 'Standard monthly bookkeeping services',
                'work_type': 'Monthly Bookkeeping',
                'tasks': [
                    {'title': 'Download bank statements', 'days_from_start': 0, 'estimated_hours': 0.25},
                    {'title': 'Categorize transactions', 'days_from_start': 1, 'estimated_hours': 3.0},
                    {'title': 'Reconcile bank accounts', 'days_from_start': 2, 'estimated_hours': 2.0},
                    {'title': 'Generate financial statements', 'days_from_start': 3, 'estimated_hours': 1.0},
                    {'title': 'Review and finalize', 'days_from_start': 4, 'estimated_hours': 0.5}
                ]
            },
            {
                'name': 'Bi-Weekly Payroll',
                'description': 'Standard bi-weekly payroll processing',
                'work_type': 'Payroll Processing',
                'tasks': [
                    {'title': 'Collect timesheets', 'days_from_start': 0, 'estimated_hours': 0.5},
                    {'title': 'Calculate payroll', 'days_from_start': 1, 'estimated_hours': 1.5},
                    {'title': 'Review calculations', 'days_from_start': 1, 'estimated_hours': 0.5},
                    {'title': 'Process payroll', 'days_from_start': 2, 'estimated_hours': 0.75},
                    {'title': 'File payroll taxes', 'days_from_start': 3, 'estimated_hours': 0.5}
                ]
            },
            {
                'name': 'Business Advisory Consultation',
                'description': 'Strategic business advisory engagement',
                'work_type': 'Advisory Services',
                'tasks': [
                    {'title': 'Initial client meeting', 'days_from_start': 0, 'estimated_hours': 2.0},
                    {'title': 'Research industry trends', 'days_from_start': 2, 'estimated_hours': 4.0},
                    {'title': 'Financial analysis', 'days_from_start': 5, 'estimated_hours': 6.0},
                    {'title': 'Prepare recommendations', 'days_from_start': 8, 'estimated_hours': 3.0},
                    {'title': 'Present findings to client', 'days_from_start': 12, 'estimated_hours': 2.0}
                ]
            }
        ]
        
        templates = []
        for template_data in templates_data:
            # Find the work type
            work_type = next((wt for wt in work_types if wt.name == template_data['work_type']), None)
            
            template = Template(
                name=template_data['name'],
                description=template_data['description'],
                firm_id=firm.id,
                work_type_id=work_type.id if work_type else None
            )
            db.session.add(template)
            db.session.flush()  # Get the ID
            
            # Create template tasks
            for task_data in template_data['tasks']:
                template_task = TemplateTask(
                    title=task_data['title'],
                    estimated_hours=task_data['estimated_hours'],
                    days_from_start=task_data['days_from_start'],
                    template_id=template.id,
                    order=len(templates) * 10 + task_data.get('order', 0)
                )
                db.session.add(template_task)
            
            templates.append(template)
        
        db.session.commit()
        
        # Create sample projects with the new work type system
        print("📁 Creating sample projects...")
        projects_data = [
            {
                'name': '2024 Tax Return',
                'client_idx': 0,
                'template_idx': 0,  # Individual Tax Return
                'start_date': date(2024, 12, 1),
                'due_date': date(2025, 4, 15),
                'priority': 'High'
            },
            {
                'name': 'December 2024 Bookkeeping',
                'client_idx': 1,
                'template_idx': 1,  # Monthly Bookkeeping
                'start_date': date(2025, 1, 1),
                'due_date': date(2025, 1, 15),
                'priority': 'Medium'
            },
            {
                'name': 'Q4 2024 Payroll',
                'client_idx': 2,
                'template_idx': 2,  # Payroll
                'start_date': date(2024, 12, 15),
                'due_date': date(2025, 1, 31),
                'priority': 'High'
            },
            {
                'name': 'Business Growth Strategy',
                'client_idx': 3,
                'template_idx': 3,  # Advisory
                'start_date': date(2025, 1, 1),
                'due_date': date(2025, 2, 28),
                'priority': 'Medium'
            }
        ]
        
        projects = []
        for project_data in projects_data:
            template = templates[project_data['template_idx']]
            client = clients[project_data['client_idx']]
            
            project = Project(
                name=project_data['name'],
                client_id=client.id,
                work_type_id=template.work_type_id,
                start_date=project_data['start_date'],
                due_date=project_data['due_date'],
                priority=project_data['priority'],
                firm_id=firm.id,
                template_origin_id=template.id,
                status='Active'
            )
            db.session.add(project)
            db.session.flush()  # Get the ID
            
            # Create tasks from template
            for template_task in template.template_tasks:
                # Calculate due date based on template
                task_due_date = project_data['start_date'] + timedelta(days=template_task.days_from_start)
                
                # Get default status for this work type
                default_status = TaskStatus.query.filter_by(
                    work_type_id=template.work_type_id,
                    is_default=True
                ).first()
                
                task = Task(
                    title=template_task.title,
                    description=f"Task from {template.name} template",
                    due_date=task_due_date,
                    estimated_hours=template_task.estimated_hours,
                    priority=project_data['priority'],
                    project_id=project.id,
                    firm_id=firm.id,
                    assignee_id=random.choice(users).id,
                    template_task_origin_id=template_task.id,
                    status='Not Started',  # Legacy field
                    status_id=default_status.id if default_status else None
                )
                db.session.add(task)
            
            projects.append(project)
        
        db.session.commit()
        
        # Success message
        print("\n" + "="*60)
        print("✅ CPA WorkflowPilot v2.0 Database initialized successfully!")
        print("="*60)
        print(f"🔑 Access Code: {access_code}")
        print(f"🏢 Firm: {firm.name}")
        print(f"👥 Users: {len(users)} team members")
        print(f"🎯 Work Types: {len(work_types)} service lines")
        print(f"📊 Total Statuses: {TaskStatus.query.count()}")
        print(f"📞 Contacts: {len(contacts)} individuals")
        print(f"👔 Clients: {len(clients)} with contact relationships")
        print(f"📋 Templates: {len(templates)} work type-specific")
        print(f"📁 Projects: {len(projects)} active engagements")
        print(f"✅ Tasks: {Task.query.count()} with new status system")
        print("\n🚀 Ready to launch the enhanced CPA WorkflowPilot!")
        print(f"   Visit http://localhost:5000 and use access code: {access_code}")
        print("="*60)

if __name__ == "__main__":
    initialize_database()