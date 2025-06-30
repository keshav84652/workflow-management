"""
Service Bootstrap for CPA WorkflowPilot
Registers service implementations with the service registry to enable dependency injection.
"""

from .interfaces import ServiceRegistry


def register_services():
    """Register all service implementations with the service registry"""
    
    # Import services here to avoid circular imports during app startup
    from src.modules.project.service import ProjectService
    from src.modules.project.task_service import TaskService
    from src.modules.client.service import ClientService
    
    # Register service implementations
    ServiceRegistry.register('project_service', ProjectService())
    ServiceRegistry.register('task_service', TaskService())
    ServiceRegistry.register('client_service', ClientService())


def get_project_service():
    """Get project service instance"""
    service = ServiceRegistry.get_project_service()
    if not service:
        # Fallback if not registered
        from src.modules.project.service import ProjectService
        return ProjectService()
    return service


def get_task_service():
    """Get task service instance"""
    service = ServiceRegistry.get_task_service()
    if not service:
        # Fallback if not registered
        from src.modules.project.task_service import TaskService
        return TaskService()
    return service


def get_client_service():
    """Get client service instance"""
    service = ServiceRegistry.get_client_service()
    if not service:
        # Fallback if not registered
        from src.modules.client.service import ClientService
        return ClientService()
    return service


