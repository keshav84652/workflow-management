# Known Issues - CPA WorkflowPilot

This document tracks current known issues that need to be addressed.

## 🔴 Critical Issues

### 1. Document Visualization with Tick Marks Not Working
**Status:** 🔍 **ROOT CAUSE IDENTIFIED**  
**Description:** The "View with tick marks" functionality for annotated documents is not working properly.  
**Impact:** Users cannot see AI analysis overlays on documents  
**Location:** Document analysis visualization system  
**Priority:** High  

**Root Cause Analysis:**
✅ **Dependencies**: All required libraries are installed (OpenCV, pdf2image, NumPy, Azure SDK)  
✅ **Azure Service**: Successfully analyzes documents and extracts field coordinates  
✅ **Visualizer Service**: Can create annotated images with tick marks  
❌ **Route Implementation**: The Flask route is overly complex and uses outdated integration patterns  

**Specific Issues Found:**
1. **Complex DocumentProcessor Pipeline**: Route tries to use async document processing when simple Azure analysis suffices
2. **Data Format Mismatch**: Azure returns data in `documents[0].fields` but route expects `key_value_pairs`
3. **Missing Dependencies**: `poppler-utils` not installed for PDF conversion (affects PDFs only)
4. **Error Handling**: Poor error reporting makes debugging difficult

**Proven Working Solution:**
The visualization system works when called directly:
- Azure analysis extracts 26 fields with coordinates from tax documents
- DocumentVisualizer successfully creates annotated images with green tick marks
- Generated files are 157KB+ and display correctly

**Expected Behavior:**
- After analyzing a document with AI, users should be able to click "Annotations" or "View with tick marks"
- This should display the document with visual overlays showing extracted fields
- Tick marks, boxes, or highlights should indicate where AI found specific information

**Current Behavior:**
- Route may fail due to complex async processing
- Authentication issues prevent testing via curl
- Existing code uses deprecated integration patterns

### 2. Workpaper Generation Not Working
**Status:** ❌ Broken  
**Description:** The workpaper generation functionality is not working properly.  
**Impact:** Users cannot create consolidated PDF workpapers from analyzed documents  
**Location:** Workpaper generation system  
**Priority:** Medium  

**Expected Behavior:**
- Users should be able to generate professional PDF workpapers
- Workpapers should include hierarchical bookmarks based on document categories
- Should consolidate multiple documents into a single organized PDF

**Current Behavior:**
- Workpaper generation may fail with errors
- Dependencies may be missing
- Integration with document analysis results may be broken

## 🟡 Investigation Status

### Document Visualization Issues
- [ ] Check document visualization routes and endpoints
- [ ] Verify Azure Document Intelligence integration
- [ ] Test document annotation overlay generation
- [ ] Validate file path handling and access
- [ ] Review frontend JavaScript for visualization

### Workpaper Generation Issues
- [ ] Check workpaper generation service availability
- [ ] Verify PDF generation library dependencies
- [ ] Test document consolidation functionality
- [ ] Review bookmark generation from AI analysis

## 📋 Action Plan

1. **Phase 1: Fix Document Visualization**
   - Investigate visualization endpoint functionality
   - Fix annotation overlay generation
   - Ensure proper document display with tick marks

2. **Phase 2: Fix Workpaper Generation**
   - Restore workpaper generation capabilities
   - Implement proper PDF creation with bookmarks
   - Test end-to-end workpaper workflow

## 🔧 Development Notes

- Current stable commit: `3243e21`
- Working in branch: `fix-document-visualization-and-workpaper`
- Access code for testing: `DEMO2024`
- Application URL: http://localhost:5000

---
*Last updated: June 11, 2025*