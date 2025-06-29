"""
Document module for CPA WorkflowPilot
Handles documents, checklists, and AI analysis functionality
"""

from .routes import documents_bp
from .ai_routes import ai_bp

def register_module(app):
    """Register the document module with the Flask app"""
    app.register_blueprint(documents_bp)
    app.register_blueprint(ai_bp)