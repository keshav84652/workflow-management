# Core Utilities
# Blueprint registration and common utilities following OpenProject patterns

from flask import jsonify


def register_blueprints(app):
    """Register all application blueprints"""
    
    # Import blueprints
    from app.auth.routes import auth_bp
    from app.clients.routes import clients_bp
    from app.projects.routes import projects_bp
    from app.tasks.routes import tasks_bp
    from app.documents.routes import documents_bp
    from app.reports.routes import reports_bp
    from app.api.v1 import api_v1_bp
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(clients_bp, url_prefix='/clients')
    app.register_blueprint(projects_bp, url_prefix='/projects')
    app.register_blueprint(tasks_bp, url_prefix='/tasks')
    app.register_blueprint(documents_bp, url_prefix='/documents')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(api_v1_bp, url_prefix='/api/v1')


def setup_error_handlers(app):
    """Setup application error handlers"""
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': 'Forbidden'}), 403