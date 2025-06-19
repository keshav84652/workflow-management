"""
Client portal blueprint
"""

from flask import Blueprint

client_portal_bp = Blueprint('client_portal', __name__, url_prefix='/client')

# Routes will be implemented here