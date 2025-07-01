# Service Return Format Standard

## Standard Response Format

All service methods should return consistent response formats for better error handling and data consumption.

### Success Response
```python
{
    'success': True,
    'message': 'Operation completed successfully',
    'data': {...}  # Optional, specific data returned
}
```

### Error Response
```python
{
    'success': False,
    'message': 'Error description for user display'
}
```

### Data Response (for getters)
```python
{
    'success': True,
    'data': [...],  # or single object
    'count': 10     # Optional, for lists
}
```

## Current State

The majority of services follow this pattern, but some inconsistencies remain:

- Some services use `'error'` instead of `'message'` for error responses
- Some methods return raw data objects without the success wrapper
- Some methods return tuples with HTTP status codes

## Migration Strategy

1. **High Priority**: Fix critical user-facing services (auth, document, project)
2. **Medium Priority**: Standardize statistical and data services  
3. **Low Priority**: Update utility and internal services

## Examples Fixed

- ProjectService.get_project_progress() - standardized error response
- DocumentService.create_checklist() - standardized error response

## Tools for Detection

```bash
# Find non-standard error patterns
rg "'error':" src/modules/*/service.py

# Find methods returning tuples (likely with status codes)
rg "return.*," src/modules/*/service.py
```