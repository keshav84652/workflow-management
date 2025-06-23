"""
Flask Configuration Management
Environment-based configuration for CPA WorkflowPilot
"""

import os
import secrets


class BaseConfig:
    """Base configuration with common settings"""
    
    # Core Flask Settings
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    
    # Session Configuration for better persistence
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
    SESSION_COOKIE_NAME = 'cpa_workflow_session'
    
    # Database Configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.path.abspath('uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Allowed file extensions for uploads
    ALLOWED_EXTENSIONS = {
        'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 
        'ppt', 'pptx', 'csv', 'zip', 'rar', '7z', 'mp4', 'avi', 'mov', 'mp3', 'wav'
    }
    
    # AI Services Configuration
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = os.environ.get('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT')
    AZURE_DOCUMENT_INTELLIGENCE_KEY = os.environ.get('AZURE_DOCUMENT_INTELLIGENCE_KEY')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    
    # AI Services Auto-Detection
    @property
    def AI_SERVICES_AVAILABLE(self):
        """Auto-detect if AI services should be enabled based on available API keys"""
        return bool(
            (self.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and self.AZURE_DOCUMENT_INTELLIGENCE_KEY) or
            self.GEMINI_API_KEY
        )
    
    # Integration Configuration  
    ONEDRIVE_CLIENT_ID = os.environ.get('ONEDRIVE_CLIENT_ID')
    ONEDRIVE_CLIENT_SECRET = os.environ.get('ONEDRIVE_CLIENT_SECRET')
    SHAREPOINT_TENANT_ID = os.environ.get('SHAREPOINT_TENANT_ID')


class DevelopmentConfig(BaseConfig):
    """Development environment configuration"""
    
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.abspath("instance/workflow.db")}'
    
    # Development-specific settings
    SQLALCHEMY_ECHO = False  # Set to True for SQL query debugging


class ProductionConfig(BaseConfig):
    """Production environment configuration"""
    
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                             f'sqlite:///{os.path.abspath("instance/workflow.db")}'
    
    # Production-specific settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }


class TestingConfig(BaseConfig):
    """Testing environment configuration"""
    
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name=None):
    """Get configuration class based on environment"""
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    return config.get(config_name, config['default'])