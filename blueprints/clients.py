"""
Client management blueprint
"""

from flask import Blueprint

clients_bp = Blueprint('clients', __name__, url_prefix='/clients')

# Routes will be implemented here