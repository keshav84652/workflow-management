# Common Issues and Troubleshooting Guide

## Kanban Board Issues

### Drag-and-Drop Not Persisting Changes

**Problem**: Moving projects between kanban columns doesn't save to database.

**Root Cause**: The kanban view uses `progress_percentage` for column placement but the drag-and-drop updates `current_status_id`. This mismatch causes visual updates without backend persistence.

**Solution**: 
- Ensure kanban_view function uses `current_status_id` for column determination
- Update project status transitions to maintain both fields in sync
- **CRITICAL**: Update project tasks when workflow status changes to keep progress_percentage synchronized

**Code Fix** (blueprints/views.py):
```python
# WRONG - causes regression
if project.progress_percentage >= 75:
    column = 'completed'

# CORRECT - use status ID
if project.current_status_id == 4:  # completed status
    column = 'completed'
```

**Additional Fix** (services/project_service.py):
```python
# When moving project via kanban, update both status and tasks
project.current_status_id = new_status_id
# CRITICAL: Also update project tasks to sync progress_percentage
ProjectService._update_project_tasks_for_workflow_change(project, old_status_id, new_status_id)
```

**Prevention**: Always use status-based logic for workflow state management, not percentage calculations.

### Kanban Columns Wrong (Generic vs Template-Based)

**Problem**: Kanban showing generic columns ("Not Started", "In Progress") instead of template task names ("Awaiting Documents", "Client Review").

**Root Cause**: 
- Kanban view was using hardcoded generic columns instead of TaskStatus objects
- TaskStatus objects contain the actual template task names when templates are converted to workflows

**Solution**:
- Use TaskStatus objects from work_type as kanban columns
- Map projects to columns based on their `current_status_id`
- Create wrapper objects for template compatibility

**Code Fix** (blueprints/views.py):
```python
# Get TaskStatus objects (which contain template task names)
kanban_columns = TaskStatus.query.filter_by(
    work_type_id=current_work_type.id
).order_by(TaskStatus.position.asc()).all()

# Map projects to columns based on current_status_id
for project in projects:
    if project.current_status_id:
        for column in kanban_columns:
            if project.current_status_id == column.id:
                projects_by_column[column.id].append(project)
```

**Key Insight**: Template tasks become TaskStatus objects with same names during workflow creation.

### Progress Percentage Not Updating on Kanban Moves

**Problem**: Moving projects between kanban columns updates workflow status but progress percentage stays the same.

**Root Cause**: `progress_percentage` is calculated from actual task completion, but kanban moves only updated `current_status_id` without updating the project's tasks.

**Solution**: When kanban status changes, update project tasks to reflect workflow progression.

**Code Implementation**:
```python
def _update_project_tasks_for_workflow_change(project, old_status_id, new_status_id):
    # Column 1: Task 1 = "In Progress", rest = "Not Started" (0% complete)
    # Column 2: Task 1 = "Completed", Task 2 = "In Progress", rest = "Not Started" (20% if 5 tasks)
    
    for i, task in enumerate(project_tasks):
        if i < new_position:
            task.status = 'Completed'      # Tasks before current position
        elif i == new_position:
            task.status = 'In Progress'    # Current position task
        else:
            task.status = 'Not Started'    # Tasks after current position
```

**Result**: Kanban position and progress percentage stay perfectly synchronized.

---

## Service Layer Issues

### Missing Static Method Errors

**Problem**: `AttributeError: type object 'ServiceName' has no attribute 'method_name'`

**Root Cause**: Service methods being called as static methods but defined as instance methods.

**Common Examples**:
- `AdminService.get_templates_for_firm()` missing firm_id argument ✅ FIXED
- `DocumentService.get_checklists_for_firm()` not defined as static ✅ FIXED
- `UserService.get_users_by_firm()` not defined as static ✅ FIXED

**Solution**: Convert service methods to `@staticmethod` or create instances.

**Code Fix**:
```python
# WRONG - instance method called as static
class AdminService:
    def get_templates_for_firm(self, firm_id):
        return self.template_repository.get_by_firm(firm_id)

# CORRECT - static method
class AdminService:
    @staticmethod
    def get_templates_for_firm(firm_id):
        return Template.query.filter_by(firm_id=firm_id).all()
```

**Recent Fixes Applied**:
- Added `@staticmethod` to `DocumentService.get_checklists_for_firm()` in services/document_service.py:192
- Added `@staticmethod` to `UserService.get_users_by_firm()` in services/user_service.py:70
- Fixed all AttributeError issues in checklist and time tracking pages

**Prevention**: Decide consistently whether service methods should be static or instance-based.

### Import Errors in Blueprint Files

**Problem**: `NameError: name 'ModelName' is not defined`

**Root Cause**: Missing imports when adding new model references.

**Solution**: Add missing imports to blueprint import statements.

**Code Fix**:
```python
# Add missing models to imports
from models import Task, Project, User, WorkType, Template, TemplateTask, Client, TaskStatus
```

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