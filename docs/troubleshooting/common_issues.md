# Common Issues and Troubleshooting Guide

## Kanban Board Issues

### Drag-and-Drop Not Persisting Changes

**Problem**: Moving projects between kanban columns doesn't save to database.

**Root Cause**: The kanban view uses `progress_percentage` for column placement but the drag-and-drop updates `current_status_id`. This mismatch causes visual updates without backend persistence.

**Solution**: 
- Ensure kanban_view function uses `current_status_id` for column determination
- Update project status transitions to maintain both fields in sync

**Code Fix** (blueprints/views.py):
```python
# WRONG - causes regression
if project.progress_percentage >= 75:
    column = 'completed'

# CORRECT - use status ID
if project.current_status_id == 4:  # completed status
    column = 'completed'
```

**Prevention**: Always use status-based logic for workflow state management, not percentage calculations.

---

## AI Services Issues

### Analysis Appearing to Work but Returning Empty Results

**Problem**: "Analyze All Documents" shows success but no actual analysis results are displayed.

**Common Causes**:

1. **Environment Variable Conflicts**
   - System GOOGLE_API_KEY overriding .env file
   - **Fix**: `unset GOOGLE_API_KEY` in shell, then restart Flask

2. **API Key Expiration/Invalid Keys**
   - **Symptoms**: 
     - 403 errors, "API key expired" messages
     - Error: `400 INVALID_ARGUMENT. {'error': {'code': 400, 'message': 'API key expired. Please renew the API key.'}}`
     - `Gemini analysis failed: API_KEY_INVALID`
   - **Fix**: 
     - Update .env with fresh API key
     - Ensure no expired keys are set in shell environment variables
     - Run `unset GOOGLE_API_KEY` to clear expired environment variables

3. **Mock Results Instead of Real Analysis**
   - **Symptoms**: Generic results like "Document type: tax_document"
   - **Fix**: Remove mock/fallback results to fail fast when services unavailable

4. **Data Structure Mapping Issues**
   - **Symptoms**: Frontend shows "No analysis results"
   - **Common Issue**: Backend returns `azure_results` but frontend expects `azure_result`
   - **Fix**: Update _format_analysis_response method to use singular forms

### Azure Document Intelligence Issues

**Problem**: Only table structure extracted, no key-value pairs.

**Root Cause**: Using basic "prebuilt-layout" model instead of capable form models.

**Solution**: Restore proper model priority order:
```python
models_to_try = [
    "prebuilt-tax.us.1099",      # Tax form 1099 variants
    "prebuilt-tax.us.w2",        # W-2 tax forms  
    "prebuilt-document",         # Generic document with fields
    "prebuilt-read"              # OCR text extraction (fallback)
]
```

**Prevention**: Always prioritize specialized models over generic layout detection.

---

## Configuration Issues

### AI Services Not Initializing

**Checklist**:
1. Verify .env file contains correct API keys
2. Check for system environment variable conflicts
3. Ensure config.py properly loads environment variables
4. Verify AI service imports are available

**Debug Commands**:
```bash
# Check environment variables
env | grep -E "(GOOGLE|AZURE|GEMINI)"

# Unset conflicting system variables
unset GOOGLE_API_KEY

# Test API key validity
curl -H "Authorization: Bearer $GOOGLE_API_KEY" "https://generativelanguage.googleapis.com/v1/models"
```

---

## Database Issues

### Session Management Problems

**Problem**: Database changes not persisting or conflicting transactions.

**Best Practices**:
- Always handle exceptions with `db.session.rollback()`
- Commit after each major operation in bulk processes
- Use try/except blocks around database operations

**Example Pattern**:
```python
try:
    # Database operations
    db.session.add(document)
    db.session.commit()
except Exception as e:
    db.session.rollback()
    raise e
```

---

## General Debugging Steps

1. **Check Logs**: Look for specific error messages in Flask console
2. **Environment Isolation**: Verify .env file loading with `print(os.environ.get('KEY'))`
3. **API Testing**: Test external services independently
4. **Frontend-Backend Sync**: Verify data structure expectations match
5. **Database State**: Check if records are actually created/updated

---

## Prevention Strategies

- **Use Status-Based Logic**: Avoid percentage calculations for workflow states
- **Fail Fast**: Remove fallback/mock results that hide configuration issues
- **Environment Management**: Use .env files exclusively, avoid system variables
- **Comprehensive Error Handling**: Always include rollback in exception handling
- **Model Priority**: Use most capable AI models first, fallback to basic ones