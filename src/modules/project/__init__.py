"""
Project module for CPA WorkflowPilot
Handles projects, tasks, and subtasks functionality
"""

from .routes import projects_bp
from .tasks_routes import tasks_bp
from .subtasks_routes import subtasks_bp

def register_module(app):
    """Register the project module with the Flask app"""
    app.register_blueprint(projects_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(subtasks_bp)