#!/usr/bin/env python3
"""
Script to migrate User table schema and update existing users
"""

import os
import sys
from flask import Flask
from flask_bcrypt import Bcrypt
from sqlalchemy import text

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db_import import db
from config import get_config

def create_app():
    """Create Flask app for database operations"""
    app = Flask(__name__)
    config_class = get_config('default')
    app.config.from_object(config_class)
    
    # Initialize database
    db.init_app(app)
    
    return app

def migrate_user_schema():
    """Add email and password_hash columns to existing user table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if columns already exist
            result = db.session.execute(text("PRAGMA table_info(user)"))
            columns = [row[1] for row in result]
            
            print(f"Current user table columns: {columns}")
            
            # Add email column if it doesn't exist
            if 'email' not in columns:
                print("Adding email column...")
                db.session.execute(text("ALTER TABLE user ADD COLUMN email VARCHAR(255)"))
                print("✅ Email column added")
            else:
                print("Email column already exists")
            
            # Add password_hash column if it doesn't exist  
            if 'password_hash' not in columns:
                print("Adding password_hash column...")
                db.session.execute(text("ALTER TABLE user ADD COLUMN password_hash VARCHAR(255)"))
                print("✅ Password_hash column added")
            else:
                print("Password_hash column already exists")
            
            db.session.commit()
            return True
            
        except Exception as e:
            print(f"❌ Error migrating schema: {str(e)}")
            db.session.rollback()
            return False

def update_user_data():
    """Update existing users with email and password"""
    app = create_app()
    bcrypt = Bcrypt(app)
    
    with app.app_context():
        try:
            # Get all users and firms
            users_data = db.session.execute(text("""
                SELECT u.id, u.name, u.role, u.firm_id, u.email, u.password_hash,
                       f.name as firm_name
                FROM user u
                JOIN firm f ON u.firm_id = f.id
                ORDER BY f.name, u.name
            """)).fetchall()
            
            if not users_data:
                print("No users found in database")
                return True
            
            print(f"Found {len(users_data)} users to update")
            
            # Default password
            default_password = "admin123"
            password_hash = bcrypt.generate_password_hash(default_password).decode('utf-8')
            
            updated_count = 0
            
            for user_data in users_data:
                user_id = user_data[0]
                user_name = user_data[1]
                current_email = user_data[4]
                current_password_hash = user_data[5]
                firm_name = user_data[6]
                
                # Generate email if not exists
                if not current_email:
                    # Create email based on user name and firm
                    firm_name_clean = firm_name.lower().replace(' ', '').replace('&', 'and')
                    user_name_clean = user_name.lower().replace(' ', '').replace('.', '')
                    email = f"{user_name_clean}@{firm_name_clean}.com"
                    
                    # Check for existing email and make unique
                    counter = 1
                    original_email = email
                    while True:
                        existing = db.session.execute(text(
                            "SELECT id FROM user WHERE email = :email AND id != :user_id"
                        ), {'email': email, 'user_id': user_id}).fetchone()
                        
                        if not existing:
                            break
                        
                        email = f"{original_email.split('@')[0]}{counter}@{original_email.split('@')[1]}"
                        counter += 1
                    
                    # Update email
                    db.session.execute(text(
                        "UPDATE user SET email = :email WHERE id = :user_id"
                    ), {'email': email, 'user_id': user_id})
                    
                    print(f"  📧 Set email for {user_name}: {email}")
                
                # Set password hash if not exists
                if not current_password_hash:
                    db.session.execute(text(
                        "UPDATE user SET password_hash = :password_hash WHERE id = :user_id"
                    ), {'password_hash': password_hash, 'user_id': user_id})
                    
                    print(f"  🔑 Set password for {user_name}")
                
                updated_count += 1
            
            # Commit all changes
            db.session.commit()
            
            print(f"\n✅ Successfully updated {updated_count} users")
            print(f"Default password for all users: {default_password}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error updating user data: {str(e)}")
            db.session.rollback()
            return False

def list_login_credentials():
    """List all user login credentials"""
    app = create_app()
    
    with app.app_context():
        try:
            users_data = db.session.execute(text("""
                SELECT u.id, u.name, u.email, u.role, f.name as firm_name, f.id as firm_id
                FROM user u
                JOIN firm f ON u.firm_id = f.id
                ORDER BY f.name, u.name
            """)).fetchall()
            
            if not users_data:
                print("No users found in database")
                return
            
            print(f"\n📋 User Login Credentials (Total: {len(users_data)})")
            print("=" * 70)
            
            current_firm = None
            for user_data in users_data:
                user_id, user_name, email, role, firm_name, firm_id = user_data
                
                if current_firm != firm_name:
                    current_firm = firm_name
                    print(f"\n🏢 {firm_name} (ID: {firm_id})")
                    print("-" * 50)
                
                print(f"  👤 {user_name} ({role})")
                print(f"     📧 Email: {email}")
                print(f"     🔑 Password: admin123")
                print()
            
        except Exception as e:
            print(f"❌ Error listing credentials: {str(e)}")

if __name__ == "__main__":
    print("🔄 Migrating User table schema...")
    
    # Step 1: Migrate schema
    if not migrate_user_schema():
        print("❌ Schema migration failed!")
        sys.exit(1)
    
    print("\n🔄 Updating user data...")
    
    # Step 2: Update user data
    if not update_user_data():
        print("❌ User data update failed!")
        sys.exit(1)
    
    # Step 3: List credentials
    print("\n" + "="*70)
    list_login_credentials()
    print("="*70)
    print("\n🎉 Migration complete! You can now log in with the credentials above.")