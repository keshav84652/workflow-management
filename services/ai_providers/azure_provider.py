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
            
            # Try different models in order of preference
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
                    poller = self.client.begin_analyze_document(
                        model_id=model_id,
                        body=BytesIO(document_content)
                    )
                    result = poller.result()
                    successful_model = model_id
                    break
                except HttpResponseError as e:
                    last_error = e
                    if e.status_code == 400:
                        logging.info(f"Model {model_id} not suitable for this document, trying next...")
                        continue
                    else:
                        logging.error(f"HTTP error with model {model_id}: {e}")
                        continue
                except Exception as e:
                    last_error = e
                    logging.error(f"Error with model {model_id}: {e}")
                    continue
            
            if result is None:
                error_msg = f"All Azure models failed. Last error: {last_error}"
                logging.error(error_msg)
                raise Exception(error_msg)
            
            # Process results
            processing_time = time.time() - start_time
            
            # Extract text content
            extracted_text = ""
            if hasattr(result, 'content'):
                extracted_text = result.content
            
            # Extract fields
            fields = {}
            if hasattr(result, 'documents') and result.documents:
                doc = result.documents[0]
                if hasattr(doc, 'fields') and doc.fields:
                    for field_name, field_value in doc.fields.items():
                        if hasattr(field_value, 'value'):
                            fields[field_name] = {
                                'value': field_value.value,
                                'confidence': getattr(field_value, 'confidence', 0.8)
                            }
            
            # Extract entities/key-value pairs
            entities = []
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
            
            overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.8
            
            raw_results = {
                'text': extracted_text,
                'fields': fields,
                'entities': entities,
                'confidence': overall_confidence,
                'model_used': successful_model,
                'document_type': self._detect_document_type(fields, entities),
                'processing_time': processing_time,
                'metadata': {
                    'azure_model': successful_model,
                    'pages_analyzed': len(result.pages) if hasattr(result, 'pages') and result.pages else 1,
                    'api_version': getattr(result, 'api_version', 'unknown')
                }
            }
            
            return self._standardize_results(raw_results)
            
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