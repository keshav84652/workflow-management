#!/usr/bin/env python3
"""
Initialize Flask-Migrate for the CPA WorkflowPilot application
"""

import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.app import create_app
from flask_migrate import init, migrate, upgrade
from src.shared.database.db_import import db

def initialize_migrations():
    """Initialize Flask-Migrate for the application"""
    app = create_app()
    
    with app.app_context():
        print("Initializing Flask-Migrate...")
        
        # Initialize migrations
        try:
            init()
            print("✅ Migrations initialized successfully")
        except Exception as e:
            print(f"Migration initialization failed: {e}")
            return False
        
        # Create initial migration
        try:
            migrate(message="Initial migration with dual status fields")
            print("✅ Initial migration created")
        except Exception as e:
            print(f"Initial migration creation failed: {e}")
            return False
        
        return True

if __name__ == '__main__':
    initialize_migrations()