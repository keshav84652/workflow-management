"""
Export Module Public Interface

This interface defines the public API for the export module.
Other modules MUST only interact with the export module through this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class IExportService(ABC):
    """Public interface for export operations"""
    
    @abstractmethod
    def export_projects_csv(self, firm_id: int) -> Any:
        """
        Export projects as CSV
        
        Args:
            firm_id: Firm ID
            
        Returns:
            Flask response with CSV file or error dictionary
        """
        pass
    
    @abstractmethod
    def export_projects_json(self, firm_id: int) -> Any:
        """
        Export projects as JSON
        
        Args:
            firm_id: Firm ID
            
        Returns:
            Flask response with JSON file or error dictionary
        """
        pass
    
    @abstractmethod
    def export_clients_csv(self, firm_id: int) -> Any:
        """
        Export clients as CSV
        
        Args:
            firm_id: Firm ID
            
        Returns:
            Flask response with CSV file or error dictionary
        """
        pass
    
    @abstractmethod
    def export_clients_json(self, firm_id: int) -> Any:
        """
        Export clients as JSON
        
        Args:
            firm_id: Firm ID
            
        Returns:
            Flask response with JSON file or error dictionary
        """
        pass
    
    @abstractmethod
    def export_tasks_csv(self, firm_id: int) -> Any:
        """
        Export tasks as CSV
        
        Args:
            firm_id: Firm ID
            
        Returns:
            Flask response with CSV file or error dictionary
        """
        pass
    
    @abstractmethod
    def export_tasks_json(self, firm_id: int) -> Any:
        """
        Export tasks as JSON
        
        Args:
            firm_id: Firm ID
            
        Returns:
            Flask response with JSON file or error dictionary
        """
        pass