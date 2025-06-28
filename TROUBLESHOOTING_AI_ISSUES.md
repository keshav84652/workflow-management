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
- ⚠️ Azure Provider: Still showing W-2 field names for 1099-G documents (needs investigation)

### Next Steps
1. Investigate why Azure provider still returns incorrect field names despite using tax-specific models
2. Compare current Azure field extraction with working version from `be39018`
3. Ensure tax model selection logic works correctly for 1099-G documents

---
*Document created: 2025-06-28*
*Reference commit: be39018 (Working baseline)*
*Issue commits: 4609785 (Strategy Pattern), 70174f4-3a3247f (Fixes)*