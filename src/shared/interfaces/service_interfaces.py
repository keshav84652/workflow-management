"""
Service Interfaces for CPA WorkflowPilot
Defines contracts for cross-module communication to reduce coupling.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class IProjectService(ABC):
    """Interface for project-related operations"""
    
    @abstractmethod
    def get_projects_by_firm(self, firm_id: int, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get projects for a firm with optional filtering"""
        pass
    
    @abstractmethod
    def get_project_statistics(self, firm_id: int) -> Dict[str, Any]:
        """Get project statistics for a firm"""
        pass


class ITaskService(ABC):
    """Interface for task-related operations"""
    
    @abstractmethod
    def get_tasks_by_firm(self, firm_id: int, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get tasks for a firm with optional filtering"""
        pass
    
    @abstractmethod
    def get_task_statistics(self, firm_id: int) -> Dict[str, Any]:
        """Get task statistics for a firm"""
        pass


class IAuthService(ABC):
    """Interface for authentication and user management operations"""
    
    @abstractmethod
    def authenticate_firm(self, access_code: str, email: str) -> Dict[str, Any]:
        """Authenticate a firm using access code"""
        pass
    
    @abstractmethod
    def get_users_by_firm(self, firm_id: int) -> List[Dict[str, Any]]:
        """Get all users for a firm as DTOs"""
        pass
    
    @abstractmethod
    def get_user_by_id_dto(self, user_id: int, firm_id: int = None) -> Dict[str, Any]:
        """Get user by ID as DTO with optional firm validation"""
        pass
    
    @abstractmethod
    def create_user(self, name: str, email: str, role: str, firm_id: int, password: str = None) -> Dict[str, Any]:
        """Create a new user"""
        pass


class IClientService(ABC):
    """Interface for client-related operations"""
    
    @abstractmethod
    def get_clients_by_firm(self, firm_id: int) -> List[Any]:
        """Get clients for a firm (raw objects)"""
        pass
    
    @abstractmethod
    def get_clients_for_api(self, firm_id: int) -> Dict[str, Any]:
        """Get clients for a firm formatted for API response"""
        pass
    
    @abstractmethod
    def get_client_statistics(self, firm_id: int) -> Dict[str, Any]:
        """Get client statistics for a firm"""
        pass


class IDataAggregatorService(ABC):
    """Interface for services that aggregate data from multiple sources"""
    
    @abstractmethod
    def get_dashboard_data(self, firm_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get aggregated dashboard data"""
        pass
    
    @abstractmethod
    def get_kanban_data(self, firm_id: int, **filters) -> Dict[str, Any]:
        """Get kanban board data with filtering"""
        pass
    
    @abstractmethod
    def get_calendar_data(self, firm_id: int, year: int, month: int) -> Dict[str, Any]:
        """Get calendar data for specified time period"""
        pass


class ServiceRegistry:
    """Registry for service implementations to enable dependency injection"""
    
    _services: Dict[str, Any] = {}
    
    @classmethod
    def register(cls, interface_name: str, implementation: Any) -> None:
        """Register a service implementation"""
        cls._services[interface_name] = implementation
    
    @classmethod
    def get(cls, interface_name: str) -> Any:
        """Get a registered service implementation"""
        return cls._services.get(interface_name)
    
    @classmethod
    def get_project_service(cls) -> Optional[IProjectService]:
        """Get project service implementation"""
        return cls.get('project_service')
    
    @classmethod
    def get_task_service(cls) -> Optional[ITaskService]:
        """Get task service implementation"""
        return cls.get('task_service')
    
    @classmethod
    def get_client_service(cls) -> Optional[IClientService]:
        """Get client service implementation"""
        return cls.get('client_service')
    
    @classmethod
    def get_data_aggregator(cls) -> Optional[IDataAggregatorService]:
        """Get data aggregator service implementation"""
        return cls.get('data_aggregator')
    
    @classmethod
    def get_export_service(cls):
        """Get export service implementation"""
        return cls.get('export_service')