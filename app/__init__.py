# Flask Application Factory
# Inspired by OpenProject's modular architecture and Plane's app organization

from flask import Flask
from flask_migrate import Migrate

from app.config.base import Config
from app.core.extensions import db, migrate
from app.core.utils import register_blueprints, setup_error_handlers


def create_app(config_name='development'):
    """Application factory pattern following OpenProject architecture"""
    app = Flask(__name__)
    
    # Load configuration
    config_class = Config.get_config(config_name)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Register blueprints (modular architecture)
    register_blueprints(app)
    
    # Setup error handlers
    setup_error_handlers(app)
    
    return app