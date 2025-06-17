#!/usr/bin/env python3
"""
Script to view collected demo access email addresses
"""

import os
import sys
from datetime import datetime

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def view_demo_emails():
    """Display all collected demo access emails"""
    
    with app.app_context():
        try:
            # Query demo access requests
            result = db.session.execute(
                db.text("""
                    SELECT email, firm_access_code, ip_address, granted, 
                           created_at, last_activity, session_id
                    FROM demo_access_request 
                    ORDER BY created_at DESC
                """)
            ).fetchall()
            
            if not result:
                print("📭 No demo access requests found yet.")
                print("\nDemo access requests will appear here when users:")
                print("1. Enter their email on the login page")
                print("2. Use access code 'DEMO2024'")
                return
            
            print(f"📧 Found {len(result)} demo access requests:")
            print("=" * 80)
            
            for row in result:
                email, access_code, ip_address, granted, created_at, last_activity, session_id = row
                
                print(f"📧 Email: {email}")
                print(f"🔑 Access Code: {access_code}")
                print(f"🌐 IP Address: {ip_address or 'Unknown'}")
                print(f"✅ Access Granted: {'Yes' if granted else 'No'}")
                print(f"📅 First Access: {created_at}")
                if last_activity:
                    print(f"🕒 Last Activity: {last_activity}")
                if session_id:
                    print(f"🎫 Session ID: {session_id}")
                print("-" * 40)
            
            # Summary stats
            unique_emails = set(row[0] for row in result)
            granted_count = sum(1 for row in result if row[3])
            
            print(f"\n📊 Summary:")
            print(f"   • Total requests: {len(result)}")
            print(f"   • Unique emails: {len(unique_emails)}")
            print(f"   • Granted access: {granted_count}")
            
        except Exception as e:
            print(f"❌ Error accessing demo emails: {e}")
            print("\nThis might happen if:")
            print("1. The migration hasn't been run yet")
            print("2. No one has accessed the demo yet")

if __name__ == '__main__':
    print("📧 Demo Access Email Tracker")
    print("=" * 40)
    view_demo_emails()