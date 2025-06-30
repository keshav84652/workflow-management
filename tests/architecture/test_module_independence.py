"""
Test Module Independence

Verifies that modules can be tested in isolation without dependencies on other modules.
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestModuleIndependence(unittest.TestCase):
    """Test that modules can operate independently"""
    
    def test_client_service_independence(self):
        """Test that ClientService can be tested in isolation"""
        from src.modules.client.service import ClientService
        from src.modules.client.interface import IClientService
        
        # Should be able to instantiate without dependencies
        service = ClientService()
        self.assertIsInstance(service, IClientService)
    
    def test_project_service_independence(self):
        """Test that ProjectService can be tested in isolation"""
        from src.modules.project.service import ProjectService
        from src.modules.project.interface import IProjectService
        
        # Should be able to instantiate without dependencies
        service = ProjectService()
        self.assertIsInstance(service, IProjectService)
    
    def test_task_service_independence(self):
        """Test that TaskService can be tested in isolation"""
        from src.modules.project.task_service import TaskService
        from src.modules.project.interface import ITaskService
        
        # Should be able to instantiate without dependencies
        service = TaskService()
        self.assertIsInstance(service, ITaskService)
    
    def test_auth_service_independence(self):
        """Test that AuthService can be tested in isolation"""
        from src.modules.auth.service import AuthService
        from src.modules.auth.interface import IAuthService
        
        # Should be able to instantiate without dependencies
        service = AuthService()
        self.assertIsInstance(service, IAuthService)
    
    def test_export_service_with_mocked_dependencies(self):
        """Test that ExportService can be tested with mocked dependencies"""
        from src.modules.export.service import ExportService
        from src.modules.export.interface import IExportService
        from src.modules.client.interface import IClientService
        from src.modules.project.interface import IProjectService, ITaskService
        
        # Create mocked dependencies
        mock_client_service = Mock(spec=IClientService)
        mock_project_service = Mock(spec=IProjectService)
        mock_task_service = Mock(spec=ITaskService)
        
        # Should be able to instantiate with mocked dependencies
        service = ExportService(
            project_service=mock_project_service,
            task_service=mock_task_service,
            client_service=mock_client_service
        )
        self.assertIsInstance(service, IExportService)
    
    def test_dashboard_aggregator_with_mocked_dependencies(self):
        """Test that DashboardAggregatorService can be tested with mocked dependencies"""
        from src.modules.dashboard.aggregator_service import DashboardAggregatorService
        
        # Should be able to instantiate (it has fallback logic)
        service = DashboardAggregatorService()
        self.assertIsNotNone(service)
    
    def test_interface_imports_work_independently(self):
        """Test that interface imports work without circular dependencies"""
        # These imports should work without issues
        from src.modules.client.interface import IClientService
        from src.modules.project.interface import IProjectService, ITaskService
        from src.modules.auth.interface import IAuthService, IFirmService
        from src.modules.export.interface import IExportService
        
        # All interfaces should be importable
        self.assertTrue(hasattr(IClientService, '__abstractmethods__'))
        self.assertTrue(hasattr(IProjectService, '__abstractmethods__'))
        self.assertTrue(hasattr(ITaskService, '__abstractmethods__'))
        self.assertTrue(hasattr(IAuthService, '__abstractmethods__'))
        self.assertTrue(hasattr(IFirmService, '__abstractmethods__'))
        self.assertTrue(hasattr(IExportService, '__abstractmethods__'))
    
    def test_no_circular_imports(self):
        """Test that there are no circular import issues"""
        # Try importing all modules - this should not raise ImportError
        try:
            from src.modules.client import service as client_service
            from src.modules.project import service as project_service
            from src.modules.project import task_service
            from src.modules.auth import service as auth_service
            from src.modules.auth import firm_service
            from src.modules.export import service as export_service
            from src.modules.admin import service as admin_service
            from src.modules.document import service as document_service
            
            # If we get here, no circular imports
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Circular import detected: {e}")
    
    def test_shared_services_independence(self):
        """Test that shared services can operate independently"""
        from src.shared.services.user_service import SharedUserService
        from src.shared.services.views_service import ViewsService
        
        # Should be able to instantiate
        user_service = SharedUserService()
        views_service = ViewsService()
        
        self.assertIsNotNone(user_service)
        self.assertIsNotNone(views_service)


class TestArchitecturalBoundaries(unittest.TestCase):
    """Test that architectural boundaries are respected"""
    
    def test_no_direct_repository_imports_across_modules(self):
        """Test that modules don't directly import repositories from other modules"""
        import ast
        import os
        
        violations = []
        src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'modules')
        
        for root, dirs, files in os.walk(src_path):
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                            
                        # Parse the AST to find imports
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ImportFrom):
                                if node.module and 'src.modules.' in str(node.module) and '.repository' in str(node.module):
                                    # Check if it's a cross-module repository import
                                    current_module = os.path.basename(os.path.dirname(file_path))
                                    imported_module = str(node.module).split('.')[2]  # src.modules.{module}.repository
                                    
                                    if current_module != imported_module:
                                        violations.append(f"{file_path}: imports {node.module}")
                    except Exception:
                        # Skip files that can't be parsed
                        pass
        
        if violations:
            self.fail(f"Cross-module repository imports found: {violations}")
    
    def test_interface_based_communication(self):
        """Test that services use interfaces for cross-module communication"""
        # This is a basic test - in practice you'd want more sophisticated checking
        from src.modules.export.service import ExportService
        from src.modules.dashboard.aggregator_service import DashboardAggregatorService
        
        # These services should have interface-based dependencies
        export_service = ExportService()
        dashboard_service = DashboardAggregatorService()
        
        # Check that they have the expected interface dependencies
        self.assertTrue(hasattr(export_service, 'project_service'))
        self.assertTrue(hasattr(export_service, 'client_service'))
        self.assertTrue(hasattr(export_service, 'task_service'))
        
        self.assertTrue(hasattr(dashboard_service, 'project_service'))
        self.assertTrue(hasattr(dashboard_service, 'client_service'))
        self.assertTrue(hasattr(dashboard_service, 'task_service'))
        self.assertTrue(hasattr(dashboard_service, 'auth_service'))


if __name__ == '__main__':
    unittest.main()