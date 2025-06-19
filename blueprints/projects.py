"""
Project and template management blueprint
"""

from flask import Blueprint

projects_bp = Blueprint('projects', __name__, url_prefix='/projects')

# Routes will be implemented here
# Placeholder for now to test blueprint structure