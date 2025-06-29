"""
Client module for CPA WorkflowPilot
Handles clients, contacts, and client portal functionality
"""

from .routes import clients_bp
from .contacts_routes import contacts_bp  
from .portal_routes import client_portal_bp

def register_module(app):
    """Register the client module with the Flask app"""
    app.register_blueprint(clients_bp)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(client_portal_bp)