"""
Core infrastructure module for CPA WorkflowPilot
"""

import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from .redis_client import RedisClient, init_redis, redis_client

# Initialize Flask extensions
db = SQLAlchemy()
migrate = Migrate()

def create_directories(app):
    """Create necessary directories for the application"""
    os.makedirs('instance', exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename, allowed_extensions):
    """Check if uploaded file has allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

__all__ = [
    'RedisClient', 'init_redis', 'redis_client',
    'db', 'migrate', 'create_directories', 'allowed_file'
]