"""
Azure Document Intelligence provider implementation.
"""

import os
import logging
import time
from typing import Dict, Any, Optional
from io import BytesIO

from .base_provider import AIProvider

# Azure imports - only if available
try:
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.core.exceptions import HttpResponseError
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False


class AzureProvider(AIProvider):
    """Azure Document Intelligence provider"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.client = None
        self.endpoint = None
        self.key = None
    
    def initialize(self) -> bool:
        """Initialize Azure Document Intelligence client"""
        if not AZURE_AVAILABLE:
            logging.warning("Azure Document Intelligence SDK not available")
            return False
        
        if not self.config:
            logging.warning("No configuration provided for Azure provider")
            return False
        
        # Extract configuration
        if hasattr(self.config, 'get'):
            self.endpoint = self.config.get('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT')
            self.key = self.config.get('AZURE_DOCUMENT_INTELLIGENCE_KEY')
        else:
            self.endpoint = getattr(self.config, 'AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT', None)
            self.key = getattr(self.config, 'AZURE_DOCUMENT_INTELLIGENCE_KEY', None)
        
        if not self.endpoint or not self.key:
            logging.warning("Azure endpoint or key not configured")
            return False
        
        try:
            self.client = DocumentIntelligenceClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.key)
            )
            self.is_initialized = True
            logging.info("Azure Document Intelligence initialized successfully")
            return True
        except Exception as e:
            logging.error(f"Failed to initialize Azure client: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if Azure provider is available"""
        return AZURE_AVAILABLE and self.is_initialized and self.client is not None
    
    def analyze_document(self, document_path: str) -> Dict[str, Any]:
        """
        Analyze document with Azure Document Intelligence
        
        Args:
            document_path: Path to the document file
            
        Returns:
            Standardized analysis results
            
        Raises:
            Exception: If analysis fails
        """
        if not self.is_available():
            raise Exception("Azure provider not available or not initialized")
        
        if not self.validate_document(document_path):
            raise Exception(f"Document validation failed: {document_path}")
        
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
                    logging.info(f"🔍 TRYING Azure model: {model_id}")
                    poller = self.client.begin_analyze_document(
                        model_id=model_id,
                        body=BytesIO(document_content)
                    )
                    result = poller.result()
                    successful_model = model_id
                    logging.info(f"✅ SUCCESS: Using Azure model {model_id}")
                    break
                except HttpResponseError as e:
                    last_error = e
                    if e.status_code == 400:
                        logging.warning(f"❌ Model {model_id} not suitable/available for this document, trying next...")
                        continue
                    else:
                        logging.error(f"❌ HTTP error with model {model_id}: {e}")
                        continue
                except Exception as e:
                    last_error = e
                    logging.error(f"❌ Error with model {model_id}: {e}")
                    continue
            
            if result is None:
                error_msg = f"All Azure models failed. Last error: {last_error}"
                logging.error(error_msg)
                raise Exception(error_msg)
            
            # Process results using exact working approach from be39018
            processing_time = time.time() - start_time
            
            # Convert to dictionary (from working version)
            result_dict = result.as_dict() if hasattr(result, 'as_dict') else self._serialize_azure_result(result)
            
            # Calculate response time
            response_time_ms = processing_time * 1000
            
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
            extracted_text = ""
            fields = {}
            
            if documents:
                doc = documents[0]
                extracted_text = doc.get('content', '')
                extracted_data['text_content'] = extracted_text
                
                # Extract fields as key-value pairs (as array) - working version
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
                                # Store in both formats for compatibility
                                fields[field_name] = {
                                    'value': value,
                                    'confidence': field_data.get('confidence', 0.8)
                                }
                                extracted_data['key_value_pairs'].append({
                                    'key': field_name,
                                    'value': str(value)
                                })
                                # Debug logging for field extraction
                                logging.debug(f"📋 Extracted field: {field_name} = {value}")
            
            # Extract tables from result (original approach)
            entities = []
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
            
            # Extract entities/key-value pairs from result level
            if hasattr(result, 'key_value_pairs') and result.key_value_pairs:
                for kv_pair in result.key_value_pairs:
                    if hasattr(kv_pair, 'key') and hasattr(kv_pair, 'value'):
                        entities.append({
                            'key': kv_pair.key.content if hasattr(kv_pair.key, 'content') else str(kv_pair.key),
                            'value': kv_pair.value.content if hasattr(kv_pair.value, 'content') else str(kv_pair.value),
                            'confidence': getattr(kv_pair, 'confidence', 0.8)
                        })
            
            # Calculate overall confidence
            confidence_scores = []
            if fields:
                confidence_scores.extend([field['confidence'] for field in fields.values() if 'confidence' in field])
            if entities:
                confidence_scores.extend([entity['confidence'] for entity in entities if 'confidence' in entity])
            
            overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.9
            
            logging.info(f"🎯 Azure analysis completed in {response_time_ms:.2f}ms using model: {successful_model}")
            logging.info(f"📊 Extracted {len(fields)} fields from Azure model {successful_model}")
            
            # Return in format that matches frontend expectations
            standardized_results = {
                'text': extracted_text,
                'fields': fields,  # For frontend compatibility
                'entities': entities,
                'confidence': overall_confidence,
                'document_type': self._detect_document_type(fields, entities),
                'extracted_data': extracted_data  # Keep original working format
            }
            
            return self._standardize_results(standardized_results)
            
        except Exception as e:
            error_info = self.format_error(e, f"Azure analysis of {document_path}")
            logging.error(f"Azure analysis failed: {error_info}")
            raise e
    
    def get_provider_name(self) -> str:
        """Get provider name"""
        return "Azure Document Intelligence"
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get Azure provider capabilities"""
        return {
            'provider': self.get_provider_name(),
            'supports_text_extraction': True,
            'supports_field_extraction': True,
            'supports_key_value_pairs': True,
            'supports_table_extraction': True,
            'supports_forms': True,
            'supported_models': [
                'prebuilt-read',
                'prebuilt-document', 
                'prebuilt-tax.us.1099',
                'prebuilt-tax.us.w2'
            ],
            'max_file_size_mb': 50,
            'supported_formats': self.get_supported_file_types()
        }
    
    def get_supported_file_types(self) -> list:
        """Get supported file types for Azure"""
        return ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp']
    
    def _serialize_azure_result(self, result) -> Dict[str, Any]:
        """Serialize Azure result to dictionary (from original working version)"""
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

    def _detect_document_type(self, fields: Dict, entities: list) -> str:
        """
        Detect document type based on extracted fields and entities
        
        Args:
            fields: Extracted fields
            entities: Extracted entities
            
        Returns:
            Document type string
        """
        # Check for tax forms
        tax_indicators = ['1099', 'w2', 'tax', 'irs', 'taxable', 'withholding']
        
        all_text = ' '.join([
            str(field.get('value', '')) for field in fields.values()
        ] + [
            f"{entity.get('key', '')} {entity.get('value', '')}" for entity in entities
        ]).lower()
        
        if any(indicator in all_text for indicator in tax_indicators):
            return 'tax_document'
        elif 'invoice' in all_text or 'bill' in all_text:
            return 'invoice'
        elif 'receipt' in all_text:
            return 'receipt'
        else:
            return 'general_document'