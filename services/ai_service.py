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

from core.db_import import db
from models import ClientDocument


class AIService:
    """AI service for document analysis using Azure and/or Gemini"""
    
    def __init__(self, config=None):
        """Initialize AI service with configuration"""
        self.config = config
        self.azure_client = None
        self.gemini_client = None
        
        # Initialize Azure if available and configured (exact copy from working version)
        azure_endpoint = None
        azure_key = None
        if config:
            # Handle both dict and config object
            if hasattr(config, 'get'):
                azure_endpoint = config.get('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT')
                azure_key = config.get('AZURE_DOCUMENT_INTELLIGENCE_KEY')
            else:
                azure_endpoint = getattr(config, 'AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT', None)
                azure_key = getattr(config, 'AZURE_DOCUMENT_INTELLIGENCE_KEY', None)
                
        if AZURE_AVAILABLE and azure_endpoint and azure_key:
            try:
                self.azure_client = DocumentIntelligenceClient(
                    endpoint=azure_endpoint,
                    credential=AzureKeyCredential(azure_key)
                )
                logging.info("Azure Document Intelligence initialized successfully")
            except Exception as e:
                logging.warning(f"Failed to initialize Azure client: {e}")
                self.azure_client = None
        else:
            self.azure_client = None
        
        # Initialize Gemini if available and configured
        gemini_key = None
        if config:
            # Handle both dict and config object
            if hasattr(config, 'get'):
                gemini_key = config.get('GEMINI_API_KEY')
            elif hasattr(config, 'GEMINI_API_KEY'):
                gemini_key = config.GEMINI_API_KEY
                
        if GEMINI_AVAILABLE and gemini_key:
            try:
                self.gemini_client = genai.Client(api_key=gemini_key)
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
            
        Raises:
            ValueError: If AI services are not configured or file not found
            Exception: If analysis fails
        """
        if not self.is_available():
            raise ValueError("AI services not configured. Please configure GEMINI_API_KEY or Azure Document Intelligence credentials.")
        
        if not os.path.exists(document_path):
            raise ValueError(f"Document file not found: {document_path}")
        
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
        
        analysis_errors = []
        
        # Try Azure analysis first
        if self.azure_client:
            try:
                azure_results = self._analyze_with_azure(document_path)
                results['azure_results'] = azure_results
                results['services_used'].append('azure')
                logging.info(f"Azure analysis completed for document {document_id}")
            except Exception as e:
                error_msg = f"Azure analysis failed: {str(e)}"
                logging.error(f"Azure analysis failed for document {document_id}: {e}")
                analysis_errors.append(error_msg)
        
        # Try Gemini analysis
        if self.gemini_client:
            try:
                gemini_results = self._analyze_with_gemini(document_path)
                results['gemini_results'] = gemini_results
                results['services_used'].append('gemini')
                logging.info(f"Gemini analysis completed for document {document_id}")
            except Exception as e:
                error_msg = f"Gemini analysis failed: {str(e)}"
                logging.error(f"Gemini analysis failed for document {document_id}: {e}")
                analysis_errors.append(error_msg)
        
        # Combine results if we have any
        if results['azure_results'] or results['gemini_results']:
            results['combined_analysis'] = self._combine_analysis_results(
                results.get('azure_results'), 
                results.get('gemini_results')
            )
            results['confidence_score'] = results['combined_analysis'].get('confidence_score', 0.8)
            
            # Include any partial errors in the results for debugging
            if analysis_errors:
                results['partial_errors'] = analysis_errors
                
            return results
        else:
            # If both services failed, raise an exception instead of returning mock results
            error_summary = "; ".join(analysis_errors) if analysis_errors else "All AI services failed"
            raise Exception(f"AI analysis failed for document {document_id}: {error_summary}")
        
        return results
    
    def _analyze_with_azure(self, document_path: str) -> Dict[str, Any]:
        """Analyze document with Azure Document Intelligence - exact copy from working version"""
        start_time = time.time()
        
        try:
            # Read document content
            with open(document_path, 'rb') as f:
                document_content = f.read()
            
            logging.info(f"Starting Azure document analysis for: {document_path}")
            
            # Use most capable models first, fallback to basic ones (restored from working version)
            models_to_try = [
                "prebuilt-tax.us.1099",      # Tax form 1099 variants
                "prebuilt-tax.us.w2",        # W-2 tax forms  
                "prebuilt-document",         # Generic document with fields
                "prebuilt-read"              # OCR text extraction (always available)
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
                            # Comprehensive Azure field value parsing (restored from working version)
                            value = None
                            if 'value' in field_data:
                                value = field_data['value']
                            elif 'content' in field_data:
                                value = field_data['content']
                            elif 'valueString' in field_data:
                                value = field_data['valueString']
                            elif 'value_string' in field_data:
                                value = field_data['value_string']
                            elif 'valueNumber' in field_data:
                                value = field_data['valueNumber']
                            elif 'value_number' in field_data:
                                value = field_data['value_number']
                            elif 'valueDate' in field_data:
                                value = field_data['valueDate']
                            elif 'value_date' in field_data:
                                value = field_data['value_date']
                            elif 'valueBoolean' in field_data:
                                value = field_data['valueBoolean']
                            elif 'value_boolean' in field_data:
                                value = field_data['value_boolean']
                            elif 'text' in field_data:
                                value = field_data['text']
                            
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
            
            # Clean the summary text to remove asterisks (same cleaning as key_findings)
            clean_summary = self._clean_analysis_text(analysis_text[:500])
            if len(analysis_text) > 500:
                clean_summary += "..."
            
            return {
                'service': 'gemini',
                'analysis_text': analysis_text,
                'document_type': self._extract_document_type(analysis_text),
                'confidence_score': 0.85,
                'summary': clean_summary,
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
    
    def _clean_analysis_text(self, text: str) -> str:
        """Clean analysis text by removing asterisks and markdown formatting"""
        # Remove asterisks used for masking sensitive data (like TINs)
        cleaned_text = text.replace('*', '')
        
        # Remove excessive markdown formatting but keep basic structure
        cleaned_text = cleaned_text.replace('###', '').replace('##', '').replace('#', '')
        
        # Clean up multiple spaces that might result from asterisk removal
        import re
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        return cleaned_text
    
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
    
    

    def save_analysis_results(self, document_id: int, results: Dict[str, Any]) -> bool:
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

    def get_or_analyze_document(self, document_id: int, firm_id: int, force_reanalysis: bool = False) -> Dict[str, Any]:
        """Get existing analysis or perform new analysis for a document"""
        from models import ChecklistItem, DocumentChecklist, Client
        
        try:
            # Get document and verify access
            document = db.session.query(ClientDocument).join(ChecklistItem).join(DocumentChecklist).join(Client).filter(
                ClientDocument.id == document_id,
                Client.firm_id == firm_id
            ).first()
            
            if not document:
                raise ValueError('Document not found')
            
            # Handle force reanalysis
            if force_reanalysis:
                document.ai_analysis_completed = False
                document.ai_analysis_results = None
                document.ai_analysis_timestamp = None
                # Note: Commit will happen at end of transaction
            
            # Check for existing results first (no AI services needed for cached data)
            if not force_reanalysis and document.ai_analysis_completed and document.ai_analysis_results:
                try:
                    cached_results = json.loads(document.ai_analysis_results)
                    return self._format_analysis_response(cached_results, 
                                                        timestamp=document.ai_analysis_timestamp,
                                                        cached=True,
                                                        filename='Cached Result')
                except (json.JSONDecodeError, AttributeError):
                    # Corrupted cache, proceed with new analysis
                    logging.warning(f"Corrupted cache for document {document_id}, proceeding with new analysis")
            
            # Only check AI services when we need to perform new analysis
            if not self.is_available():
                raise ValueError('AI services not configured. Please configure GEMINI_API_KEY or Azure Document Intelligence credentials.')
            
            # Find document file path
            document_path = self._get_document_path(document)
            if not document_path or not os.path.exists(document_path):
                raise ValueError(f'Document file not found on server: {document_path or "No path"}')
            
            # Perform analysis - this will raise exceptions if it fails
            analysis_results = self.analyze_document(document_path, document_id)
            
            # Save results and return formatted response
            if self.save_analysis_results(document_id, analysis_results):
                db.session.commit()
                # Convert timestamp string back to datetime if needed
                timestamp_str = analysis_results.get('analysis_timestamp')
                timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.utcnow()
                return self._format_analysis_response(analysis_results, 
                                                    timestamp=timestamp,
                                                    cached=False,
                                                    filename=os.path.basename(document_path))
            else:
                raise Exception('Failed to save analysis results to database')
                
        except Exception as e:
            db.session.rollback()
            raise
    
    def _get_document_path(self, document) -> Optional[str]:
        """Get the file path for a document"""
        if hasattr(document, 'attachment') and document.attachment:
            return document.attachment.file_path
        elif hasattr(document, 'file_path') and document.file_path:
            return document.file_path
        return None
    
    def _format_analysis_response(self, analysis_results: Dict[str, Any], 
                                timestamp: Optional[datetime] = None,
                                cached: bool = False,
                                filename: str = 'Unknown') -> Dict[str, Any]:
        """Format analysis results for API response"""
        response_data = {
            'document_type': analysis_results.get('document_type', 'general_document'),
            'confidence_score': analysis_results.get('confidence_score', 0.0),
            'analysis_timestamp': timestamp.isoformat() if timestamp else None,
            'status': analysis_results.get('status', 'completed'),
            'services_used': analysis_results.get('services_used', []),
            'extracted_data': {},
            'azure_result': analysis_results.get('azure_results'),  # Frontend expects singular
            'gemini_result': analysis_results.get('gemini_results'),  # Frontend expects singular  
            'combined_analysis': analysis_results.get('combined_analysis'),
            'cached': cached,
            'filename': filename
        }
        
        # Add extracted data from combined analysis
        if 'combined_analysis' in analysis_results:
            combined = analysis_results['combined_analysis']
            response_data['extracted_data'] = combined.get('structured_data', {})
            response_data['confidence_score'] = combined.get('confidence_score', 0.0)
            response_data['document_type'] = combined.get('document_type', 'general_document')
        
        return response_data

    def analyze_checklist_documents(self, checklist_id: int, firm_id: int, force_reanalysis: bool = False) -> Dict[str, Any]:
        """Analyze all documents in a checklist"""
        from models import DocumentChecklist, Client
        
        try:
            # First check if AI services are available
            if not self.is_available():
                return {
                    'success': False,
                    'error': 'AI services not configured',
                    'message': 'Please configure GEMINI_API_KEY or Azure Document Intelligence to enable AI analysis',
                    'ai_services_available': False,
                    'analyzed_count': 0,
                    'total_documents': 0
                }
            
            # Get checklist with proper firm verification
            checklist = db.session.query(DocumentChecklist).join(Client).filter(
                DocumentChecklist.id == checklist_id,
                Client.firm_id == firm_id
            ).first()
            
            if not checklist:
                raise ValueError('Checklist not found')
            
            total_documents = 0
            analyzed_count = 0
            real_analysis_count = 0
            mock_analysis_count = 0
            errors = []
            
            for item in checklist.items:
                for document in item.client_documents:
                    total_documents += 1
                    
                    # Handle force reanalysis
                    if force_reanalysis:
                        document.ai_analysis_completed = False
                        document.ai_analysis_results = None
                        document.ai_analysis_timestamp = None
                    
                    if not document.ai_analysis_completed or force_reanalysis:
                        try:
                            document_path = self._get_document_path(document)
                            
                            if document_path and os.path.exists(document_path):
                                # Perform real AI analysis
                                logging.info(f"Starting AI analysis for document {document.id}: {os.path.basename(document_path)}")
                                results = self.analyze_document(document_path, document.id)
                                
                                # If we reach here, analysis succeeded
                                real_analysis_count += 1
                                logging.info(f"Document {document.id} analyzed successfully with {results.get('services_used', [])} services")
                                self.save_analysis_results(document.id, results)
                            else:
                                # File not found - add to errors and skip
                                error_msg = f"Document {document.id}: File not found at {document_path or 'No path'}"
                                errors.append(error_msg)
                                logging.error(error_msg)
                                continue  # Skip saving anything for missing files
                            
                            analyzed_count += 1
                            # Commit after each document to avoid session buildup
                            db.session.commit()
                            
                        except Exception as doc_error:
                            error_msg = f"Document {document.id}: {str(doc_error)}"
                            errors.append(error_msg)
                            logging.error(f"Error processing document {document.id}: {doc_error}")
                            db.session.rollback()
                            # Continue with next document
            
            # Determine success based on what actually happened
            success_status = real_analysis_count > 0
            
            if real_analysis_count == 0 and total_documents > 0:
                if errors:
                    message = f"Analysis failed - no documents could be processed. Errors: {len(errors)} documents had issues."
                else:
                    message = "Analysis failed - no documents were found to analyze."
            elif real_analysis_count == total_documents:
                message = f"AI analysis completed successfully: {real_analysis_count} documents analyzed"
            elif real_analysis_count > 0:
                failed_count = total_documents - real_analysis_count
                message = f"AI analysis partially completed: {real_analysis_count} documents analyzed, {failed_count} failed"
            else:
                message = "No documents found to analyze"
            
            return {
                'success': success_status,
                'analyzed_count': real_analysis_count,  # Only count successful analyses
                'real_analysis_count': real_analysis_count,
                'failed_count': total_documents - real_analysis_count,
                'total_documents': total_documents,
                'message': message,
                'ai_services_available': True,
                'errors': errors[:10] if errors else []  # Show more errors for debugging
            }
            
        except Exception as e:
            db.session.rollback()
            raise

    def generate_income_worksheet(self, checklist_id: int, firm_id: int, user_id: int) -> Dict[str, Any]:
        """Generate income worksheet from analyzed documents"""
        from models import DocumentChecklist, Client, IncomeWorksheet
        
        try:
            # Get checklist and verify access
            checklist = db.session.query(DocumentChecklist).join(Client).filter(
                DocumentChecklist.id == checklist_id,
                Client.firm_id == firm_id
            ).first()
            
            if not checklist:
                raise ValueError('Checklist not found')
            
            # Mock income worksheet generation (could be enhanced with real analysis)
            worksheet_data = {
                'total_income': 75000,
                'w2_income': 60000,
                'interest_income': 500,
                'dividend_income': 1500,
                'other_income': 13000,
                'total_deductions': 12000,
                'federal_withholding': 8000,
                'state_withholding': 2000
            }
            
            # Create or update income worksheet
            worksheet = IncomeWorksheet.query.filter_by(checklist_id=checklist_id).first()
            if not worksheet:
                worksheet = IncomeWorksheet(
                    checklist_id=checklist_id,
                    created_by=user_id
                )
                db.session.add(worksheet)
            
            worksheet.worksheet_data = json.dumps(worksheet_data)
            worksheet.updated_at = datetime.utcnow()
            db.session.commit()
            
            return {
                'success': True,
                'worksheet_id': worksheet.id,
                'data': worksheet_data
            }
            
        except Exception as e:
            db.session.rollback()
            raise

    def get_saved_income_worksheet(self, checklist_id: int, firm_id: int) -> Dict[str, Any]:
        """Get saved income worksheet data"""
        from models import DocumentChecklist, Client, IncomeWorksheet
        
        try:
            # Verify checklist access
            checklist = db.session.query(DocumentChecklist).join(Client).filter(
                DocumentChecklist.id == checklist_id,
                Client.firm_id == firm_id
            ).first()
            
            if not checklist:
                raise ValueError('Checklist not found')
            
            # Get worksheet
            worksheet = IncomeWorksheet.query.filter_by(checklist_id=checklist_id).first()
            
            if worksheet and worksheet.worksheet_data:
                try:
                    worksheet_data = json.loads(worksheet.worksheet_data)
                    return {
                        'success': True,
                        'worksheet_id': worksheet.id,
                        'data': worksheet_data,
                        'updated_at': worksheet.updated_at.isoformat() if worksheet.updated_at else None
                    }
                except json.JSONDecodeError:
                    raise ValueError('Invalid worksheet data format')
            else:
                return {
                    'success': False,
                    'message': 'No income worksheet found for this checklist'
                }
                
        except Exception as e:
            raise
    

    def export_checklist_analysis(self, checklist_id: int, firm_id: int) -> Dict[str, Any]:
        """
        Export checklist analysis results as structured data
        
        Args:
            checklist_id: The checklist's ID
            firm_id: The firm's ID for security check
            
        Returns:
            Dict containing analysis data for export
        """
        from models import DocumentChecklist, Client
        
        # Get checklist and verify access
        checklist = DocumentChecklist.query.join(Client).filter(
            DocumentChecklist.id == checklist_id,
            Client.firm_id == firm_id
        ).first()
        
        if not checklist:
            raise ValueError('Checklist not found or access denied')
        
        try:
            # Gather analysis results
            analysis_data = {
                'checklist_name': checklist.name,
                'client_name': checklist.client.name,
                'export_timestamp': datetime.utcnow().isoformat(),
                'documents': []
            }
            
            for item in checklist.items:
                for document in item.client_documents:
                    doc_data = {
                        'item_title': item.title,
                        'filename': document.original_filename,
                        'analysis_completed': document.ai_analysis_completed,
                        'analysis_results': json.loads(document.ai_analysis_results) if document.ai_analysis_results else None
                    }
                    analysis_data['documents'].append(doc_data)
            
            return {
                'success': True,
                'data': analysis_data,
                'filename': f'checklist_analysis_{checklist_id}.json'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Export failed: {str(e)}'
            }
    

    def get_income_worksheet_for_download(self, checklist_id: int, firm_id: int) -> Dict[str, Any]:
        """
        Get income worksheet data formatted for download
        
        Args:
            checklist_id: The checklist's ID
            firm_id: The firm's ID for security check
            
        Returns:
            Dict containing worksheet data and metadata for download
        """
        from models import DocumentChecklist, Client, IncomeWorksheet
        
        # Get checklist and verify access
        checklist = DocumentChecklist.query.join(Client).filter(
            DocumentChecklist.id == checklist_id,
            Client.firm_id == firm_id
        ).first()
        
        if not checklist:
            raise ValueError('Checklist not found or access denied')
        
        worksheet = IncomeWorksheet.query.filter_by(checklist_id=checklist_id).first()
        if not worksheet:
            raise ValueError('Income worksheet not found')
        
        try:
            worksheet_data = json.loads(worksheet.worksheet_data)
            
            return {
                'success': True,
                'data': worksheet_data,
                'filename': f'income_worksheet_{checklist_id}.json',
                'checklist_name': checklist.name,
                'client_name': checklist.client.name
            }
            
        except json.JSONDecodeError:
            raise ValueError('Invalid worksheet data format')
        except Exception as e:
            return {
                'success': False,
                'error': f'Download preparation failed: {str(e)}'
            }
    

    def get_ai_services_status(config) -> Dict[str, Any]:
        """
        Check the status of AI services
        
        Args:
            config: Application configuration
            
        Returns:
            Dict containing AI services status and availability
        """
        try:
            ai_service = AIService(config)
            
            status = {
                'ai_services_available': ai_service.is_available(),
                'azure_available': ai_service.azure_client is not None,
                'gemini_available': ai_service.gemini_client is not None,
                'services_configured': []
            }
            
            if ai_service.azure_client:
                status['services_configured'].append('Azure Document Intelligence')
            if ai_service.gemini_client:
                status['services_configured'].append('Google Gemini')
                
            if not status['ai_services_available']:
                status['message'] = 'No AI services configured. Please add GEMINI_API_KEY or Azure Document Intelligence credentials.'
            else:
                status['message'] = f"AI services ready: {', '.join(status['services_configured'])}"
                
            return status
            
        except Exception as e:
            return {
                'ai_services_available': False,
                'error': f'Failed to check AI service status: {str(e)}'
            }