#!/usr/bin/env python3
"""
Script to update existing users with default password and email addresses
"""

import os
import sys
from flask import Flask
from flask_bcrypt import Bcrypt
from sqlalchemy import text

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db_import import db
from models.auth import User, Firm
from config import get_config

def create_app():
    """Create Flask app for database operations"""
    app = Flask(__name__)
    config_class = get_config('default')
    app.config.from_object(config_class)
    
    # Initialize database
    db.init_app(app)
    
    return app

def update_user_passwords():
    """Update existing users with default password and email addresses"""
    app = create_app()
    bcrypt = Bcrypt(app)
    
    with app.app_context():
        try:
            # Get all users
            users = User.query.all()
            
            if not users:
                print("No users found in database")
                return
            
            print(f"Found {len(users)} users to update")
            
            # Default password
            default_password = "admin123"
            password_hash = bcrypt.generate_password_hash(default_password).decode('utf-8')
            
            updated_count = 0
            
            for user in users:
                # Generate email if not exists
                if not hasattr(user, 'email') or not user.email:
                    # Create email based on user name and firm
                    firm = Firm.query.get(user.firm_id)
                    firm_name = firm.name.lower().replace(' ', '') if firm else 'firm'
                    user_name = user.name.lower().replace(' ', '')
                    email = f"{user_name}@{firm_name}.com"
                    
                    # Make sure email is unique
                    counter = 1
                    original_email = email
                    while User.query.filter_by(email=email).first():
                        email = f"{original_email.split('@')[0]}{counter}@{original_email.split('@')[1]}"
                        counter += 1
                    
                    user.email = email
                
                # Set password hash
                user.password_hash = password_hash
                
                print(f"Updated user: {user.name} (ID: {user.id}) - Email: {user.email}")
                updated_count += 1
            
            # Commit changes
            db.session.commit()
            
            print(f"\n✅ Successfully updated {updated_count} users")
            print(f"Default password for all users: {default_password}")
            print("\nUsers can now log in with their email addresses and the default password")
            
        except Exception as e:
            print(f"❌ Error updating users: {str(e)}")
            db.session.rollback()
            return False
    
    return True

def list_users():
    """List all users with their login credentials"""
    app = create_app()
    
    with app.app_context():
        try:
            # Query users with their firm information
            users = db.session.execute(
                text("""
                    SELECT u.id, u.name, u.email, u.role, f.name as firm_name, f.id as firm_id
                    FROM user u
                    JOIN firm f ON u.firm_id = f.id
                    ORDER BY f.name, u.name
                """)
            ).fetchall()
            
            if not users:
                print("No users found in database")
                return
            
            print(f"\n📋 User Login Credentials (Total: {len(users)})")
            print("=" * 70)
            
            current_firm = None
            for user in users:
                if current_firm != user.firm_name:
                    current_firm = user.firm_name
                    print(f"\n🏢 {current_firm} (ID: {user.firm_id})")
                    print("-" * 50)
                
                print(f"  👤 {user.name} ({user.role})")
                print(f"     📧 Email: {user.email}")
                print(f"     🔑 Password: admin123")
                print()
            
        except Exception as e:
            print(f"❌ Error listing users: {str(e)}")

if __name__ == "__main__":
    print("🔄 Updating existing users with default password...")
    
    if update_user_passwords():
        print("\n" + "="*70)
        list_users()
        print("="*70)
        print("\n🎉 Update complete! You can now log in with any of the above credentials.")
    else:
        print("\n❌ Update failed!")