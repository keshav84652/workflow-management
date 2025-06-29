"""
Export Module for CPA WorkflowPilot
Handles data export functionality for various formats.
"""

from .routes import export_bp

def register_module(app):
    """Register the export module with the Flask app"""
    app.register_blueprint(export_bp)