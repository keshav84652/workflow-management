"""
Base Service Infrastructure for CPA WorkflowPilot

Provides common service patterns and utilities to eliminate code duplication
and standardize service layer architecture.
"""

from typing import Dict, Any, Optional, Callable
from flask import session, request
from core.db_import import db


class DatabaseService:
    """
    Centralized database operations and transaction management
    """
    
    @staticmethod
    def get_db():
        """Get the database instance"""
        return db
    
    @staticmethod
    def execute_with_transaction(operation: Callable[[], Any]) -> Dict[str, Any]:
        """
        Execute operation with proper transaction handling
        
        Args:
            operation: Callable that performs database operations
            
        Returns:
            Dict with success status and result/error message
        """
        try:
            result = operation()
            db.session.commit()
            return {
                'success': True,
                'result': result,
                'message': 'Operation completed successfully'
            }
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e),
                'message': f'Operation failed: {str(e)}'
            }


class SessionService:
    """
    Centralized session management and access control
    """
    
    @staticmethod
    def get_current_firm_id() -> int:
        """
        Get current user's firm ID from session
        
        Returns:
            int: Current firm ID
            
        Raises:
            ValueError: If no firm_id in session or user not authenticated
        """
        if 'firm_id' not in session:
            available_keys = list(session.keys())
            raise ValueError(f"No firm_id in session. Available session keys: {available_keys}. "
                           f"User may need to log in again. Request path: {request.path}")
        return session['firm_id']
    
    @staticmethod
    def get_current_user_id() -> int:
        """
        Get current user ID from session
        
        Returns:
            int: Current user ID
            
        Raises:
            ValueError: If no user_id in session or user not authenticated
        """
        if 'user_id' not in session:
            available_keys = list(session.keys())
            raise ValueError(f"No user_id in session. Available session keys: {available_keys}. "
                           f"User may need to log in again. Request path: {request.path}")
        return session['user_id']
    
    @staticmethod
    def require_firm_access(firm_id: int) -> bool:
        """
        Verify current user has access to the specified firm
        
        Args:
            firm_id: Firm ID to check access for
            
        Returns:
            bool: True if access granted
            
        Raises:
            ValueError: If access denied or user not authenticated
        """
        current_firm_id = SessionService.get_current_firm_id()
        if current_firm_id != firm_id:
            raise ValueError(f"Access denied. User belongs to firm {current_firm_id}, "
                           f"but tried to access firm {firm_id}")
        return True
    
    @staticmethod
    def get_current_context() -> Dict[str, int]:
        """
        Get current user and firm context
        
        Returns:
            Dict with user_id and firm_id
        """
        return {
            'user_id': SessionService.get_current_user_id(),
            'firm_id': SessionService.get_current_firm_id()
        }


class ValidationService:
    """
    Common validation patterns for services
    """
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: list) -> Dict[str, Any]:
        """
        Validate that required fields are present and not empty
        
        Args:
            data: Dictionary to validate
            required_fields: List of required field names
            
        Returns:
            Dict with validation result
        """
        missing_fields = []
        empty_fields = []
        
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
            elif not data[field] or (isinstance(data[field], str) and not data[field].strip()):
                empty_fields.append(field)
        
        if missing_fields or empty_fields:
            errors = []
            if missing_fields:
                errors.append(f"Missing required fields: {', '.join(missing_fields)}")
            if empty_fields:
                errors.append(f"Empty required fields: {', '.join(empty_fields)}")
            
            return {
                'valid': False,
                'errors': errors,
                'message': '; '.join(errors)
            }
        
        return {'valid': True, 'message': 'Validation passed'}
    
    @staticmethod
    def validate_positive_integer(value: Any, field_name: str) -> Dict[str, Any]:
        """
        Validate that value is a positive integer
        
        Args:
            value: Value to validate
            field_name: Name of the field for error messages
            
        Returns:
            Dict with validation result
        """
        try:
            int_value = int(value)
            if int_value <= 0:
                return {
                    'valid': False,
                    'message': f'{field_name} must be a positive integer, got {value}'
                }
            return {'valid': True, 'value': int_value}
        except (ValueError, TypeError):
            return {
                'valid': False,
                'message': f'{field_name} must be a valid integer, got {value}'
            }


class BaseService:
    """
    Base class for all services with common functionality
    """
    
    def __init__(self):
        self.db = DatabaseService.get_db()
        self.session_service = SessionService()
        self.validation_service = ValidationService()
    
    def get_current_context(self) -> Dict[str, int]:
        """Get current user and firm context"""
        return SessionService.get_current_context()
    
    def execute_with_transaction(self, operation: Callable[[], Any]) -> Dict[str, Any]:
        """Execute operation with transaction handling"""
        return DatabaseService.execute_with_transaction(operation)
    
    def validate_firm_access(self, firm_id: int) -> bool:
        """Validate current user has access to firm"""
        return SessionService.require_firm_access(firm_id)


__all__ = ['DatabaseService', 'SessionService', 'ValidationService', 'BaseService']