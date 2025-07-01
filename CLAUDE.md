# CPA WorkflowPilot - Development & Architecture Guide

**Project:** CPA WorkflowPilot - Professional Workflow Management System  
**Architecture:** Service Layer Pattern with Repository Pattern  
**Phase:** 2.5 Complete - Ready for Phase 3 Modular Monolith  
**Last Updated:** $(date +"%Y-%m-%d")

---

## 🏗️ Current Architecture Overview

The application follows a **professional multi-layered architecture** with clean separation of concerns:

```
├── blueprints/          # Presentation Layer (Flask routes)
├── services/            # Business Logic Layer  
├── repositories/        # Data Access Layer
├── models/              # Database Models (SQLAlchemy)
├── events/              # Event-Driven Communication
├── utils/               # Shared Utilities
└── core/                # Core Infrastructure
```

## 🎯 Service Layer Pattern (Current State)

### ✅ **Properly Implemented Services**

All services follow the **instance method pattern** for proper dependency management:

```python
# ✅ CORRECT: Instance method with dependency injection
class TaskService(BaseService):
    def __init__(self):
        super().__init__()
        self.task_repository = TaskRepository()
    
    @transactional
    def create_task(self, title, description, firm_id, user_id):
        # Business logic here
        return {'success': True, 'task': task_data}
```

### 🔧 **Blueprint Integration Pattern**

All blueprints follow the **one service instance per request scope** pattern:

```python
# ✅ CORRECT: Service instance per request
@bp.route('/some-route')
def route_handler():
    # Create ONE service instance for this request
    service = SomeService()
    
    # Use instance for all operations in this request
    result1 = service.method1()
    result2 = service.method2()
    
    return render_template(...)
```

## 📋 Service Inventory

### **Core Business Services**
| Service | Status | Pattern | Repository |
|---------|--------|---------|------------|
| `TaskService` | ✅ Complete | Instance | `TaskRepository` |
| `ProjectService` | ✅ Complete | Instance | `ProjectRepository` |
| `ClientService` | ✅ Complete | Instance | `ClientRepository` |
| `DocumentService` | ✅ Complete | Mixed Static/Instance | N/A |
| `WorkTypeService` | ✅ Complete | Instance | N/A |
| `TemplateService` | ✅ Complete | Instance | N/A |
| `UserService` | ✅ Complete | Instance | `UserRepository` |

### **Supporting Services**
| Service | Status | Pattern |
|---------|--------|---------|
| `ActivityLoggingService` | ✅ Complete | Static (by design) |
| `AIService` | ✅ Complete | Instance |
| `AuthService` | ✅ Complete | Static (stateless) |
| `ViewsService` | ✅ Complete | Static (stateless) |

## 🔧 Transaction Management

All data-modifying operations use the `@transactional` decorator:

```python
from services.base import BaseService, transactional

class SomeService(BaseService):
    @transactional
    def create_something(self, data):
        # Automatic transaction management
        # Commit on success, rollback on exception
        pass
```

## 🗄️ Repository Pattern

Data access is abstracted through repositories:

```python
class TaskRepository:
    def get_by_id_with_firm_access(self, task_id, firm_id):
        return Task.query.filter_by(id=task_id, firm_id=firm_id).first()
    
    def get_filtered_tasks(self, firm_id, filters=None):
        # Complex filtering logic encapsulated
        pass
```

## 🎯 Blueprint Architecture

### **Current State: Clean & Consistent**

✅ **No business logic in blueprints**  
✅ **No direct database access**  
✅ **Service layer delegation only**  
✅ **Proper error handling**  
✅ **Consistent response patterns**

Example blueprint structure:
```python
@bp.route('/endpoint')
def handler():
    firm_id = get_session_firm_id()
    user_id = get_session_user_id()
    
    # Single service instance per request
    service = SomeService()
    
    # Business logic delegated to service
    result = service.perform_operation(firm_id, user_id, data)
    
    if result['success']:
        flash(result['message'], 'success')
        return redirect(...)
    else:
        flash(result['message'], 'error')
        return redirect(...)
```

## 📦 Event-Driven Architecture

Services publish domain events for loose coupling:

```python
from events.schemas import TaskCreatedEvent
from events.publisher import publish_event

# In service method
event = TaskCreatedEvent(
    task_id=task.id,
    firm_id=firm_id,
    title=task.title
)
publish_event(event)
```

## 🚀 Phase 3 Readiness Assessment

### ✅ **Prerequisites Met**

- **Clean Service Boundaries**: All services have clear responsibilities
- **No Architectural Violations**: Zero direct DB access in blueprints
- **Consistent Patterns**: All services follow the same architectural patterns
- **Transaction Safety**: Reliable data integrity with `@transactional`
- **Event Infrastructure**: Ready for inter-module communication

### 🎯 **Phase 3 Preparation**

The current architecture is **perfectly positioned** for Phase 3 modular monolith refactoring:

1. **Service boundaries** → Module boundaries
2. **Event publishing** → Inter-module communication
3. **Repository pattern** → Module data access
4. **Transaction management** → Module transaction boundaries

## 🔧 Development Patterns

### **Adding New Features**

1. **Create/Update Service**: Add business logic to appropriate service
2. **Update Repository**: Add any new data access methods
3. **Update Blueprint**: Add route handler with service delegation
4. **Add Events**: Publish relevant domain events
5. **Update Tests**: Test service logic, not blueprints

### **Service Method Signature Pattern**

```python
@transactional  # For data-modifying operations
def business_operation(self, business_params, firm_id, user_id=None):
    """
    Args:
        business_params: Domain-specific parameters
        firm_id: Always required for multi-tenancy
        user_id: Required for audit trail and permissions
    
    Returns:
        Dict with 'success', 'message', and result data
    """
    pass
```

## 🏃‍♂️ Running the Application

### **Development Setup**
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export FLASK_ENV=development
export DATABASE_URL=sqlite:///workflow.db

# Run application
python app.py
```

### **Testing**
```bash
# Run unit tests
python -m pytest tests/unit/

# Run integration tests  
python -m pytest tests/integration/

# Run all tests
python -m pytest
```

## 📁 Key Files & Directories

### **Core Architecture**
- `services/base.py` - Base service class with `@transactional`
- `repositories/` - Data access layer
- `models.py` - Database models
- `core/db_import.py` - Database configuration

### **Business Logic**
- `services/task_service.py` - Task management
- `services/project_service.py` - Project management  
- `services/client_service.py` - Client management
- `services/document_service.py` - Document/checklist management

### **Presentation Layer**
- `blueprints/tasks.py` - Task routes
- `blueprints/projects.py` - Project routes
- `blueprints/clients.py` - Client routes
- `blueprints/documents.py` - Document routes

## 🎯 Next Steps (Phase 3)

The application is **architecturally ready** for Phase 3 modular monolith refactoring:

1. **Module Structure**: Reorganize into domain modules
2. **Module Interfaces**: Define clean module APIs  
3. **Module Registration**: Replace blueprint registration
4. **Shared Infrastructure**: Extract common utilities

The current clean service layer will make this transition **smooth and low-risk**.

---

*This document reflects the current architectural state after Phase 2.5 completion. All major architectural violations have been resolved and the codebase follows professional enterprise patterns.*