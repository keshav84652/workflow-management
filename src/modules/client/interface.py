"""
Client Module Public Interface

This interface defines the public API for the client module.
Other modules MUST only interact with the client module through this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class IClientService(ABC):
    """Public interface for client-related operations"""
    
    @abstractmethod
    def get_client_by_id(self, client_id: int, firm_id: int) -> Optional[Dict[str, Any]]:
        """
        Get client by ID with firm access check
        
        Args:
            client_id: Client ID
            firm_id: Firm ID for access control
            
        Returns:
            Client data dictionary or None if not found
        """
        pass
    
    @abstractmethod
    def get_clients_for_firm(self, firm_id: int) -> List[Dict[str, Any]]:
        """
        Get all clients for a firm
        
        Args:
            firm_id: Firm ID
            
        Returns:
            List of client data dictionaries
        """
        pass
    
    @abstractmethod
    def get_active_clients_by_firm(self, firm_id: int) -> List[Dict[str, Any]]:
        """
        Get active clients for a firm
        
        Args:
            firm_id: Firm ID
            
        Returns:
            List of active client data dictionaries
        """
        pass
    
    @abstractmethod
    def create_client(self, client_data: Dict[str, Any], firm_id: int, user_id: int) -> Dict[str, Any]:
        """
        Create a new client
        
        Args:
            client_data: Client information
            firm_id: Firm ID
            user_id: User ID for audit trail
            
        Returns:
            Result dictionary with success status and client data
        """
        pass
    
    @abstractmethod
    def update_client(self, client_id: int, client_data: Dict[str, Any], firm_id: int, user_id: int) -> Dict[str, Any]:
        """
        Update an existing client
        
        Args:
            client_id: Client ID
            client_data: Updated client information
            firm_id: Firm ID for access control
            user_id: User ID for audit trail
            
        Returns:
            Result dictionary with success status
        """
        pass
    
    @abstractmethod
    def search_clients(self, firm_id: int, query: str, limit: int = 20) -> Dict[str, Any]:
        """
        Search clients by name or other criteria
        
        Args:
            firm_id: Firm ID
            query: Search query
            limit: Maximum number of results
            
        Returns:
            Search results dictionary
        """
        pass
    
    @abstractmethod
    def get_client_statistics(self, firm_id: int) -> Dict[str, Any]:
        """
        Get client statistics for a firm
        
        Args:
            firm_id: Firm ID
            
        Returns:
            Statistics dictionary
        """
        pass