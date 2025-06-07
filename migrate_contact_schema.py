#!/usr/bin/env python3

"""
Migration script to add missing columns to the contact table
"""

import sqlite3
import sys
import os

def migrate_contact_table():
    db_path = 'instance/workflow.db'
    
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current schema
        cursor.execute('PRAGMA table_info(contact)')
        columns = cursor.fetchall()
        existing_columns = [col[1] for col in columns]
        
        print(f"Current contact table columns: {existing_columns}")
        
        # Add missing columns
        missing_columns = []
        
        if 'company' not in existing_columns:
            print("Adding 'company' column...")
            cursor.execute('ALTER TABLE contact ADD COLUMN company VARCHAR(200)')
            missing_columns.append('company')
        
        if 'address' not in existing_columns:
            print("Adding 'address' column...")
            cursor.execute('ALTER TABLE contact ADD COLUMN address TEXT')
            missing_columns.append('address')
        
        # Commit changes
        conn.commit()
        conn.close()
        
        if missing_columns:
            print(f"Successfully added columns: {missing_columns}")
        else:
            print("No missing columns found, schema is up to date")
        
        return True
        
    except Exception as e:
        print(f"Error migrating database: {e}")
        return False

if __name__ == '__main__':
    print("Migrating contact table schema...")
    success = migrate_contact_table()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
        sys.exit(1)