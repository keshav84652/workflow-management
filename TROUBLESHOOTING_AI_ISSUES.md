# AI Services Troubleshooting Guide

## Issue: Strategy Pattern Architecture Compatibility Errors

### Problem Description
After implementing the AI Strategy Pattern refactor (commit `4609785` on June 28, 2025), both Azure and Gemini providers broke with various interface compatibility errors.

### Reference Working Version
**Working baseline:** Commit `be39018` (June 26, 14:06:42 +0530) - "Complete AI service transaction fixes"
- **File:** `services/ai_service.py` (monolithic implementation)
- **Status:** Last known working version before architectural changes

### Specific Errors Encountered

#### 1. Missing Method Error (Gemini)
```
ERROR: 'GeminiProvider' object has no attribute '_parse_gemini_response'
```

**Root Cause:** Strategy Pattern expected different interface methods than monolithic version.

**Solution:** 
- Removed calls to non-existent `_parse_gemini_response()` and `_calculate_confidence()`
- Implemented direct response parsing in `analyze_document()` method
- Used `_standardize_results()` from base class instead of custom parsing

#### 2. Data Structure Incompatibility
**Root Cause:** 
- Monolithic version: Direct data format returned to frontend
- Strategy Pattern: Data wrapped in `{provider: {...}, raw_results: {...}, timestamp: ...}` format
- Frontend transformation expected specific field names in `raw_results`

**Solution:**
- Azure: Provide `{fields: {...}, entities: [...], text: "..."}` in raw_results
- Gemini: Provide `{analysis_text: "...", summary: "...", key_findings: [...]}` in raw_results
- Both call `self._standardize_results(raw_results)` to maintain interface compliance

#### 3. Model Configuration Issues (Azure)
**Root Cause:** Complex document type detection logic interfered with working field extraction.

**Solution:** 
- Restored simple, direct field extraction from `be39018`
- Restored tax-specific models: `prebuilt-tax.us.1099`, `prebuilt-tax.us.w2`
- Removed complex field mapping logic that was causing confusion

### Architecture Differences

#### Monolithic Version (Working)
```python
class AIService:
    def _analyze_with_azure(self, document_path):
        # Direct method call within same class
        return extracted_data  # Direct format
        
    def _analyze_with_gemini(self, document_path):
        # Direct method call within same class  
        return analysis_results  # Direct format
```

#### Strategy Pattern (Fixed)
```python
class AzureProvider(AIProvider):
    def analyze_document(self, document_path):
        # Must implement interface method
        raw_results = {...}  # Working data format
        return self._standardize_results(raw_results)  # Interface compliance

class GeminiProvider(AIProvider):  
    def analyze_document(self, document_path):
        # Must implement interface method
        raw_results = {...}  # Working data format
        return self._standardize_results(raw_results)  # Interface compliance
```

### Data Flow Comparison

#### Before (Monolithic)
```
Azure Method → Direct Data → Frontend
Gemini Method → Direct Data → Frontend  
```

#### After (Strategy Pattern)
```
Azure Provider → _standardize_results() → AI Service → Frontend Transformation
Gemini Provider → _standardize_results() → AI Service → Frontend Transformation
```

### Key Lessons Learned

1. **Interface Compatibility:** When refactoring to design patterns, ensure all expected interface methods exist
2. **Data Structure Consistency:** Frontend transformations must match provider data structures
3. **Working Baseline:** Always identify and document the last working commit before major refactors
4. **Incremental Changes:** Avoid simultaneous architectural and functional changes

### Prevention Strategies

1. **Test After Each Change:** Run AI analysis tests after each architectural modification
2. **Preserve Working Logic:** When changing architecture, preserve working business logic exactly
3. **Document Interfaces:** Clearly define what methods and data structures each layer expects
4. **Gradual Migration:** Refactor architecture without changing business logic first, then optimize

### Current Status
- ✅ Gemini Provider: Working correctly with meaningful analysis and key findings
- ⚠️ Azure Provider: Still showing W-2 field names for 1099-G documents (known issue - under investigation)

## Known Issue: Azure W-2 Field Names for 1099-G Documents

### Problem Description
Azure returns W-2 field names (e.g., `WagesTipsAndOtherCompensation`) for 1099-G documents, despite correctly identifying the document type (`W2FormVariant: 1099-G`).

### Root Cause Identified: API Version Incompatibility
According to Microsoft documentation:
- **`prebuilt-tax.us.1099`**: Only supported in API version `2024-11-30` (GA)
- **`prebuilt-tax.us.w2`**: Supported in multiple versions (`2024-11-30`, `2023-07-31`, `v2.1`)

**Issue:** Azure client may be using older API version that doesn't support 1099 model
1. Azure tries `prebuilt-tax.us.1099` model → **FAILS** (not available in older API version)
2. Falls back to `prebuilt-tax.us.w2` model → **SUCCEEDS** (available in older versions)
3. W-2 model processes 1099-G document but applies W-2 field schema
4. Model correctly detects content type but field names remain W-2-specific

### Enhanced Debugging Added
Enhanced logging in Azure provider to track model selection:
- `🔍 TRYING Azure model: [model_name]`
- `❌ Model [model] not suitable/available...`
- `✅ SUCCESS: Using Azure model [model]`
- `📋 Extracted field: [field_name] = [value]`
- `🎯 Azure analysis completed using model: [model]`

### Solution Implemented: API Version Update
**✅ FIXED**: Updated Azure client to explicitly use API version `2024-11-30`:
```python
self.client = DocumentIntelligenceClient(
    endpoint=self.endpoint,
    credential=AzureKeyCredential(self.key),
    api_version="2024-11-30"  # Required for 1099 model support
)
```

### Alternative Solutions (if API version fix doesn't work)
1. **Model Reordering**: Try `prebuilt-document` before `prebuilt-tax.us.w2` to avoid W-2 schema contamination
2. **Field Mapping**: Add post-processing to map W-2 field names to 1099-G equivalents when document type is detected as 1099-G
3. **SDK Version Check**: Verify Azure SDK version supports latest API features
4. **Alternative Strategy**: Use generic document model and add custom field extraction

### Testing Required
1. Run AI analysis to confirm `prebuilt-tax.us.1099` model now works
2. Verify 1099-G documents show correct field names (e.g., "UnemploymentCompensation" instead of "WagesTipsAndOtherCompensation")
3. Check enhanced logging shows successful 1099 model usage

---
*Document created: 2025-06-28*
*Reference commit: be39018 (Working baseline)*
*Issue commits: 4609785 (Strategy Pattern), 70174f4-3a3247f (Fixes)*