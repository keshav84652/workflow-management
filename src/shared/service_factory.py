"""
Service Factory Pattern
Provides properly configured service instances with dependency injection
"""

from typing import TypeVar, Type, Dict, Any
import inspect

T = TypeVar('T')

class ServiceFactory:
    """Factory for creating properly configured service instances"""
    
    @staticmethod
    def create_auth_service():
        """Create AuthService with proper dependency injection"""
        from src.modules.auth.firm_repository import FirmRepository
        from src.modules.auth.repository import UserRepository
        from src.modules.auth.service import AuthService
        
        return AuthService(
            firm_repository=FirmRepository(),
            user_repository=UserRepository()
        )
    
    @staticmethod
    def create_project_service():
        """Create ProjectService with proper dependency injection"""
        from src.modules.project.repository import ProjectRepository
        from src.modules.project.service import ProjectService
        
        return ProjectService(project_repository=ProjectRepository())
    
    @staticmethod
    def create_task_service():
        """Create TaskService with proper dependency injection"""
        from src.modules.project.task_repository import TaskRepository
        from src.modules.project.task_service import TaskService
        
        return TaskService(task_repository=TaskRepository())
    
    @staticmethod
    def create_client_service():
        """Create ClientService with proper dependency injection"""
        try:
            from src.modules.client.repository import ClientRepository
            from src.modules.client.service import ClientService
            
            return ClientService(client_repository=ClientRepository())
        except ImportError:
            # Return None if client module not available
            return None
    
    @staticmethod
    def create_document_service():
        """Create DocumentService with proper dependency injection"""
        try:
            from src.modules.document.repository import DocumentRepository
            from src.modules.document.service import DocumentService
            
            return DocumentService(document_repository=DocumentRepository())
        except ImportError:
            # Return None if document module not available
            return None