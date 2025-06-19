#!/usr/bin/env python3
"""
Initialize New Database Structure
Create tables and sample data for refactored app
"""

import os
from app import create_app
from app.core.extensions import db
from app.auth.models import Firm, User, UserRole
from app.auth.services import FirmService

def init_database():
    """Initialize database with new structure"""
    
    # Create Flask app
    app = create_app('development')
    
    with app.app_context():
        # Drop and create all tables
        print("Creating database tables...")
        db.drop_all()
        db.create_all()
        
        # Create demo firm and users
        print("Creating demo firm...")
        firm_service = FirmService()
        result = firm_service.create_firm(
            name="Demo CPA Firm",
            access_code="DEMO2024",
            admin_user_name="Admin User"
        )
        
        if result.is_success():
            firm = result.data['firm']
            admin_user = result.data['admin_user']
            
            print(f"Created firm: {firm.name} (Access Code: {firm.access_code})")
            print(f"Created admin user: {admin_user.name}")
            
            # Create additional demo users
            demo_users = [
                {"name": "Sarah Manager", "role": UserRole.MANAGER, "title": "Senior Manager"},
                {"name": "John Senior", "role": UserRole.SENIOR, "title": "Senior Associate"},
                {"name": "Emily Staff", "role": UserRole.STAFF, "title": "Staff Accountant"},
                {"name": "Mike Partner", "role": UserRole.PARTNER, "title": "Managing Partner"}
            ]
            
            for user_data in demo_users:
                user = User(
                    name=user_data["name"],
                    role=user_data["role"],
                    title=user_data["title"],
                    firm_id=firm.id,
                    created_by_id=admin_user.id
                )
                db.session.add(user)
            
            db.session.commit()
            print(f"Created {len(demo_users)} additional demo users")
            
        else:
            print("Error creating demo firm:")
            for field, error in result.errors.items():
                print(f"  {field}: {error}")
        
        print("\nDatabase initialization complete!")
        print(f"Access the application at: http://localhost:5001")
        print(f"Use access code: DEMO2024")

if __name__ == '__main__':
    # Ensure instance directory exists
    os.makedirs('instance', exist_ok=True)
    init_database()