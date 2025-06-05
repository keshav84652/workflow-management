from app import app, db
from models import Firm, User, Template, TemplateTask
from utils import generate_access_code

def init_database():
    with app.app_context():
        db.create_all()
        
        demo_firm = Firm.query.filter_by(name='Demo CPA Firm').first()
        if not demo_firm:
            access_code = generate_access_code()
            demo_firm = Firm(name='Demo CPA Firm', access_code=access_code)
            db.session.add(demo_firm)
            db.session.flush()
            
            admin_user = User(
                name='John Admin',
                role='Admin',
                firm_id=demo_firm.id
            )
            db.session.add(admin_user)
            
            member_user = User(
                name='Jane Member',
                role='Member',
                firm_id=demo_firm.id
            )
            db.session.add(member_user)
            db.session.flush()
            
            tax_template = Template(
                name='1040 Tax Preparation',
                description='Individual tax return preparation workflow',
                firm_id=demo_firm.id
            )
            db.session.add(tax_template)
            db.session.flush()
            
            tax_tasks = [
                ('Client organizer review', 'Review and verify client tax organizer', None),
                ('Gather supporting documents', 'Collect W-2s, 1099s, receipts, etc.', None),
                ('Prepare tax return', 'Complete federal and state tax returns', None),
                ('Review and quality check', 'Partner review of completed return', None),
                ('Client review meeting', 'Present return to client for approval', None),
                ('File returns', 'E-file federal and state returns', None),
                ('Quarterly estimated payments', 'Calculate and send quarterly vouchers', 'quarterly:last_biz_day')
            ]
            
            for i, (title, desc, recurrence) in enumerate(tax_tasks):
                task = TemplateTask(
                    title=title,
                    description=desc,
                    order=i,
                    recurrence_rule=recurrence,
                    template_id=tax_template.id,
                    default_assignee_id=member_user.id if i < 3 else admin_user.id
                )
                db.session.add(task)
            
            bookkeeping_template = Template(
                name='Monthly Bookkeeping',
                description='Monthly bookkeeping and financial reporting',
                firm_id=demo_firm.id
            )
            db.session.add(bookkeeping_template)
            db.session.flush()
            
            bookkeeping_tasks = [
                ('Import bank transactions', 'Download and import monthly bank data', 'monthly:1'),
                ('Categorize transactions', 'Review and categorize all transactions', 'monthly:5'),
                ('Reconcile accounts', 'Reconcile bank and credit card accounts', 'monthly:10'),
                ('Generate reports', 'Create P&L and Balance Sheet', 'monthly:15'),
                ('Client review', 'Send reports to client for review', 'monthly:18'),
                ('Sales tax filing', 'Prepare and file monthly sales tax', 'monthly:last_biz_day')
            ]
            
            for i, (title, desc, recurrence) in enumerate(bookkeeping_tasks):
                task = TemplateTask(
                    title=title,
                    description=desc,
                    order=i,
                    recurrence_rule=recurrence,
                    template_id=bookkeeping_template.id,
                    default_assignee_id=member_user.id
                )
                db.session.add(task)
            
            db.session.commit()
            
            print(f"Database initialized with demo data!")
            print(f"Demo Firm Access Code: {access_code}")
            print(f"Admin Password: admin123 (or set ADMIN_PASSWORD env var)")
            print(f"Users created: {admin_user.name} (Admin), {member_user.name} (Member)")
            print(f"Templates created: {tax_template.name}, {bookkeeping_template.name}")
        else:
            print("Database already initialized")

if __name__ == '__main__':
    init_database()