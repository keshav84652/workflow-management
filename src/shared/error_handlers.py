"""
Global Error Handlers for CPA WorkflowPilot

Provides centralized exception handling to convert business exceptions
into proper HTTP responses with correct status codes.
"""

from flask import jsonify, request, flash, redirect, url_for
from src.shared.exceptions import (
    WorkflowPilotException, ValidationError, NotFoundError, 
    PermissionDeniedError, ConflictError, UnprocessableEntityError,
    BusinessLogicError, ExternalServiceError, InternalServerError,
    get_http_status_for_exception
)
import logging

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    """Register all error handlers with the Flask app"""
    
    @app.errorhandler(WorkflowPilotException)
    def handle_workflow_pilot_exception(error):
        """Handle all custom WorkflowPilot exceptions"""
        logger.error(f"Business exception: {error.__class__.__name__}: {error.message}")
        
        status_code = get_http_status_for_exception(error)
        
        # If this is an AJAX/JSON request, return JSON response
        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            return jsonify({
                'success': False,
                'error': error.__class__.__name__,
                'message': error.message,
                'details': error.details
            }), status_code
        
        # For HTML requests, flash the error and redirect based on exception type
        error_category = _get_flash_category_for_exception(error)
        flash(error.message, error_category)
        
        # Determine redirect based on the current endpoint and exception type
        redirect_url = _get_redirect_url_for_exception(error)
        return redirect(redirect_url)
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        """Handle validation errors specifically"""
        return handle_workflow_pilot_exception(error)
    
    @app.errorhandler(NotFoundError)
    def handle_not_found_error(error):
        """Handle not found errors specifically"""
        return handle_workflow_pilot_exception(error)
    
    @app.errorhandler(PermissionDeniedError)
    def handle_permission_denied_error(error):
        """Handle permission denied errors specifically"""
        return handle_workflow_pilot_exception(error)
    
    @app.errorhandler(500)
    def handle_internal_server_error(error):
        """Handle unexpected server errors"""
        logger.error(f"Internal server error: {str(error)}")
        
        if request.is_json:
            return jsonify({
                'success': False,
                'error': 'InternalServerError',
                'message': 'An unexpected error occurred. Please try again.',
                'details': None
            }), 500
        
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('dashboard.index'))


def _get_flash_category_for_exception(exception: WorkflowPilotException) -> str:
    """Get the appropriate flash message category for an exception"""
    if isinstance(exception, ValidationError):
        return 'warning'
    elif isinstance(exception, NotFoundError):
        return 'error'
    elif isinstance(exception, PermissionDeniedError):
        return 'error'
    elif isinstance(exception, ConflictError):
        return 'warning'
    elif isinstance(exception, (BusinessLogicError, UnprocessableEntityError)):
        return 'warning'
    elif isinstance(exception, ExternalServiceError):
        return 'error'
    else:
        return 'error'


def _get_redirect_url_for_exception(exception: WorkflowPilotException) -> str:
    """Get the appropriate redirect URL for an exception based on current context"""
    try:
        # Try to redirect to a contextually appropriate page
        if request.endpoint:
            endpoint_parts = request.endpoint.split('.')
            
            # For project-related endpoints
            if 'project' in endpoint_parts:
                if isinstance(exception, NotFoundError):
                    return url_for('projects.list_projects')
                else:
                    # For validation errors, stay on the same page
                    return request.url
            
            # For client-related endpoints
            elif 'client' in endpoint_parts:
                if isinstance(exception, NotFoundError):
                    return url_for('clients.list_clients')
                else:
                    return request.url
            
            # For auth-related endpoints
            elif 'auth' in endpoint_parts:
                if isinstance(exception, PermissionDeniedError):
                    return url_for('auth.login')
                else:
                    return request.url
        
        # Default fallback to dashboard
        return url_for('dashboard.index')
        
    except Exception:
        # If URL generation fails, return a safe default
        return '/'


def create_json_error_response(message: str, error_type: str = None, status_code: int = 400, details: str = None):
    """Create a standardized JSON error response"""
    response_data = {
        'success': False,
        'message': message
    }
    
    if error_type:
        response_data['error'] = error_type
    
    if details:
        response_data['details'] = details
    
    return jsonify(response_data), status_code


def create_success_response(data: dict = None, message: str = None):
    """Create a standardized JSON success response"""
    response_data = {'success': True}
    
    if message:
        response_data['message'] = message
    
    if data:
        response_data.update(data)
    
    return jsonify(response_data)
