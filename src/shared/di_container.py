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
                self._singletons[interface] = self._interfaces[interface]()
            return self._singletons[interface]
        
        # Create new instance each time
        return self._interfaces[interface]()
    
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
    
    # Register all service implementations
    register_service(IClientService, ClientService)
    register_service(IAuthService, AuthService)
    register_service(IFirmService, FirmService)
    register_service(IProjectService, ProjectService)
    register_service(ITaskService, TaskService)