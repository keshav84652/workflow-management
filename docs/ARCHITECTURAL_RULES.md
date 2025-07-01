# Architectural Rules and Guidelines

## Overview

This document defines the architectural rules and boundaries for the CPA WorkflowPilot modular monolith. These rules ensure clean separation of concerns, maintainable code, and prevent architectural violations.

## Core Principles

### 1. Module Independence
- Each module MUST be independently testable
- Modules MUST NOT directly import from other modules' internal components
- All inter-module communication MUST go through defined interfaces

### 2. Interface-Based Communication
- All cross-module dependencies MUST use abstract interfaces (ABC pattern)
- Services MUST implement their module's public interface
- Direct service imports across modules are FORBIDDEN

### 3. Dependency Injection
- Services MUST be registered in the DI container
- Routes and services SHOULD use dependency injection when possible
- Fallback to direct instantiation is allowed for backward compatibility

## Module Structure Rules

### Required Files per Module
```
src/modules/{module_name}/
├── __init__.py
├── interface.py          # REQUIRED: Public interface definitions
├── service.py           # REQUIRED: Main service implementation
├── routes.py            # REQUIRED: HTTP route handlers
├── repository.py        # OPTIONAL: Data access layer
└── models.py            # OPTIONAL: Module-specific models
```

### Interface Requirements
- All public interfaces MUST inherit from `ABC`
- Interface methods MUST be decorated with `@abstractmethod`
- Interfaces MUST be defined in `{module}/interface.py`
- Interface names MUST follow pattern `I{ServiceName}Service`

## Dependency Rules

### ✅ ALLOWED Dependencies

#### Within Module
```python
# Same module imports - ALLOWED
from .service import ProjectService
from .repository import ProjectRepository
from .interface import IProjectService
```

#### Shared Components
```python
# Shared utilities - ALLOWED
from src.shared.base import BaseService
from src.shared.di_container import get_service
from src.shared.bootstrap import get_project_service
```

#### Interface Dependencies
```python
# Interface imports - ALLOWED
from src.modules.client.interface import IClientService
from src.shared.interfaces.service_interfaces import IProjectService
```

### ❌ FORBIDDEN Dependencies

#### Direct Cross-Module Service Imports
```python
# FORBIDDEN - Direct service imports
from src.modules.project.service import ProjectService
from src.modules.client.service import ClientService
```

#### Cross-Module Repository Access
```python
# FORBIDDEN - Repository imports across modules
from src.modules.auth.repository import UserRepository
from src.modules.project.repository import ProjectRepository
```

#### Model Imports Across Modules
```python
# FORBIDDEN - Direct model access from other modules
from src.modules.project.models import Project
```

## Service Layer Rules

### Service Implementation
- Services MUST inherit from `BaseService`
- Services MUST implement their module's public interface
- Services MUST use dependency injection for cross-module dependencies

### Example Correct Service Implementation
```python
from src.shared.base import BaseService
from src.shared.di_container import get_service
from src.modules.client.interface import IClientService
from .interface import IProjectService

class ProjectService(BaseService, IProjectService):
    def __init__(self, client_service: IClientService = None):
        super().__init__()
        # Use DI with fallback
        self.client_service = client_service or get_service(IClientService)
        
    def create_project(self, client_id: int) -> Dict[str, Any]:
        # Use injected client service
        client = self.client_service.get_client_by_id(client_id)
        # ... implementation
```

## Route Layer Rules

### Route Implementation
- Routes MUST be thin and delegate to services
- Routes MUST use dependency injection or service registry
- Routes MUST NOT contain business logic

### Example Correct Route Implementation
```python
from flask import Blueprint
from src.shared.di_container import get_service
from .interface import IProjectService
from .service import ProjectService  # Fallback only

@projects_bp.route('/create', methods=['POST'])
def create_project():
    # Use DI with fallback
    try:
        project_service = get_service(IProjectService)
    except ValueError:
        project_service = ProjectService()
    
    result = project_service.create_project(data)
    return jsonify(result)
```

## Testing Rules

### Module Independence Tests
- Each module MUST have tests that run in isolation
- Tests MUST NOT depend on other modules' implementations
- Mock external dependencies using interfaces

### Example Test Structure
```python
import unittest
from unittest.mock import Mock
from src.modules.project.service import ProjectService
from src.modules.client.interface import IClientService

class TestProjectService(unittest.TestCase):
    def setUp(self):
        # Mock external dependencies
        self.mock_client_service = Mock(spec=IClientService)
        self.project_service = ProjectService(
            client_service=self.mock_client_service
        )
```

## Dependency Injection Rules

### Service Registration
- All services MUST be registered in `src/shared/di_container.py`
- Registration MUST happen in `setup_service_registry()`
- Services SHOULD be registered as singletons for stateless services

### Example Registration
```python
def setup_service_registry():
    from src.modules.project.interface import IProjectService
    from src.modules.project.service import ProjectService
    
    register_service(IProjectService, ProjectService, singleton=True)
```

## Error Handling Rules

### Service Errors
- Services MUST return structured error responses
- Services MUST NOT raise exceptions for business logic errors
- Services MUST use `@transactional` decorator for database operations

### Example Error Response
```python
def create_project(self, data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # ... implementation
        return {'success': True, 'project_id': project.id}
    except ValidationError as e:
        return {'success': False, 'error': str(e)}
```

## Automated Enforcement

### Pre-commit Hooks
- Dependency violation checks
- Interface compliance verification
- Import pattern validation

### CI/CD Checks
- Module independence tests
- Architectural compliance verification
- Dependency graph analysis

## Violation Detection

### Common Violations
1. **Direct Service Imports**: `from src.modules.*.service import`
2. **Cross-Module Repository Access**: `from src.modules.*.repository import`
3. **Missing Interface Implementation**: Service not implementing interface
4. **Circular Dependencies**: Module A → Module B → Module A

### Detection Commands
```bash
# Check for direct service imports
grep -r "from src\.modules\..*\.service import" src/modules/

# Check for repository violations
grep -r "from src\.modules\..*\.repository import" src/modules/

# Check for missing interface implementations
python scripts/check_interface_compliance.py
```

## Migration Guidelines

### Existing Code Migration
1. Create module interface if missing
2. Update service to implement interface
3. Replace direct imports with DI calls
4. Register service in DI container
5. Update tests to use mocks

### New Feature Development
1. Define interface first
2. Implement service with interface
3. Register in DI container
4. Create routes using DI
5. Write tests with mocked dependencies

## Enforcement Tools

### Automated Checks
- `scripts/check_dependencies.py` - Validates dependency rules
- `scripts/check_interfaces.py` - Verifies interface compliance
- `tests/architecture/test_module_independence.py` - Module isolation tests

### Manual Review Checklist
- [ ] No direct cross-module service imports
- [ ] All services implement their interfaces
- [ ] DI container registrations are complete
- [ ] Routes use dependency injection
- [ ] Tests mock external dependencies

## Conclusion

These architectural rules ensure:
- **Maintainability**: Clear boundaries and responsibilities
- **Testability**: Independent module testing
- **Scalability**: Easy to add new modules or extract to microservices
- **Reliability**: Reduced coupling and improved error handling

All developers MUST follow these rules. Violations will be caught by automated checks and code reviews.

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-29  
**Status**: ✅ Active Enforcement