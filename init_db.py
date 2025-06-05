from app import app, db
from models import Firm, User, Template, TemplateTask, Client, Project, Task
from utils import generate_access_code, calculate_task_due_date
from datetime import date, timedelta

def init_database():
    with app.app_context():
        # Drop all tables and recreate (clear existing data)
        db.drop_all()
        db.create_all()
        
        # Create demo firm
        access_code = generate_access_code()
        demo_firm = Firm(name='Premier CPA Solutions', access_code=access_code)
        db.session.add(demo_firm)
        db.session.flush()
        
        # Create users
        admin_user = User(
            name='Sarah Johnson',
            role='Admin',
            firm_id=demo_firm.id
        )
        db.session.add(admin_user)
        
        senior_user = User(
            name='Michael Chen',
            role='Admin',
            firm_id=demo_firm.id
        )
        db.session.add(senior_user)
        
        junior_user = User(
            name='Emily Rodriguez',
            role='Member',
            firm_id=demo_firm.id
        )
        db.session.add(junior_user)
        
        associate_user = User(
            name='David Park',
            role='Member',
            firm_id=demo_firm.id
        )
        db.session.add(associate_user)
        db.session.flush()
        
        # Create clients
        clients_data = [
            ('Acme Corporation', 'Corporation', 'john.smith@acme.com', '(555) 123-4567', 'CEO', '12-3456789'),
            ('Johnson & Associates LLC', 'LLC', 'mary@johnsonlaw.com', '(555) 234-5678', 'Mary Johnson', '98-7654321'),
            ('Robert Wilson', 'Individual', 'rwilson@email.com', '(555) 345-6789', None, '123-45-6789'),
            ('Tech Startup Inc', 'S-Corp', 'ceo@techstartup.com', '(555) 456-7890', 'Jennifer Lee', '55-5555555'),
            ('Green Valley Trust', 'Trust', 'trustee@greenvalley.org', '(555) 567-8901', 'Thomas Brown', '77-7777777'),
            ('Downtown Restaurant Group', 'Partnership', 'partners@downtown.com', '(555) 678-9012', 'Lisa Wang', '33-3333333')
        ]
        
        clients = []
        for name, entity_type, email, phone, contact, tax_id in clients_data:
            client = Client(
                name=name,
                entity_type=entity_type,
                email=email,
                phone=phone,
                contact_person=contact,
                tax_id=tax_id,
                firm_id=demo_firm.id,
                address=f"123 Business St\nSuite 100\nCityville, ST 12345"
            )
            db.session.add(client)
            clients.append(client)
        db.session.flush()
        
        # Create enhanced templates with better task structure
        templates_data = [
            {
                'name': '1040 Individual Tax Return',
                'description': 'Complete individual tax return preparation workflow',
                'tasks': [
                    ('Initial client meeting', 'Meet with client to discuss tax situation', 1, 'High', 2.0),
                    ('Gather tax documents', 'Collect W-2s, 1099s, receipts, and other documents', 2, 'High', 1.5),
                    ('Organize and review documents', 'Sort and verify all tax documents', 3, 'Medium', 1.0),
                    ('Prepare federal return', 'Complete federal Form 1040', 7, 'High', 4.0),
                    ('Prepare state return', 'Complete state tax return', 8, 'High', 2.0),
                    ('Quality review', 'Partner review of completed returns', 10, 'High', 1.0),
                    ('Client review meeting', 'Present returns to client for approval', 12, 'Medium', 1.0),
                    ('E-file returns', 'Submit federal and state returns electronically', 14, 'High', 0.5),
                    ('Follow up and delivery', 'Deliver copies and follow up on refund/payment', 16, 'Low', 0.5)
                ]
            },
            {
                'name': 'Monthly Bookkeeping Service',
                'description': 'Comprehensive monthly bookkeeping and financial reporting',
                'tasks': [
                    ('Bank reconciliation', 'Reconcile all bank and credit card accounts', 5, 'High', 2.0),
                    ('Transaction categorization', 'Review and categorize all transactions', 3, 'High', 3.0),
                    ('Accounts receivable review', 'Review outstanding invoices and collections', 7, 'Medium', 1.0),
                    ('Accounts payable review', 'Review outstanding bills and payments', 8, 'Medium', 1.0),
                    ('Generate financial statements', 'Create P&L, Balance Sheet, and Cash Flow', 12, 'High', 2.0),
                    ('Client dashboard update', 'Update client portal with latest financials', 14, 'Low', 0.5),
                    ('Monthly client meeting', 'Review financials and discuss business performance', 18, 'Medium', 1.5)
                ]
            },
            {
                'name': 'Corporate Tax Return (1120)',
                'description': 'Corporate income tax return preparation',
                'tasks': [
                    ('Trial balance preparation', 'Prepare and review trial balance', 1, 'High', 3.0),
                    ('Book-to-tax adjustments', 'Calculate and document book-to-tax differences', 5, 'High', 4.0),
                    ('Prepare Form 1120', 'Complete corporate tax return', 10, 'High', 6.0),
                    ('State tax return preparation', 'Prepare state corporate returns', 12, 'High', 3.0),
                    ('Tax provision calculation', 'Calculate current and deferred tax provision', 8, 'High', 2.0),
                    ('Partner review', 'Senior partner review of completed return', 15, 'High', 2.0),
                    ('Client presentation', 'Present tax returns and planning opportunities', 18, 'Medium', 1.5),
                    ('E-file and extensions', 'File returns or extensions as needed', 20, 'High', 0.5)
                ]
            },
            {
                'name': 'Quarterly Payroll Tax Filing',
                'description': 'Quarterly payroll tax compliance and filing',
                'tasks': [
                    ('Payroll register review', 'Review quarterly payroll registers', 1, 'High', 1.0),
                    ('941 preparation', 'Prepare Form 941 quarterly return', 5, 'High', 2.0),
                    ('State unemployment filing', 'Prepare state unemployment returns', 7, 'High', 1.5),
                    ('Deposit verification', 'Verify all payroll tax deposits were made', 3, 'High', 1.0),
                    ('Client review', 'Review payroll tax filings with client', 10, 'Medium', 0.5),
                    ('E-file returns', 'Submit all quarterly payroll returns', 12, 'High', 0.5)
                ]
            }
        ]
        
        templates = []
        for template_data in templates_data:
            template = Template(
                name=template_data['name'],
                description=template_data['description'],
                firm_id=demo_firm.id
            )
            db.session.add(template)
            db.session.flush()
            templates.append(template)
            
            for i, (title, desc, days, priority, hours) in enumerate(template_data['tasks']):
                template_task = TemplateTask(
                    title=title,
                    description=desc,
                    order=i,
                    days_from_start=days,
                    default_priority=priority,
                    estimated_hours=hours,
                    template_id=template.id,
                    default_assignee_id=junior_user.id if priority == 'Low' else senior_user.id if priority == 'High' else associate_user.id
                )
                db.session.add(template_task)
        
        db.session.flush()
        
        # Create sample projects with tasks
        sample_projects = [
            ('2024 Tax Return', clients[2].id, templates[0].id, 'High', date(2024, 2, 1), date(2024, 4, 15)),
            ('March 2024 Bookkeeping', clients[0].id, templates[1].id, 'Medium', date(2024, 4, 1), date(2024, 4, 20)),
            ('2023 Corporate Return', clients[1].id, templates[2].id, 'High', date(2024, 1, 15), date(2024, 3, 15)),
            ('Q1 2024 Payroll Filing', clients[3].id, templates[3].id, 'High', date(2024, 4, 1), date(2024, 4, 30)),
            ('February 2024 Books', clients[5].id, templates[1].id, 'Medium', date(2024, 3, 1), date(2024, 3, 20))
        ]
        
        for proj_name, client_id, template_id, priority, start_date, due_date in sample_projects:
            project = Project(
                name=proj_name,
                client_id=client_id,
                start_date=start_date,
                due_date=due_date,
                priority=priority,
                firm_id=demo_firm.id,
                template_origin_id=template_id
            )
            db.session.add(project)
            db.session.flush()
            
            # Create tasks from template
            template = Template.query.get(template_id)
            for template_task in template.template_tasks:
                task_due_date = calculate_task_due_date(start_date, template_task)
                
                # Randomly assign some tasks as completed for demo
                import random
                statuses = ['Not Started', 'In Progress', 'Completed', 'Needs Review']
                status = random.choice(statuses) if random.random() > 0.3 else 'Completed'
                
                task = Task(
                    title=template_task.title,
                    description=template_task.description,
                    due_date=task_due_date,
                    priority=template_task.default_priority,
                    estimated_hours=template_task.estimated_hours,
                    actual_hours=random.uniform(0.5, template_task.estimated_hours * 1.2) if status == 'Completed' else 0,
                    status=status,
                    project_id=project.id,
                    assignee_id=template_task.default_assignee_id,
                    template_task_origin_id=template_task.id
                )
                db.session.add(task)
        
        db.session.commit()
        
        print(f"✅ Database initialized with enhanced demo data!")
        print(f"🔑 Access Code: {access_code}")
        print(f"🔒 Admin Password: admin123")
        print(f"👥 Users: {admin_user.name} (Admin), {senior_user.name} (Admin), {junior_user.name} (Member), {associate_user.name} (Member)")
        print(f"📋 Templates: {len(templates)} professional templates created")
        print(f"👔 Clients: {len(clients)} sample clients with contact information")
        print(f"📁 Projects: {len(sample_projects)} active projects with tasks")
        print(f"")
        print(f"🚀 Ready to explore the enhanced CPA WorkflowPilot!")
        print(f"Visit http://localhost:5000 and use access code: {access_code}")
        
        return access_code

if __name__ == '__main__':
    init_database()