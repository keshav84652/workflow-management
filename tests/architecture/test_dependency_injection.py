"""
Test Dependency Injection Container

Verifies that the DI container is properly set up and services can be retrieved.
"""

import unittest
import sys
import os

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.shared.di_container import get_service, container
from src.modules.client.interface import IClientService
from src.modules.project.interface import IProjectService, ITaskService
from src.modules.auth.interface import IAuthService, IFirmService
from src.modules.export.interface import IExportService


class TestDependencyInjection(unittest.TestCase):
    """Test dependency injection container functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Initialize the DI container
        from src.shared.di_container import setup_service_registry
        setup_service_registry()
    
    def test_client_service_registration(self):
        """Test that client service is properly registered"""
        service = get_service(IClientService)
        self.assertIsNotNone(service)
        self.assertTrue(hasattr(service, 'get_clients_for_api'))
    
    def test_project_service_registration(self):
        """Test that project service is properly registered"""
        service = get_service(IProjectService)
        self.assertIsNotNone(service)
        self.assertTrue(hasattr(service, 'get_projects_by_firm'))
    
    def test_task_service_registration(self):
        """Test that task service is properly registered"""
        service = get_service(ITaskService)
        self.assertIsNotNone(service)
        self.assertTrue(hasattr(service, 'get_tasks_by_firm'))
    
    def test_auth_service_registration(self):
        """Test that auth service is properly registered"""
        service = get_service(IAuthService)
        self.assertIsNotNone(service)
        self.assertTrue(hasattr(service, 'get_users_for_firm'))
    
    def test_firm_service_registration(self):
        """Test that firm service is properly registered"""
        service = get_service(IFirmService)
        self.assertIsNotNone(service)
        self.assertTrue(hasattr(service, 'get_firm_by_id'))
    
    def test_export_service_registration(self):
        """Test that export service is properly registered"""
        service = get_service(IExportService)
        self.assertIsNotNone(service)
        self.assertTrue(hasattr(service, 'export_projects_csv'))
    
    def test_service_interface_compliance(self):
        """Test that services implement their interfaces correctly"""
        # Test client service
        client_service = get_service(IClientService)
        self.assertIsInstance(client_service, IClientService)
        
        # Test project service
        project_service = get_service(IProjectService)
        self.assertIsInstance(project_service, IProjectService)
        
        # Test task service
        task_service = get_service(ITaskService)
        self.assertIsInstance(task_service, ITaskService)
        
        # Test auth service
        auth_service = get_service(IAuthService)
        self.assertIsInstance(auth_service, IAuthService)
        
        # Test firm service
        firm_service = get_service(IFirmService)
        self.assertIsInstance(firm_service, IFirmService)
        
        # Test export service
        export_service = get_service(IExportService)
        self.assertIsInstance(export_service, IExportService)
    
    def test_unregistered_service_raises_error(self):
        """Test that requesting an unregistered service raises ValueError"""
        from abc import ABC, abstractmethod
        
        class IUnregisteredService(ABC):
            @abstractmethod
            def some_method(self):
                pass
        
        with self.assertRaises(ValueError):
            get_service(IUnregisteredService)
    
    def test_container_state(self):
        """Test that the container maintains proper state"""
        # Check that services are registered
        self.assertTrue(container.is_registered(IClientService))
        self.assertTrue(container.is_registered(IProjectService))
        self.assertTrue(container.is_registered(ITaskService))
        self.assertTrue(container.is_registered(IAuthService))
        self.assertTrue(container.is_registered(IFirmService))
        self.assertTrue(container.is_registered(IExportService))


if __name__ == '__main__':
    unittest.main()