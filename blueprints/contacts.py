"""
Contact management blueprint
"""

from flask import Blueprint

contacts_bp = Blueprint('contacts', __name__, url_prefix='/contacts')

# Routes will be implemented here