"""
Dependency Injection Container

This container manages service instances and their dependencies to enable
proper module decoupling following the interface-based architecture.
"""

from typing import Dict, Type, Any, TypeVar
from abc import ABC

T = TypeVar('T')


class ServiceContainer:
    """Dependency injection container for managing service instances"""
    
    def __init__(self):
        self._interfaces: Dict[Type, Type] = {}
        self._instances: Dict[Type, Any] = {}
        self._singletons: Dict[Type, Any] = {}
    
    def register(self, interface: Type[T], implementation: Type[T], singleton: bool = False) -> None:
        """
        Register a service implementation for an interface
        
        Args:
            interface: The interface/abstract class
            implementation: The concrete implementation class
            singleton: Whether to reuse the same instance (default: False)
        """
        self._interfaces[interface] = implementation
        if singleton:
            self._singletons[interface] = None
    
    def get(self, interface: Type[T]) -> T:
        """
        Get an instance of a service by its interface
        
        Args:
            interface: The interface/abstract class
            
        Returns:
            Instance of the registered implementation
            
        Raises:
            ValueError: If interface is not registered
        """
        if interface not in self._interfaces:
            raise ValueError(f"Interface {interface.__name__} is not registered")
        
        # Check if it's registered as singleton and already instantiated
        if interface in self._singletons:
            if self._singletons[interface] is None:
                self._singletons[interface] = self._create_instance(interface)
            return self._singletons[interface]
        
        # Create new instance each time
        return self._create_instance(interface)
    
    def _create_instance(self, interface: Type[T]) -> T:
        """
        Create an instance of a service with proper dependency injection
        
        Args:
            interface: The interface to create an instance for
            
        Returns:
            Instance with dependencies injected
        """
        implementation_class = self._interfaces[interface]
        
        # Special handling for services that need repository injection
        if hasattr(implementation_class, '__name__'):
            class_name = implementation_class.__name__
            
            # Inject repositories for services that need them
            if class_name == 'ProjectService':
                from src.modules.project.repository import ProjectRepository
                return implementation_class(project_repository=ProjectRepository())
            elif class_name == 'TaskService':
                from src.modules.project.task_repository import TaskRepository
                return implementation_class(task_repository=TaskRepository())
            elif class_name == 'ClientService':
                from src.modules.client.repository import ClientRepository
                return implementation_class(client_repository=ClientRepository())
            elif class_name == 'AdminService':
                from src.modules.admin.repository import AdminRepository
                return implementation_class(admin_repository=AdminRepository())
        
        # Default: create instance without special injection
        return implementation_class()
    
    def is_registered(self, interface: Type) -> bool:
        """
        Check if an interface is registered
        
        Args:
            interface: The interface to check
            
        Returns:
            True if registered, False otherwise
        """
        return interface in self._interfaces
    
    def clear(self) -> None:
        """Clear all registrations and instances"""
        self._interfaces.clear()
        self._instances.clear()
        self._singletons.clear()


# Global container instance
container = ServiceContainer()


def register_service(interface: Type[T], implementation: Type[T], singleton: bool = False) -> None:
    """
    Convenience function to register a service with the global container
    
    Args:
        interface: The interface/abstract class
        implementation: The concrete implementation class
        singleton: Whether to reuse the same instance (default: False)
    """
    container.register(interface, implementation, singleton)


def get_service(interface: Type[T]) -> T:
    """
    Convenience function to get a service from the global container
    
    Args:
        interface: The interface/abstract class
        
    Returns:
        Instance of the registered implementation
    """
    return container.get(interface)


def setup_service_registry():
    """
    Set up the service registry with all module implementations
    This should be called during application initialization
    """
    # Import here to avoid circular dependencies
    from src.modules.client.interface import IClientService
    from src.modules.client.service import ClientService
    from src.modules.auth.interface import IAuthService, IFirmService
    from src.modules.auth.service import AuthService
    from src.modules.auth.firm_service import FirmService
    from src.modules.project.interface import IProjectService, ITaskService
    from src.modules.project.service import ProjectService
    from src.modules.project.task_service import TaskService
    from src.modules.export.interface import IExportService
    from src.modules.export.service import ExportService
    from src.modules.admin.interface import IAdminService, ITemplateService, IUserService
    from src.modules.admin.service import AdminService
    from src.modules.admin.template_service import TemplateService
    from src.modules.admin.user_service import UserService
    from src.modules.document.interface import IDocumentService, IAIService
    from src.modules.document.service import DocumentService
    from src.modules.document.analysis_service import AIAnalysisService
    
    # Register all service implementations
    register_service(IClientService, ClientService)
    register_service(IAuthService, AuthService)
    register_service(IFirmService, FirmService)
    register_service(IProjectService, ProjectService)
    register_service(ITaskService, TaskService)
    register_service(IExportService, ExportService)
    register_service(IAdminService, AdminService)
    register_service(ITemplateService, TemplateService)
    register_service(IUserService, UserService)
    register_service(IDocumentService, DocumentService)
    register_service(IAIService, AIAnalysisService)
