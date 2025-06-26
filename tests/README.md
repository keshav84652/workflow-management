# Test Infrastructure

Comprehensive test structure for CPA WorkflowPilot refactoring safety.

## Running Tests

### Quick Safety Net (Before Refactoring)
```bash
# Run all safety net tests
python run_safety_tests.py

# Run only critical tests (recent fixes validation)
python run_safety_tests.py --critical-only

# Run only integration tests
python run_safety_tests.py --integration-only
```

### Individual Test Files
```bash
# Run basic service tests
python -m pytest tests/test_services.py

# Run integration safety tests 
python -m pytest tests/test_integration_refactor_safety.py

# Run critical AI workflow tests
python -m pytest tests/test_ai_workflow_critical.py
```

### Advanced Testing
```bash
# Run with coverage
python -m pytest tests/ --cov=services --cov=models

# Run with verbose output
python -m pytest tests/ -v
```

## Test Structure

### Safety Net Tests (Pre-Refactoring)
- `test_integration_refactor_safety.py` - Full integration tests for workflows being refactored
- `test_ai_workflow_critical.py` - Focused tests for AI service fixes
- `run_safety_tests.py` - Test runner with clear pass/fail reporting

### Foundation Tests
- `test_services.py` - Basic service layer functionality tests

## Testing Strategy

### Phase 0: Safety Net (Current)
**Purpose**: Protect against regressions during refactoring

**Focus Areas**:
- Kanban board persistence (views.py refactoring target)
- AI document analysis workflow (ai.py + ai_service.py)
- Document checklist workflows (documents.py refactoring target)
- Task status transitions (tasks.py refactoring target)
- Service boundary contracts
- Database transaction safety

**Test Types**:
- Integration tests with real database operations
- Contract tests for service interfaces
- Error handling and rollback validation
- Critical workflow end-to-end testing

### Phase 1+: Comprehensive Testing (Post-Refactoring)
**Purpose**: Full test coverage for long-term maintenance

**Planned Additions**:
- Unit tests for extracted service methods
- API endpoint testing
- Authentication flow testing
- Performance regression testing
- Security testing

## Test Environment

- Uses in-memory SQLite for fast execution
- Mock external services (Azure, Gemini) for isolated testing
- Real Flask application context for integration fidelity
- Temporary file handling for document upload testing

## Safety Net Validation

Before proceeding with refactoring:

1. **🔧 Critical Tests** - Validate recent bug fixes
2. **🛡️ Integration Tests** - Validate workflow integrity  
3. **📋 Existing Tests** - Ensure baseline functionality

All three test suites must pass before refactoring begins.