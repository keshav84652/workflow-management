"""
Admin module for CPA WorkflowPilot
Handles administration, user management, and templates
"""

from .routes import admin_bp
from .users_routes import users_bp

def register_module(app):
    """Register the admin module with the Flask app"""
    app.register_blueprint(admin_bp)
    app.register_blueprint(users_bp)