"""
AI Service for document analysis using Azure Document Intelligence and Google Gemini
Based on working implementations from backend services
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
from io import BytesIO
import time

# AI service imports - only if available
try:
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.core.exceptions import HttpResponseError
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except (ImportError, Exception) as e:
    GEMINI_AVAILABLE = False
    logging.warning(f"Gemini not available: {e}")

from core import db
from models import ClientDocument


class AIService:
    """AI service for document analysis using Azure and/or Gemini"""
    
    def __init__(self, config=None):
        """Initialize AI service with configuration"""
        self.config = config
        self.azure_client = None
        self.gemini_client = None
        
        # Initialize Azure if available and configured (exact copy from working version)
        if (AZURE_AVAILABLE and config and 
            config.get('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT') and 
            config.get('AZURE_DOCUMENT_INTELLIGENCE_KEY')):
            try:
                self.azure_client = DocumentIntelligenceClient(
                    endpoint=config['AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT'],
                    credential=AzureKeyCredential(config['AZURE_DOCUMENT_INTELLIGENCE_KEY'])
                )
                logging.info("Azure Document Intelligence initialized successfully")
            except Exception as e:
                logging.warning(f"Failed to initialize Azure client: {e}")
                self.azure_client = None
        else:
            self.azure_client = None
        
        # Initialize Gemini if available and configured (exact copy from working version)
        if (GEMINI_AVAILABLE and config and 
            config.get('GEMINI_API_KEY')):
            try:
                self.gemini_client = genai.Client(api_key=config['GEMINI_API_KEY'])
                logging.info("Google Gemini initialized successfully")
                
                # Define structured output schema (from original working version)
                self.output_schema = types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "document_category": types.Schema(
                            type=types.Type.STRING,
                            description="Primary category or type of the document"
                        ),
                        "document_analysis_summary": types.Schema(
                            type=types.Type.STRING,
                            description="Professional analysis highlighting key tax-relevant information (max 200 words)"
                        ),
                        "extracted_key_info": types.Schema(
                            type=types.Type.OBJECT,
                            description="Flat structure with all extracted information as key-value pairs",
                            properties={
                                "tax_year": types.Schema(type=types.Type.STRING, description="Tax year"),
                                "form_type": types.Schema(type=types.Type.STRING, description="Form type"),
                                "payer_name": types.Schema(type=types.Type.STRING, description="Payer name"),
                                "payer_tin": types.Schema(type=types.Type.STRING, description="Payer TIN/EIN"),
                                "recipient_name": types.Schema(type=types.Type.STRING, description="Recipient name"),
                                "recipient_tin": types.Schema(type=types.Type.STRING, description="Recipient TIN/SSN"),
                                "box1": types.Schema(type=types.Type.STRING, description="Box 1 amount"),
                                "box2": types.Schema(type=types.Type.STRING, description="Box 2 amount"),
                                "box3": types.Schema(type=types.Type.STRING, description="Box 3 amount"),
                                "box4": types.Schema(type=types.Type.STRING, description="Box 4 amount"),
                                "box5": types.Schema(type=types.Type.STRING, description="Box 5 amount"),
                                "box6": types.Schema(type=types.Type.STRING, description="Box 6 amount"),
                                "box7": types.Schema(type=types.Type.STRING, description="Box 7 amount"),
                                "box8": types.Schema(type=types.Type.STRING, description="Box 8 amount"),
                                "box9": types.Schema(type=types.Type.STRING, description="Box 9 amount"),
                                "box1a": types.Schema(type=types.Type.STRING, description="Box 1a amount"),
                                "box1b": types.Schema(type=types.Type.STRING, description="Box 1b amount"),
                                "box2a": types.Schema(type=types.Type.STRING, description="Box 2a amount"),
                                "box2b": types.Schema(type=types.Type.STRING, description="Box 2b amount"),
                                "federal_tax_withheld": types.Schema(type=types.Type.STRING, description="Federal income tax withheld"),
                                "state_tax_withheld": types.Schema(type=types.Type.STRING, description="State tax withheld"),
                                "total_amount": types.Schema(type=types.Type.STRING, description="Main dollar amount"),
                                "is_corrected": types.Schema(type=types.Type.STRING, description="Corrected document")
                            }
                        ),
                        "suggested_bookmark_structure": types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "level1": types.Schema(type=types.Type.STRING, description="Category"),
                                "level2": types.Schema(type=types.Type.STRING, description="File Type"),
                                "level3": types.Schema(type=types.Type.STRING, description="Specifics")
                            },
                            required=["level1", "level2", "level3"]
                        )
                    },
                    required=["document_category", "document_analysis_summary", "extracted_key_info", "suggested_bookmark_structure"]
                )
                
            except Exception as e:
                logging.warning(f"Failed to initialize Gemini: {e}")
                self.gemini_client = None
                self.output_schema = None
        else:
            self.gemini_client = None
            self.output_schema = None
    
    def is_available(self) -> bool:
        """Check if any AI services are available"""
        return self.azure_client is not None or self.gemini_client is not None
    
    def analyze_document(self, document_path: str, document_id: int) -> Dict[str, Any]:
        """
        Analyze a document using available AI services
        
        Args:
            document_path: Path to the document file
            document_id: Database ID of the document
            
        Returns:
            Analysis results dictionary
        """
        if not self.is_available():
            return self._get_mock_results("No AI services configured")
        
        if not os.path.exists(document_path):
            return self._get_mock_results(f"File not found: {document_path}")
        
        results = {
            'document_id': document_id,
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'services_used': [],
            'azure_results': None,
            'gemini_results': None,
            'combined_analysis': {},
            'status': 'completed',
            'confidence_score': 0.0
        }
        
        # Try Azure analysis first
        if self.azure_client:
            try:
                azure_results = self._analyze_with_azure(document_path)
                results['azure_results'] = azure_results
                results['services_used'].append('azure')
                logging.info(f"Azure analysis completed for document {document_id}")
            except Exception as e:
                logging.error(f"Azure analysis failed for document {document_id}: {e}")
                results['azure_error'] = str(e)
        
        # Try Gemini analysis
        if self.gemini_client:
            try:
                gemini_results = self._analyze_with_gemini(document_path)
                results['gemini_results'] = gemini_results
                results['services_used'].append('gemini')
                logging.info(f"Gemini analysis completed for document {document_id}")
            except Exception as e:
                logging.error(f"Gemini analysis failed for document {document_id}: {e}")
                results['gemini_error'] = str(e)
        
        # Combine results if we have any
        if results['azure_results'] or results['gemini_results']:
            results['combined_analysis'] = self._combine_analysis_results(
                results.get('azure_results'), 
                results.get('gemini_results')
            )
            results['confidence_score'] = results['combined_analysis'].get('confidence_score', 0.8)
        else:
            # If both failed, return mock results
            return self._get_mock_results("AI analysis failed")
        
        return results
    
    def _analyze_with_azure(self, document_path: str) -> Dict[str, Any]:
        """Analyze document with Azure Document Intelligence - exact copy from working version"""
        start_time = time.time()
        
        try:
            # Read document content
            with open(document_path, 'rb') as f:
                document_content = f.read()
            
            logging.info(f"Starting Azure document analysis for: {document_path}")
            
            # Use tax-specific models first, then fallback to generic models
            models_to_try = [
                "prebuilt-tax.us.1099",      # Tax form 1099 variants
                "prebuilt-tax.us.w2",        # W-2 tax forms  
                "prebuilt-document",         # Generic document with fields
                "prebuilt-layout"            # Layout-only fallback
            ]
            analysis_result = None
            last_error = None
            successful_model = None
            
            for model_id in models_to_try:
                try:
                    logging.info(f"Trying Azure model: {model_id}")
                    poller = self.azure_client.begin_analyze_document(
                        model_id=model_id,
                        body=BytesIO(document_content)
                    )
                    analysis_result = poller.result()
                    successful_model = model_id
                    logging.info(f"✅ Successfully used Azure model: {model_id}")
                    break
                except Exception as e:
                    last_error = e
                    logging.warning(f"❌ Azure model {model_id} failed: {str(e)}")
                    continue
            
            if not analysis_result:
                raise Exception(f"All Azure models failed. Last error: {str(last_error)}")
            
            result = analysis_result
            
            # Convert to dictionary (from working version)
            result_dict = result.as_dict() if hasattr(result, 'as_dict') else self._serialize_azure_result(result)
            
            # Debug logging to see what Azure returns  
            logging.info(f"🔍 Azure model '{successful_model}' result structure:")
            logging.info(f"📄 Documents found: {len(result_dict.get('documents', []))}")
            logging.info(f"📊 Tables found: {len(result_dict.get('tables', []))}")
            if result_dict.get('documents'):
                doc = result_dict['documents'][0]
                fields_count = len(doc.get('fields', {}))
                logging.info(f"🔑 Fields found: {fields_count}")
                if fields_count > 0:
                    field_names = list(doc.get('fields', {}).keys())[:5]  # Show first 5
                    logging.info(f"📝 Sample fields: {field_names}")
            logging.info(f"Raw structure preview: {json.dumps(result_dict, indent=2, default=str)[:500]}...")
            
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            
            # Extract key information from Azure results (format for frontend)
            extracted_data = {
                'service': 'azure',
                'model_id': successful_model or 'unknown',
                'documents_found': len(result_dict.get('documents', [])),
                'tables': [],
                'key_value_pairs': [],  # Array format for frontend
                'text_content': '',
                'confidence_score': 0.9,
                'response_time_ms': response_time_ms
            }
            
            # Extract content from first document
            documents = result_dict.get('documents', [])
            if documents:
                doc = documents[0]
                extracted_data['text_content'] = doc.get('content', '')
                
                # Extract document type from Azure (original working version)
                doc_type = doc.get('docType', doc.get('doc_type', ''))
                if doc_type:
                    # Convert Azure docType to clean form name (us.tax.1099G → 1099-G)
                    extracted_data['document_type'] = self._clean_azure_doc_type(doc_type)
                
                # Extract fields as key-value pairs (as array)
                if 'fields' in doc:
                    for field_name, field_data in doc['fields'].items():
                        if isinstance(field_data, dict):
                            # Handle different Azure field value formats
                            value = None
                            if 'value' in field_data:
                                value = field_data['value']
                            elif 'content' in field_data:
                                value = field_data['content']
                            elif 'valueString' in field_data:
                                value = field_data['valueString']
                            elif 'valueNumber' in field_data:
                                value = field_data['valueNumber']
                            elif 'valueDate' in field_data:
                                value = field_data['valueDate']
                            
                            if value is not None:
                                extracted_data['key_value_pairs'].append({
                                    'key': self._clean_field_name(field_name),
                                    'value': str(value)
                                })
                
                # If no fields found, try to extract from tables (fallback for layout-only models)
                if len(extracted_data['key_value_pairs']) == 0 and 'tables' in result_dict:
                    logging.info("🔄 No structured fields found, attempting table-based extraction...")
                    table_fields = self._extract_fields_from_tables(result_dict['tables'])
                    extracted_data['key_value_pairs'].extend(table_fields)
                    logging.info(f"📊 Extracted {len(table_fields)} fields from table analysis")
            
            # Extract tables from result
            if 'tables' in result_dict:
                for table in result_dict['tables']:
                    table_data = {
                        'row_count': table.get('rowCount', 0),
                        'column_count': table.get('columnCount', 0),
                        'cells': []
                    }
                    for cell in table.get('cells', []):
                        table_data['cells'].append({
                            'content': cell.get('content', ''),
                            'row_index': cell.get('rowIndex', 0),
                            'column_index': cell.get('columnIndex', 0)
                        })
                    extracted_data['tables'].append(table_data)
            
            # Final extraction summary
            fields_extracted = len(extracted_data['key_value_pairs'])
            tables_extracted = len(extracted_data['tables'])
            logging.info(f"✅ Azure analysis completed in {response_time_ms:.2f}ms")
            logging.info(f"📊 Final extraction: {fields_extracted} fields, {tables_extracted} tables")
            if fields_extracted > 0:
                sample_fields = [f"{field['key']}: {field['value'][:30]}..." 
                                for field in extracted_data['key_value_pairs'][:3]]
                logging.info(f"📝 Sample extracted fields: {sample_fields}")
            
            return extracted_data
            
        except Exception as e:
            logging.error(f"Azure analysis failed: {str(e)}")
            raise Exception(f"Azure analysis failed: {str(e)}")
    
    def _clean_azure_doc_type(self, doc_type: str) -> str:
        """Convert Azure docType to clean form name"""
        # Handle Azure tax document types (us.tax.1099G → 1099-G)
        if doc_type.startswith('us.tax.'):
            form_type = doc_type.replace('us.tax.', '')
            if form_type.upper() == 'W2':
                return 'W-2'
            elif len(form_type) == 5 and form_type[:4].isdigit():  # 1099G, 1098T
                return f"{form_type[:4]}-{form_type[4:].upper()}"
            elif len(form_type) >= 4 and form_type[:4].isdigit():  # 1099DIV, 1099MISC
                return f"{form_type[:4]}-{form_type[4:].upper()}"
            else:
                return form_type.upper()
        
        # Fallback for other formats
        return doc_type
    
    def _clean_field_name(self, field_name: str) -> str:
        """Convert Azure field names to human-readable format"""
        # Convert camelCase and specific field names to readable format
        cleaned = field_name.replace('_', ' ').replace('.', ' ')
        
        # Handle common tax field names
        field_mappings = {
            'Employee': 'Employee Name',
            'EmployerName': 'Employer Name',
            'EmployerAddress': 'Employer Address',
            'EmployerEIN': 'Employer EIN',
            'WagesTipsAndOtherCompensation': 'Wages, Tips & Other Compensation',
            'FederalIncomeTaxWithheld': 'Federal Income Tax Withheld',
            'SocialSecurityWages': 'Social Security Wages',
            'SocialSecurityTaxWithheld': 'Social Security Tax Withheld',
            'MedicareWagesAndTips': 'Medicare Wages and Tips',
            'MedicareTaxWithheld': 'Medicare Tax Withheld',
            'SocialSecurityTips': 'Social Security Tips',
            'AllocatedTips': 'Allocated Tips',
            'DependentCareBenefits': 'Dependent Care Benefits',
            'NonqualifiedPlans': 'Nonqualified Plans',
            'StateTaxWithheld': 'State Tax Withheld',
            'StateWages': 'State Wages',
            'Payer': 'Payer Name',
            'PayerAddress': 'Payer Address',
            'PayerTIN': 'Payer TIN',
            'Recipient': 'Recipient Name',
            'RecipientTIN': 'Recipient TIN',
            'RecipientAddress': 'Recipient Address'
        }
        
        return field_mappings.get(field_name, cleaned.title())
    
    def _extract_fields_from_tables(self, tables: list) -> list:
        """Extract key-value pairs from Azure table data when structured fields aren't available"""
        extracted_fields = []
        
        for table in tables:
            cells = table.get('cells', [])
            row_count = table.get('rowCount', 0)
            col_count = table.get('columnCount', 0)
            
            # Create a grid structure from cells
            grid = {}
            for cell in cells:
                row_idx = cell.get('rowIndex', 0)
                col_idx = cell.get('columnIndex', 0)
                content = cell.get('content', '').strip()
                grid[(row_idx, col_idx)] = content
            
            # Strategy 1: Look for key-value patterns in adjacent cells
            for row in range(row_count):
                for col in range(col_count - 1):  # Avoid out of bounds
                    left_cell = grid.get((row, col), '')
                    right_cell = grid.get((row, col + 1), '')
                    
                    # Check if left cell looks like a field name and right cell like a value
                    if self._is_field_name(left_cell) and self._is_field_value(right_cell):
                        extracted_fields.append({
                            'key': self._clean_field_name(left_cell),
                            'value': right_cell
                        })
            
            # Strategy 2: Look for vertical patterns (label above value)
            for row in range(row_count - 1):  # Avoid out of bounds
                for col in range(col_count):
                    top_cell = grid.get((row, col), '')
                    bottom_cell = grid.get((row + 1, col), '')
                    
                    # Check if top cell is label and bottom is value
                    if self._is_field_name(top_cell) and self._is_field_value(bottom_cell):
                        # Avoid duplicates
                        field_key = self._clean_field_name(top_cell)
                        if not any(field['key'] == field_key for field in extracted_fields):
                            extracted_fields.append({
                                'key': field_key,
                                'value': bottom_cell
                            })
        
        return extracted_fields
    
    def _is_field_name(self, text: str) -> bool:
        """Check if text looks like a field name/label"""
        if not text or len(text) < 2:
            return False
        
        # Common field indicators
        field_indicators = [
            'name', 'address', 'ein', 'ssn', 'wage', 'tip', 'tax', 'withh', 'fed', 'state',
            'payer', 'recipient', 'employer', 'employee', 'box', 'amount', 'income', 'total'
        ]
        
        text_lower = text.lower().replace(':', '').replace('.', '').strip()
        
        # Check if it contains field indicators
        if any(indicator in text_lower for indicator in field_indicators):
            return True
        
        # Check if it looks like "Box 1", "Line 2a", etc.
        if text_lower.startswith(('box ', 'line ', 'form ', 'part ')):
            return True
        
        # Check if it ends with colon (common for labels)
        if text.endswith(':'):
            return True
        
        return False
    
    def _is_field_value(self, text: str) -> bool:
        """Check if text looks like a field value"""
        if not text or len(text.strip()) < 1:
            return False
        
        text = text.strip()
        
        # Don't treat obvious labels as values
        if text.endswith(':'):
            return False
        
        # Don't treat very short text as values unless it's a number
        if len(text) < 2 and not text.isdigit():
            return False
        
        # Common non-value patterns to avoid
        avoid_patterns = ['form', 'copy', 'void', 'corrected', 'draft']
        if text.lower() in avoid_patterns:
            return False
        
        return True
    
    def _serialize_azure_result(self, result) -> Dict[str, Any]:
        """Serialize Azure result to dictionary (from working version)"""
        try:
            # Basic serialization for Azure Document Intelligence results
            serialized = {
                'model_id': getattr(result, 'model_id', 'unknown'),
                'documents': [],
                'tables': []
            }
            
            # Serialize documents
            if hasattr(result, 'documents') and result.documents:
                for doc in result.documents:
                    doc_dict = {
                        'content': getattr(doc, 'content', ''),
                        'docType': getattr(doc, 'doc_type', ''),
                        'fields': {}
                    }
                    if hasattr(doc, 'fields') and doc.fields:
                        for field_name, field_value in doc.fields.items():
                            # Handle different field value formats
                            field_dict = {}
                            if hasattr(field_value, 'value'):
                                field_dict['value'] = field_value.value
                            if hasattr(field_value, 'content'):
                                field_dict['content'] = field_value.content
                            if hasattr(field_value, 'value_string'):
                                field_dict['valueString'] = field_value.value_string
                            if hasattr(field_value, 'value_number'):
                                field_dict['valueNumber'] = field_value.value_number
                            if hasattr(field_value, 'value_date'):
                                field_dict['valueDate'] = str(field_value.value_date)
                            if hasattr(field_value, 'bounding_regions'):
                                field_dict['boundingRegions'] = []
                                for region in field_value.bounding_regions:
                                    if hasattr(region, 'polygon'):
                                        field_dict['boundingRegions'].append({
                                            'polygon': region.polygon
                                        })
                            
                            doc_dict['fields'][field_name] = field_dict
                    serialized['documents'].append(doc_dict)
            
            # Serialize tables
            if hasattr(result, 'tables') and result.tables:
                for table in result.tables:
                    table_dict = {
                        'rowCount': getattr(table, 'row_count', 0),
                        'columnCount': getattr(table, 'column_count', 0),
                        'cells': []
                    }
                    if hasattr(table, 'cells') and table.cells:
                        for cell in table.cells:
                            cell_dict = {
                                'content': getattr(cell, 'content', ''),
                                'rowIndex': getattr(cell, 'row_index', 0),
                                'columnIndex': getattr(cell, 'column_index', 0)
                            }
                            table_dict['cells'].append(cell_dict)
                    serialized['tables'].append(table_dict)
            
            return serialized
            
        except Exception as e:
            logging.warning(f"Failed to serialize Azure result: {e}")
            return {'model_id': 'unknown', 'documents': [], 'tables': []}
    
    def _analyze_with_gemini(self, document_path: str) -> Dict[str, Any]:
        """Analyze document with Google Gemini - based on working implementation"""
        start_time = time.time()
        
        try:
            logging.info(f"Starting Gemini analysis for: {os.path.basename(document_path)}")
            
            # Read document content as bytes (from working version)
            with open(document_path, 'rb') as f:
                document_content = f.read()
            
            # Determine content type
            file_ext = document_path.lower().split('.')[-1]
            if file_ext in ['png', 'jpg', 'jpeg']:
                content_type = f"image/{file_ext}"
            elif file_ext == 'pdf':
                content_type = "application/pdf"
            elif file_ext == 'txt':
                content_type = "text/plain"
            else:
                content_type = "application/octet-stream"
            
            # Prepare the content for Gemini (exact copy from working version)
            parts = []
            
            if content_type.startswith('image/') or content_type == 'application/pdf':
                # Handle image/PDF formats - send actual binary data (from working version)
                parts.append(types.Part.from_bytes(
                    data=document_content,
                    mime_type=content_type
                ))
            else:
                # Handle text files
                content_text = document_content.decode('utf-8', errors='ignore')
                parts.append(f"Document content:\n{content_text[:2000]}")
            
            # Add analysis prompt (exact original working version)
            prompt = f"""Analyze this tax document '{os.path.basename(document_path)}' and extract key information.

**Requirements:**
1. Identify document type (W-2, 1099-DIV, 1099-G, etc.)
2. Extract payer/recipient names and TINs
3. Extract all numbered box amounts (Box1, Box1a, Box2, etc.)
4. Identify tax withholdings (federal, state)
5. Note if document is corrected

**For Bookmark Structure:**
- Level 1: Choose from "Income Documents", "Deduction Documents", "Investment Documents", "Business Documents", "Other Tax Documents"  
- Level 2: Specific form type (e.g., "1099-DIV", "W-2")
- Level 3: Include payer name (e.g., "1099-DIV - Bank Name")

**Important:**
- Extract amounts exactly as shown, including $0.00
- Only include visible information
- Use "Unknown" for missing fields
- Keep analysis summary under 200 words

Provide structured JSON response with all extracted information."""
            
            parts.append(prompt)
            
            # Use structured JSON output (exact original working version)
            response = self.gemini_client.models.generate_content(
                model="gemini-1.5-flash",  # Use working model
                contents=parts,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    top_p=0.95,
                    top_k=32,
                    max_output_tokens=4096,
                    response_mime_type="application/json",
                    response_schema=self.output_schema
                )
            )
            
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            
            # Parse JSON response (original working version)
            if not response.text:
                raise ValueError("Empty response from Gemini API")
            
            try:
                result = json.loads(response.text)
                logging.info(f"Gemini analysis completed in {response_time_ms:.2f}ms")
                
                # Extract key findings from structured data
                key_findings = self._extract_structured_key_findings(result.get('extracted_key_info', {}))
                
                # Return in format expected by frontend
                return {
                    'service': 'gemini',
                    'analysis_text': response.text,
                    'document_type': result.get('extracted_key_info', {}).get('form_type', result.get('document_category', 'Unknown')),
                    'confidence_score': 0.85,
                    'summary': result.get('document_analysis_summary', ''),
                    'response_time_ms': response_time_ms,
                    'key_findings': key_findings,
                    'extracted_key_info': result.get('extracted_key_info', {}),
                    'suggested_bookmark_structure': result.get('suggested_bookmark_structure', {})
                }
                
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON response: {e}")
                # Fallback to raw text processing
                analysis_text = response.text
                key_findings = self._extract_key_findings(analysis_text)
                
                return {
                    'service': 'gemini',
                    'analysis_text': analysis_text,
                    'document_type': 'Unknown',
                    'confidence_score': 0.7,
                    'summary': analysis_text[:500] + "..." if len(analysis_text) > 500 else analysis_text,
                    'response_time_ms': response_time_ms,
                    'key_findings': key_findings
                }
                
        except Exception as e:
            logging.error(f"Gemini analysis failed: {str(e)}")
            raise Exception(f"Gemini analysis failed: {str(e)}")
    
    def _extract_key_findings(self, text: str) -> list:
        """Extract key findings from Gemini analysis text and remove markdown formatting"""
        findings = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for specific patterns that indicate key findings
            if any(keyword in line.lower() for keyword in [
                'box', 'amount', 'withheld', 'payer', 'recipient', 'tin', 'ein', 'ssn',
                'federal', 'state', 'income', 'tax', 'form', 'corrected'
            ]):
                # Clean up the line and remove markdown formatting
                cleaned_line = line.replace('**', '').replace('*', '')  # Remove asterisks
                cleaned_line = cleaned_line.replace('###', '').replace('##', '').replace('#', '')  # Remove hash marks
                
                if ':' in cleaned_line:
                    findings.append(cleaned_line)
                elif cleaned_line.startswith('-') or cleaned_line.startswith('•'):
                    findings.append(cleaned_line)
                elif any(char.isdigit() for char in cleaned_line) and '$' in cleaned_line:
                    findings.append(cleaned_line)
        
        # Limit to most relevant findings
        return findings[:8]
    
    def _extract_structured_key_findings(self, extracted_info: Dict[str, Any]) -> list:
        """Extract key findings from structured Gemini response"""
        findings = []
        
        # Extract key information in order of importance
        if extracted_info.get('payer_name') and extracted_info.get('payer_name') != 'Unknown':
            findings.append(f"Payer: {extracted_info['payer_name']}")
        
        if extracted_info.get('recipient_name') and extracted_info.get('recipient_name') != 'Unknown':
            findings.append(f"Recipient: {extracted_info['recipient_name']}")
        
        if extracted_info.get('payer_tin') and extracted_info.get('payer_tin') != 'Unknown':
            findings.append(f"Payer TIN: {extracted_info['payer_tin']}")
        
        if extracted_info.get('recipient_tin') and extracted_info.get('recipient_tin') != 'Unknown':
            findings.append(f"Recipient TIN: {extracted_info['recipient_tin']}")
        
        # Extract box amounts
        for i in range(1, 10):
            box_key = f'box{i}'
            if extracted_info.get(box_key) and extracted_info.get(box_key) != 'Unknown':
                findings.append(f"Box {i}: {extracted_info[box_key]}")
        
        # Extract sub-boxes
        for box in ['1a', '1b', '2a', '2b']:
            box_key = f'box{box}'
            if extracted_info.get(box_key) and extracted_info.get(box_key) != 'Unknown':
                findings.append(f"Box {box}: {extracted_info[box_key]}")
        
        # Extract tax withholdings
        if extracted_info.get('federal_tax_withheld') and extracted_info.get('federal_tax_withheld') != 'Unknown':
            findings.append(f"Federal Tax Withheld: {extracted_info['federal_tax_withheld']}")
        
        if extracted_info.get('state_tax_withheld') and extracted_info.get('state_tax_withheld') != 'Unknown':
            findings.append(f"State Tax Withheld: {extracted_info['state_tax_withheld']}")
        
        return findings[:8]  # Limit to most relevant
    
    def _extract_document_type(self, text: str) -> str:
        """Extract document type from analysis text (original working version)"""
        text_lower = text.lower()
        if 'tax' in text_lower or 'form' in text_lower or '1099' in text_lower or '1098' in text_lower or 'w-2' in text_lower:
            return 'tax_document'
        elif 'invoice' in text_lower or 'bill' in text_lower:
            return 'invoice'
        elif 'receipt' in text_lower:
            return 'receipt'
        elif 'contract' in text_lower or 'agreement' in text_lower:
            return 'contract'
        else:
            return 'general_document'
    
    def _combine_analysis_results(self, azure_results: Optional[Dict], gemini_results: Optional[Dict]) -> Dict[str, Any]:
        """Combine Azure and Gemini analysis results"""
        combined = {
            'document_type': 'general_document',
            'confidence_score': 0.0,
            'key_findings': [],
            'text_content': '',
            'structured_data': {}
        }
        
        # Combine confidence scores
        confidence_scores = []
        
        # Determine document type (prefer Azure if available)
        document_type = 'general_document'
        
        if azure_results:
            confidence_scores.append(azure_results.get('confidence_score', 0.8))
            combined['text_content'] = azure_results.get('text_content', '')
            combined['structured_data']['tables'] = azure_results.get('tables', [])
            combined['structured_data']['key_value_pairs'] = azure_results.get('key_value_pairs', [])
            combined['key_findings'].append("Azure: Structured data extraction completed")
            
            # Prefer Azure document type if available
            if azure_results.get('document_type'):
                document_type = azure_results['document_type']
        
        if gemini_results:
            confidence_scores.append(gemini_results.get('confidence_score', 0.8))
            # Use Gemini document type as fallback
            if document_type == 'general_document':
                document_type = gemini_results.get('document_type', 'general_document')
            if gemini_results.get('summary'):
                combined['key_findings'].append(f"Gemini: {gemini_results['summary']}")
        
        combined['document_type'] = document_type
        
        # Average confidence if we have multiple services
        if confidence_scores:
            combined['confidence_score'] = sum(confidence_scores) / len(confidence_scores)
        
        return combined
    
    def _get_mock_results(self, reason: str) -> Dict[str, Any]:
        """Generate mock results when AI services are not available"""
        return {
            'document_type': 'general_document',
            'confidence_score': 0.5,
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'status': 'mock',
            'reason': reason,
            'mock_data': {
                'extracted_text': 'Mock text content - AI services not configured',
                'key_findings': [
                    'Document uploaded successfully',
                    'AI analysis would provide detailed insights with proper API keys',
                    'Configure Azure and/or Gemini API keys in .env file for real analysis'
                ]
            },
            'services_used': ['mock']
        }
    
    @staticmethod
    def save_analysis_results(document_id: int, results: Dict[str, Any]) -> bool:
        """Save analysis results to database"""
        try:
            document = ClientDocument.query.get(document_id)
            if document:
                # Ensure we have the latest version of the document
                db.session.refresh(document)
                document.ai_analysis_completed = True
                document.ai_analysis_results = json.dumps(results)
                document.ai_analysis_timestamp = datetime.utcnow()
                
                # Extract document type for easy querying
                if 'combined_analysis' in results:
                    document.ai_document_type = results['combined_analysis'].get('document_type', 'general_document')
                    document.ai_confidence_score = results['combined_analysis'].get('confidence_score', 0.0)
                elif 'document_type' in results:
                    document.ai_document_type = results['document_type']
                    document.ai_confidence_score = results.get('confidence_score', 0.0)
                
                db.session.commit()
                logging.info(f"✅ Successfully saved analysis results for document {document_id}")
                logging.info(f"📊 Document type: {document.ai_document_type}, Confidence: {document.ai_confidence_score}")
                return True
            else:
                logging.error(f"Document {document_id} not found")
                return False
        except Exception as e:
            logging.error(f"Failed to save analysis results for document {document_id}: {e}")
            db.session.rollback()
            return False