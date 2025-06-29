"""
Authentication module for CPA WorkflowPilot
"""

from .routes import auth_bp

def register_module(app):
    """Register the auth module with the Flask app"""
    app.register_blueprint(auth_bp)