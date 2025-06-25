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
            except Exception as e:
                logging.warning(f"Failed to initialize Gemini: {e}")
                self.gemini_client = None
        else:
            self.gemini_client = None
    
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
            
            result = None
            successful_model = None
            last_error = None
            
            for model_id in models_to_try:
                try:
                    logging.info(f"Trying Azure model: {model_id}")
                    poller = self.azure_client.begin_analyze_document(
                        model_id=model_id,
                        body=BytesIO(document_content)
                    )
                    result = poller.result()
                    successful_model = model_id
                    logging.info(f"Successfully used Azure model: {model_id}")
                    break
                except Exception as e:
                    last_error = e
                    logging.warning(f"Azure model {model_id} failed: {str(e)}")
                    continue
            
            if not result:
                raise Exception(f"All Azure models failed. Last error: {str(last_error)}")
            
            # Convert to dictionary (from working version)
            result_dict = result.as_dict() if hasattr(result, 'as_dict') else self._serialize_azure_result(result)
            
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
                                    'key': field_name,
                                    'value': str(value)
                                })
            
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
            
            logging.info(f"Azure analysis completed in {response_time_ms:.2f}ms")
            return extracted_data
            
        except Exception as e:
            logging.error(f"Azure analysis failed: {str(e)}")
            raise Exception(f"Azure analysis failed: {str(e)}")
    
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
                        'fields': {}
                    }
                    if hasattr(doc, 'fields') and doc.fields:
                        for field_name, field_value in doc.fields.items():
                            if hasattr(field_value, 'value'):
                                doc_dict['fields'][field_name] = {'value': field_value.value}
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
            
            # Add analysis prompt (from working version)
            prompt = f"""Analyze this tax document and extract key information.

**Requirements:**
1. Identify document type (W-2, 1099-DIV, 1099-G, 1098-T, etc.)
2. Extract payer/recipient names and TINs
3. Extract all numbered box amounts (Box1, Box1a, Box2, etc.)
4. Identify tax withholdings (federal, state)
5. Note if document is corrected

**Important:**
- Extract amounts exactly as shown, including $0.00
- Only include visible information
- Use "Unknown" for missing fields
- Keep analysis summary under 200 words"""
            
            parts.append(prompt)
            
            # Use the correct API call from working version
            response = self.gemini_client.models.generate_content(
                model="gemini-1.5-flash",  # Use working model
                contents=parts,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    top_p=0.95,
                    top_k=32,
                    max_output_tokens=2048
                )
            )
            
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            
            # Parse the response
            if not response.text:
                raise ValueError("Empty response from Gemini API")
            
            analysis_text = response.text
            logging.info(f"Gemini analysis completed in {response_time_ms:.2f}ms")
            
            # Extract key findings from the analysis text (for frontend dropdown)
            key_findings = self._extract_key_findings(analysis_text)
            
            return {
                'service': 'gemini',
                'analysis_text': analysis_text,
                'document_type': self._extract_document_type(analysis_text),
                'confidence_score': 0.85,
                'summary': analysis_text[:500] + "..." if len(analysis_text) > 500 else analysis_text,
                'key_findings': key_findings,  # Added for frontend dropdown display
                'response_time_ms': response_time_ms
            }
                
        except Exception as e:
            logging.error(f"Gemini analysis failed: {str(e)}")
            raise Exception(f"Gemini analysis failed: {str(e)}")
    
    def _extract_document_type(self, text: str) -> str:
        """Extract document type from analysis text"""
        text_lower = text.lower()
        if 'tax' in text_lower or 'form' in text_lower:
            return 'tax_document'
        elif 'invoice' in text_lower or 'bill' in text_lower:
            return 'invoice'
        elif 'receipt' in text_lower:
            return 'receipt'
        elif 'contract' in text_lower or 'agreement' in text_lower:
            return 'contract'
        else:
            return 'general_document'
    
    def _extract_key_findings(self, text: str) -> list:
        """Extract key findings from Gemini analysis text with clean formatting"""
        findings = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for specific patterns that indicate key findings
            if any(keyword in line.lower() for keyword in [
                'box', 'amount', 'withheld', 'payer', 'recipient', 'tin', 'ein', 'ssn',
                'federal', 'state', 'income', 'tax', 'form', 'corrected', 'document type',
                'employer', 'employee', 'wages', 'medicare', 'social security'
            ]):
                # Clean up the line and remove markdown formatting and asterisks
                cleaned_line = line.replace('*', '').replace('#', '').replace('-', '').strip()
                
                # Remove asterisks from sensitive data (like TINs)
                cleaned_line = cleaned_line.replace('*', '')
                
                if cleaned_line and len(cleaned_line) > 10:  # Filter out very short lines
                    findings.append(cleaned_line)
        
        # Limit to most relevant findings
        return findings[:8]
    
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
        
        if azure_results:
            confidence_scores.append(azure_results.get('confidence_score', 0.8))
            combined['text_content'] = azure_results.get('text_content', '')
            combined['structured_data']['tables'] = azure_results.get('tables', [])
            combined['structured_data']['key_value_pairs'] = azure_results.get('key_value_pairs', [])
            combined['key_findings'].append("Azure: Structured data extraction completed")
        
        if gemini_results:
            confidence_scores.append(gemini_results.get('confidence_score', 0.8))
            combined['document_type'] = gemini_results.get('document_type', 'general_document')
            if gemini_results.get('summary'):
                combined['key_findings'].append(f"Gemini: {gemini_results['summary']}")
        
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
            'services_used': ['mock'],
            # Add frontend-expected fields for display
            'azure_results': {
                'key_value_pairs': [
                    {'key': 'Status', 'value': 'Mock Analysis'},
                    {'key': 'Document Type', 'value': 'Tax Document'},
                    {'key': 'Confidence', 'value': '50%'}
                ],
                'tables': [{'row_count': 1, 'column_count': 2, 'cells': []}],
                'text_content': 'Mock analysis - AI services not configured',
                'confidence_score': 0.5
            },
            'gemini_results': {
                'summary': 'This is mock analysis data. Configure AI services for real document analysis.',
                'document_type': 'tax_document',
                'confidence_score': 0.5,
                'key_findings': [
                    'Document Type: Mock Tax Document',
                    'Status: AI services not configured',
                    'Configure GEMINI_API_KEY for real analysis',
                    'Mock data for testing purposes'
                ]
            },
            'combined_analysis': {
                'document_type': 'general_document',
                'confidence_score': 0.5,
                'structured_data': {
                    'tables': [],
                    'key_value_pairs': [
                        {'key': 'Status', 'value': 'Mock Analysis'},
                        {'key': 'Note', 'value': 'Configure AI API keys for real analysis'}
                    ]
                }
            }
        }
    
    @staticmethod
    def save_analysis_results(document_id: int, results: Dict[str, Any]) -> bool:
        """Save analysis results to database session without committing. Caller must handle transaction."""
        try:
            document = ClientDocument.query.get(document_id)
            if document:
                document.ai_analysis_completed = True
                document.ai_analysis_results = json.dumps(results)
                document.ai_analysis_timestamp = datetime.utcnow()
                
                # Extract document type for easy querying
                if 'combined_analysis' in results and results['combined_analysis']:
                    combined = results['combined_analysis']
                    document.ai_document_type = combined.get('document_type', 'general_document')
                    document.ai_confidence_score = combined.get('confidence_score', 0.0)
                elif 'document_type' in results:
                    document.ai_document_type = results['document_type']
                    document.ai_confidence_score = results.get('confidence_score', 0.0)
                
                # Add to session but do not commit - caller handles transaction
                db.session.add(document)
                logging.info(f"Staged analysis results for document {document_id}")
                return True
            else:
                logging.error(f"Document {document_id} not found")
                return False
        except Exception as e:
            logging.error(f"Failed to save analysis results for document {document_id}: {e}")
            return False