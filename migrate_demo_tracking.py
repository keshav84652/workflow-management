#!/usr/bin/env python3
"""
Migration script to add demo tracking and client checklist access tokens
"""

import os
import sys
from datetime import datetime

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import DocumentChecklist

def migrate_database():
    """Add new columns and tables for production deployment"""
    
    with app.app_context():
        # Create all tables (including new ones from models.py)
        db.create_all()
        
        # Add new columns to existing table using raw SQL
        try:
            # Check if access_token column exists
            result = db.session.execute(db.text("PRAGMA table_info(document_checklist)")).fetchall()
            columns = [row[1] for row in result]  # row[1] is column name
            
            if 'access_token' not in columns:
                print("Adding new columns to document_checklist table...")
                db.session.execute(db.text("ALTER TABLE document_checklist ADD COLUMN access_token VARCHAR(255)"))
                db.session.execute(db.text("ALTER TABLE document_checklist ADD COLUMN token_expires_at DATETIME"))
                db.session.execute(db.text("ALTER TABLE document_checklist ADD COLUMN client_email VARCHAR(255)"))
                db.session.execute(db.text("ALTER TABLE document_checklist ADD COLUMN token_access_count INTEGER DEFAULT 0"))
                db.session.execute(db.text("ALTER TABLE document_checklist ADD COLUMN token_last_accessed DATETIME"))
                db.session.commit()
                print("✅ New columns added successfully!")
            else:
                print("✅ Columns already exist, skipping column creation")
            
        except Exception as e:
            print(f"Warning during column creation: {e}")
        
        # Add access tokens to existing checklists that don't have them
        checklists_updated = 0
        try:
            checklists = DocumentChecklist.query.filter_by(access_token=None).all()
            
            for checklist in checklists:
                try:
                    checklist.generate_access_token()
                    checklist.client_email = checklist.client.email if checklist.client.email else ""
                    # Set 30-day expiration
                    from datetime import timedelta
                    checklist.token_expires_at = datetime.utcnow() + timedelta(days=30)
                    checklists_updated += 1
                except Exception as e:
                    print(f"Warning: Could not generate token for checklist {checklist.id}: {e}")
                    continue
        except Exception as e:
            print(f"Warning during token generation: {e}")
        
        # Commit all changes
        try:
            db.session.commit()
            print("✅ Database migration completed successfully!")
            print(f"📊 Added access tokens to {checklists_updated} existing checklists")
            
            # Show summary of new tables
            print("\n📋 New tables added:")
            print("   • demo_access_request - Track demo access with email collection")
            print("   • client_checklist_access - Secure token-based checklist access")
            
            print("\n🔗 New checklist features:")
            print("   • Public client access URLs with secure tokens")
            print("   • Access tracking and expiration")
            print("   • Revoke/regenerate link functionality")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {e}")
            return False
            
    return True

if __name__ == '__main__':
    print("🚀 Starting database migration for production deployment...")
    print("⚠️  This will add new tables and columns to your database.")
    
    confirm = input("Continue? (y/N): ").lower().strip()
    if confirm != 'y':
        print("Migration cancelled.")
        sys.exit(0)
    
    if migrate_database():
        print("\n✅ Migration complete! Your application is ready for production deployment.")
        print("\n🔧 Next steps:")
        print("   1. Test the email collection on login")
        print("   2. Create a checklist and test the Share functionality")
        print("   3. Test the public client access URL")
        print("   4. Deploy to Replit")
    else:
        print("\n❌ Migration failed! Check the error messages above.")
        sys.exit(1)