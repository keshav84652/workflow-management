"""
Custom Exceptions for CPA WorkflowPilot

Provides specific exception classes that can be caught and handled appropriately
by the presentation layer to return proper HTTP status codes and error responses.

This replaces the anti-pattern of returning {'success': False, 'message': '...'} 
dictionaries from services.
"""

class WorkflowPilotException(Exception):
    """Base exception for all WorkflowPilot-specific errors"""
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class ValidationError(WorkflowPilotException):
    """
    Raised when input validation fails
    HTTP Status: 400 Bad Request
    """
    pass


class NotFoundError(WorkflowPilotException):
    """
    Raised when a requested resource is not found
    HTTP Status: 404 Not Found
    """
    pass


class PermissionDeniedError(WorkflowPilotException):
    """
    Raised when user lacks permission to access or modify a resource
    HTTP Status: 403 Forbidden
    """
    pass


class ConflictError(WorkflowPilotException):
    """
    Raised when a request conflicts with current state
    (e.g., trying to create a duplicate resource)
    HTTP Status: 409 Conflict
    """
    pass


class UnprocessableEntityError(WorkflowPilotException):
    """
    Raised when request is well-formed but semantically incorrect
    HTTP Status: 422 Unprocessable Entity
    """
    pass


class BusinessLogicError(WorkflowPilotException):
    """
    Raised when business rules are violated
    HTTP Status: 422 Unprocessable Entity
    """
    pass


class ExternalServiceError(WorkflowPilotException):
    """
    Raised when an external service (database, API, etc.) fails
    HTTP Status: 503 Service Unavailable
    """
    pass


class InternalServerError(WorkflowPilotException):
    """
    Raised for unexpected internal errors
    HTTP Status: 500 Internal Server Error
    """
    pass


# HTTP Status Code Mapping
EXCEPTION_STATUS_MAP = {
    ValidationError: 400,
    NotFoundError: 404,
    PermissionDeniedError: 403,
    ConflictError: 409,
    UnprocessableEntityError: 422,
    BusinessLogicError: 422,
    ExternalServiceError: 503,
    InternalServerError: 500,
}


def get_http_status_for_exception(exception: Exception) -> int:
    """
    Get the appropriate HTTP status code for an exception
    
    Args:
        exception: The exception to map
        
    Returns:
        HTTP status code
    """
    return EXCEPTION_STATUS_MAP.get(type(exception), 500)
