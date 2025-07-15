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
        logging.info(f"Azure provider config type: {type(self.config)}")
        logging.info(f"Azure provider config has get: {hasattr(self.config, 'get') if self.config else False}")
        
        if hasattr(self.config, 'get'):
            self.endpoint = self.config.get('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT')
            self.key = self.config.get('AZURE_DOCUMENT_INTELLIGENCE_KEY')
            logging.info(f"Azure config via .get(): endpoint={bool(self.endpoint)}, key={bool(self.key)}")
        else:
            self.endpoint = getattr(self.config, 'AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT', None)
            self.key = getattr(self.config, 'AZURE_DOCUMENT_INTELLIGENCE_KEY', None)
            logging.info(f"Azure config via getattr(): endpoint={bool(self.endpoint)}, key={bool(self.key)}")
        
        if not self.endpoint or not self.key:
            logging.warning("Azure endpoint or key not configured")
            return False
        
        try:
            # Use latest API version that supports prebuilt-tax.us.1099 model
            self.client = DocumentIntelligenceClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.key),
                api_version="2024-11-30"  # Required for 1099 model support
            )
            self.is_initialized = True
            logging.info("Azure Document Intelligence initialized successfully with API version 2024-11-30")
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
                
                # Extract fields using flat extraction (like cpa_copilot)
                if 'fields' in doc:
                    # Use flat field extraction
                    flat_fields = self._extract_flat_fields(doc['fields'])
                    fields.update(flat_fields)
                    
                    # Also populate key_value_pairs for frontend compatibility
                    for field_name, value in flat_fields.items():
                        extracted_data['key_value_pairs'].append({
                            'key': field_name,
                            'value': str(value)
                        })
                        logging.debug(f"📋 Extracted flat field: {field_name} = {value}")
            
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
        
        try:
            # Safely build all_text with proper string conversion
            field_texts = []
            for field in fields.values():
                if isinstance(field, dict):
                    value = field.get('value', '')
                    field_texts.append(str(value) if value is not None else '')
                else:
                    field_texts.append(str(field) if field is not None else '')
            
            entity_texts = []
            for entity in entities:
                if isinstance(entity, dict):
                    key = entity.get('key', '')
                    value = entity.get('value', '')
                    entity_texts.append(f"{str(key) if key is not None else ''} {str(value) if value is not None else ''}")
                else:
                    entity_texts.append(str(entity) if entity is not None else '')
            
            all_text = ' '.join(field_texts + entity_texts).lower()
        except Exception as e:
            logging.warning(f"Error building text for document type detection: {e}")
            all_text = ''
        
        if all_text and any(indicator in all_text for indicator in tax_indicators):
            return 'tax_document'
        elif 'invoice' in all_text or 'bill' in all_text:
            return 'invoice'
        elif 'receipt' in all_text:
            return 'receipt'
        else:
            return 'general_document'
    
    def _extract_flat_fields(self, fields_dict: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Extract and flatten fields from Azure response (from cpa_copilot)."""
        flat_fields = {}
        
        for field_name, field_data in fields_dict.items():
            current_key = f"{prefix}_{field_name}" if prefix else field_name
            
            if isinstance(field_data, dict):
                # Handle different Azure field types
                if 'type' in field_data:
                    field_type = field_data.get('type')
                    
                    if field_type == 'object' and 'valueObject' in field_data:
                        # Recursively flatten nested objects
                        nested_fields = self._extract_flat_fields(field_data['valueObject'], current_key)
                        flat_fields.update(nested_fields)
                    elif field_type == 'array' and 'valueArray' in field_data:
                        # Handle arrays
                        flat_fields[current_key] = self._extract_array_values(field_data['valueArray'])
                    elif field_type == 'address' and 'valueAddress' in field_data:
                        # Flatten address fields
                        address_fields = self._flatten_address(field_data['valueAddress'], current_key)
                        flat_fields.update(address_fields)
                    else:
                        # Extract scalar values
                        value = self._extract_scalar_value(field_data)
                        if value is not None:
                            flat_fields[current_key] = value
                else:
                    # Simple dictionary without type information
                    flat_fields[current_key] = field_data
            else:
                flat_fields[current_key] = field_data
        
        return flat_fields
    
    def _extract_scalar_value(self, field_data: Dict[str, Any]) -> Any:
        """Extract scalar value from Azure field data."""
        # Try different value types in order of preference
        for value_key in ['valueString', 'valueNumber', 'valueDate', 'valueTime', 'valueBoolean', 'content']:
            if value_key in field_data:
                return field_data[value_key]
        return None
    
    def _extract_array_values(self, array_data: list) -> list:
        """Extract values from array field."""
        values = []
        for item in array_data:
            if isinstance(item, dict):
                if 'type' in item and item['type'] == 'object' and 'valueObject' in item:
                    # Flatten object in array
                    flat_obj = self._extract_flat_fields(item['valueObject'])
                    values.append(flat_obj)
                else:
                    # Try to extract scalar value
                    scalar = self._extract_scalar_value(item)
                    if scalar is not None:
                        values.append(scalar)
            else:
                values.append(item)
        return values
    
    def _flatten_address(self, address_data: Dict[str, Any], prefix: str) -> Dict[str, Any]:
        """Flatten address fields."""
        address_fields = {}
        address_components = ['houseNumber', 'road', 'city', 'state', 'postalCode', 'countryRegion']
        
        for component in address_components:
            if component in address_data:
                key = f"{prefix}_{component}"
                address_fields[key] = address_data[component]
        
        return address_fields