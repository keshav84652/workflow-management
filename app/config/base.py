# Configuration Management
# Environment-based configuration inspired by Vikunja's config patterns

import os
import secrets


class BaseConfig:
    """Base configuration with common settings"""
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload configuration
    UPLOAD_FOLDER = os.path.abspath('uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {
        'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 
        'xls', 'xlsx', 'ppt', 'pptx', 'csv', 'zip', 'rar', '7z'
    }
    
    # API Configuration
    API_VERSION = 'v1'
    API_PREFIX = f'/api/{API_VERSION}'
    
    # Integration Configuration
    ONEDRIVE_CLIENT_ID = os.environ.get('ONEDRIVE_CLIENT_ID')
    ONEDRIVE_CLIENT_SECRET = os.environ.get('ONEDRIVE_CLIENT_SECRET')
    SHAREPOINT_TENANT_ID = os.environ.get('SHAREPOINT_TENANT_ID')


class DevelopmentConfig(BaseConfig):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.abspath("instance/workflow.db")}'
    
    # Development-specific settings
    SQLALCHEMY_ECHO = False  # Set to True for SQL debugging


class ProductionConfig(BaseConfig):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                             f'sqlite:///{os.path.abspath("instance/workflow.db")}'
    
    # Production-specific settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }


class TestConfig(BaseConfig):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


class Config:
    """Configuration factory"""
    
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestConfig,
        'default': DevelopmentConfig
    }
    
    @classmethod
    def get_config(cls, config_name):
        """Get configuration class by name"""
        return cls.configs.get(config_name, cls.configs['default'])