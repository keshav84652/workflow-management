#!/usr/bin/env python3
"""
Database Backup Script for CPA WorkflowPilot
Creates timestamped backups to prevent data loss during development.
"""

import os
import shutil
from datetime import datetime

def backup_database():
    """Create a timestamped backup of the database"""
    
    # Paths
    db_path = 'instance/workflow.db'
    backup_dir = 'instance/backups'
    
    # Create backup directory if it doesn't exist
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'workflow_backup_{timestamp}.db')
    
    try:
        if os.path.exists(db_path):
            # Copy database file
            shutil.copy2(db_path, backup_path)
            
            # Get file size for verification
            size = os.path.getsize(backup_path)
            size_kb = size / 1024
            
            print(f"✅ Database backed up successfully!")
            print(f"   Source: {db_path}")
            print(f"   Backup: {backup_path}")
            print(f"   Size: {size_kb:.1f} KB")
            
            return backup_path
        else:
            print(f"❌ Database file not found: {db_path}")
            return None
            
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return None

def list_backups():
    """List all available backups"""
    backup_dir = 'instance/backups'
    
    if not os.path.exists(backup_dir):
        print("No backups directory found")
        return []
    
    backups = []
    for file in os.listdir(backup_dir):
        if file.startswith('workflow_backup_') and file.endswith('.db'):
            backup_path = os.path.join(backup_dir, file)
            size = os.path.getsize(backup_path) / 1024
            mtime = os.path.getmtime(backup_path)
            timestamp = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            backups.append({
                'file': file,
                'path': backup_path,
                'size_kb': size,
                'timestamp': timestamp
            })
    
    # Sort by modification time (newest first)
    backups.sort(key=lambda x: x['timestamp'], reverse=True)
    
    if backups:
        print(f"Available backups ({len(backups)}):")
        for backup in backups:
            print(f"  - {backup['file']} ({backup['size_kb']:.1f} KB) - {backup['timestamp']}")
    else:
        print("No backups found")
    
    return backups

def restore_backup(backup_file):
    """Restore database from a backup file"""
    
    db_path = 'instance/workflow.db'
    backup_path = os.path.join('instance/backups', backup_file)
    
    if not os.path.exists(backup_path):
        print(f"❌ Backup file not found: {backup_path}")
        return False
    
    try:
        # Create backup of current database first
        if os.path.exists(db_path):
            current_backup = backup_database()
            print(f"Current database backed up as: {current_backup}")
        
        # Restore from backup
        shutil.copy2(backup_path, db_path)
        
        print(f"✅ Database restored successfully!")
        print(f"   Restored from: {backup_path}")
        print(f"   To: {db_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Restore failed: {e}")
        return False

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) == 1:
        # Default action: create backup
        backup_database()
    elif sys.argv[1] == 'list':
        list_backups()
    elif sys.argv[1] == 'restore' and len(sys.argv) == 3:
        restore_backup(sys.argv[2])
    else:
        print("Usage:")
        print("  python backup_database.py           # Create backup")
        print("  python backup_database.py list      # List backups")
        print("  python backup_database.py restore <backup_file>  # Restore backup")