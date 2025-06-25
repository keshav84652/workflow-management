# Test Infrastructure

Basic test structure for CPA WorkflowPilot MVP.

## Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=services --cov=models

# Run specific test file
python -m pytest tests/test_services.py
```

## Test Structure

- `test_services.py` - Service layer functionality tests
- Focus on high-value business logic testing
- Uses in-memory SQLite for fast test execution

## MVP Testing Approach

Tests focus on:
- Configuration management
- Core service layer functionality
- Critical business logic validation

Future expansion can include:
- Integration tests with database
- API endpoint testing
- Authentication flow testing