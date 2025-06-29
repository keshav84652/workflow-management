"""
Dashboard module for CPA WorkflowPilot
Handles dashboard, views, and reporting functionality
"""

from .routes import dashboard_bp
from .views_routes import views_bp

def register_module(app):
    """Register the dashboard module with the Flask app"""
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(views_bp)