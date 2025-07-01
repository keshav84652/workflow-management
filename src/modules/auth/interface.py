"""
Auth Module Public Interface

This interface defines the public API for the auth module.
Other modules MUST only interact with the auth module through this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class IAuthService(ABC):
    """Public interface for authentication and user management operations"""
    
    @abstractmethod
    def authenticate_firm(self, access_code: str, email: str) -> Dict[str, Any]:
        """
        Authenticate a firm using access code and email
        
        Args:
            access_code: The firm's access code
            email: User's email for tracking
            
        Returns:
            Authentication result dictionary
        """
        pass
    
    @abstractmethod
    def get_users_for_firm(self, firm_id: int) -> List[Dict[str, Any]]:
        """
        Get all users for a firm
        
        Args:
            firm_id: Firm ID
            
        Returns:
            List of user data dictionaries
        """
        pass
    
    @abstractmethod
    def get_user_by_id(self, user_id: int, firm_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user by ID with firm access check
        
        Args:
            user_id: User ID
            firm_id: Firm ID for access control
            
        Returns:
            User data dictionary or None if not found
        """
        pass
    
    @abstractmethod
    def create_user(self, user_data: Dict[str, Any], firm_id: int) -> Dict[str, Any]:
        """
        Create a new user for a firm
        
        Args:
            user_data: User information
            firm_id: Firm ID
            
        Returns:
            Result dictionary with success status and user data
        """
        pass
    
    @abstractmethod
    def update_user(self, user_id: int, user_data: Dict[str, Any], firm_id: int) -> Dict[str, Any]:
        """
        Update an existing user
        
        Args:
            user_id: User ID
            user_data: Updated user information
            firm_id: Firm ID for access control
            
        Returns:
            Result dictionary with success status
        """
        pass
    
    @abstractmethod
    def set_user_in_session(self, user_id: int, firm_id: int) -> Dict[str, Any]:
        """
        Set user context in session
        
        Args:
            user_id: User ID
            firm_id: Firm ID for validation
            
        Returns:
            Result dictionary with success status
        """
        pass


class IFirmService(ABC):
    """Public interface for firm management operations"""
    
    @abstractmethod
    def get_firm_by_id(self, firm_id: int) -> Optional[Dict[str, Any]]:
        """
        Get firm by ID
        
        Args:
            firm_id: Firm ID
            
        Returns:
            Firm data dictionary or None if not found
        """
        pass
    
    @abstractmethod
    def get_firm_by_access_code(self, access_code: str) -> Optional[Dict[str, Any]]:
        """
        Get firm by access code
        
        Args:
            access_code: Firm's access code
            
        Returns:
            Firm data dictionary or None if not found
        """
        pass
    
    @abstractmethod
    def create_firm(self, firm_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new firm
        
        Args:
            firm_data: Firm information
            
        Returns:
            Result dictionary with success status and firm data
        """
        pass
    
    @abstractmethod
    def update_firm(self, firm_id: int, firm_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing firm
        
        Args:
            firm_id: Firm ID
            firm_data: Updated firm information
            
        Returns:
            Result dictionary with success status
        """
        pass
    
    @abstractmethod
    def get_all_firms(self) -> List[Dict[str, Any]]:
        """
        Get all firms in the system (admin only)
        
        Returns:
            List of firm data dictionaries
        """
        pass
    
    @abstractmethod
    def toggle_firm_status(self, firm_id: int) -> Dict[str, Any]:
        """
        Toggle a firm's active status (admin only)
        
        Args:
            firm_id: Firm ID
            
        Returns:
            Result dictionary with success status
        """
        pass