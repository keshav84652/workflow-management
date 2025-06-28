"""
Google Gemini provider implementation.
"""

import os
import logging
import time
import base64
from typing import Dict, Any, Optional

from .base_provider import AIProvider

# Gemini imports - only if available
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except (ImportError, Exception) as e:
    GEMINI_AVAILABLE = False


class GeminiProvider(AIProvider):
    """Google Gemini provider"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.client = None
        self.api_key = None
    
    def initialize(self) -> bool:
        """Initialize Gemini client"""
        if not GEMINI_AVAILABLE:
            logging.warning("Google Gemini SDK not available")
            return False
        
        if not self.config:
            logging.warning("No configuration provided for Gemini provider")
            return False
        
        # Extract API key
        if hasattr(self.config, 'get'):
            self.api_key = self.config.get('GEMINI_API_KEY')
        else:
            self.api_key = getattr(self.config, 'GEMINI_API_KEY', None)
        
        if not self.api_key:
            logging.warning("Gemini API key not configured")
            return False
        
        try:
            self.client = genai.Client(api_key=self.api_key)
            self.is_initialized = True
            logging.info("Google Gemini initialized successfully")
            return True
        except Exception as e:
            logging.error(f"Failed to initialize Gemini client: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if Gemini provider is available"""
        return GEMINI_AVAILABLE and self.is_initialized and self.client is not None
    
    def analyze_document(self, document_path: str) -> Dict[str, Any]:
        """
        Analyze document with Google Gemini
        
        Args:
            document_path: Path to the document file
            
        Returns:
            Standardized analysis results
            
        Raises:
            Exception: If analysis fails
        """
        if not self.is_available():
            raise Exception("Gemini provider not available or not initialized")
        
        if not self.validate_document(document_path):
            raise Exception(f"Document validation failed: {document_path}")
        
        start_time = time.time()
        
        try:
            logging.info(f"Starting Gemini document analysis for: {document_path}")
            
            # Read and encode the document
            with open(document_path, 'rb') as f:
                document_content = f.read()
            
            # Determine MIME type
            mime_type = self._get_mime_type(document_path)
            
            # Create the prompt for document analysis
            analysis_prompt = self._create_analysis_prompt()
            
            # Prepare the content for Gemini
            content_parts = [
                types.Part(text=analysis_prompt),
                types.Part(
                    inline_data=types.Blob(
                        data=document_content,
                        mime_type=mime_type
                    )
                )
            ]
            
            # Generate content using Gemini
            response = self.client.models.generate_content(
                model='gemini-1.5-flash',
                contents=types.GenerateContentRequest(
                    contents=[types.Content(parts=content_parts)]
                )
            )
            
            processing_time = time.time() - start_time
            
            # Parse the response
            if response.candidates and len(response.candidates) > 0:
                result_text = response.candidates[0].content.parts[0].text
                parsed_results = self._parse_gemini_response(result_text)
            else:
                raise Exception("No candidates returned from Gemini")
            
            # Calculate confidence based on response quality
            confidence = self._calculate_confidence(parsed_results, result_text)
            
            raw_results = {
                'text': parsed_results.get('extracted_text', ''),
                'fields': parsed_results.get('fields', {}),
                'entities': parsed_results.get('entities', []),
                'confidence': confidence,
                'document_type': parsed_results.get('document_type', 'unknown'),
                'processing_time': processing_time,
                'metadata': {
                    'gemini_model': 'gemini-1.5-flash',
                    'raw_response': result_text[:500] + '...' if len(result_text) > 500 else result_text,
                    'response_length': len(result_text)
                }
            }
            
            return self._standardize_results(raw_results)
            
        except Exception as e:
            error_info = self.format_error(e, f"Gemini analysis of {document_path}")
            logging.error(f"Gemini analysis failed: {error_info}")
            raise e
    
    def get_provider_name(self) -> str:
        """Get provider name"""
        return "Google Gemini"
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get Gemini provider capabilities"""
        return {
            'provider': self.get_provider_name(),
            'supports_text_extraction': True,
            'supports_field_extraction': True,
            'supports_key_value_pairs': True,
            'supports_document_understanding': True,
            'supports_multimodal': True,
            'supported_models': ['gemini-1.5-flash', 'gemini-1.5-pro'],
            'max_file_size_mb': 20,
            'supported_formats': self.get_supported_file_types()
        }
    
    def get_supported_file_types(self) -> list:
        """Get supported file types for Gemini"""
        return ['.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp']
    
    def _get_mime_type(self, document_path: str) -> str:
        """
        Get MIME type for the document
        
        Args:
            document_path: Path to the document
            
        Returns:
            MIME type string
        """
        extension = os.path.splitext(document_path)[1].lower()
        mime_types = {
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        return mime_types.get(extension, 'application/octet-stream')
    
    def _create_analysis_prompt(self) -> str:
        """
        Create comprehensive analysis prompt for Gemini
        
        Returns:
            Prompt string
        """
        return """Please analyze this document thoroughly and provide the following information in a structured format:

1. DOCUMENT TYPE: Identify what type of document this is (tax form, invoice, receipt, contract, etc.)

2. EXTRACTED TEXT: Provide all readable text from the document

3. KEY FIELDS: Extract key fields and their values in JSON format, such as:
   - Names, addresses, phone numbers
   - Dates (due dates, creation dates, etc.)
   - Monetary amounts
   - ID numbers, account numbers
   - Any form-specific fields

4. KEY-VALUE PAIRS: Identify important label-value relationships

5. ENTITIES: Extract named entities like:
   - Person names
   - Organizations
   - Locations
   - Dates
   - Financial amounts

Please format your response as follows:
DOCUMENT_TYPE: [type]
EXTRACTED_TEXT: [full text]
FIELDS: {JSON object with key-value pairs}
ENTITIES: [list of entities with types]
CONFIDENCE: [your confidence level 0-1]

Be thorough and accurate in your extraction."""
    
    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Gemini's response into structured data
        
        Args:
            response_text: Raw response from Gemini
            
        Returns:
            Parsed results dictionary
        """
        import json
        import re
        
        results = {
            'document_type': 'unknown',
            'extracted_text': '',
            'fields': {},
            'entities': []
        }
        
        try:
            # Extract document type
            doc_type_match = re.search(r'DOCUMENT_TYPE:\s*(.+)', response_text, re.IGNORECASE)
            if doc_type_match:
                results['document_type'] = doc_type_match.group(1).strip()
            
            # Extract full text
            text_match = re.search(r'EXTRACTED_TEXT:\s*(.+?)(?=FIELDS:|ENTITIES:|$)', response_text, re.IGNORECASE | re.DOTALL)
            if text_match:
                results['extracted_text'] = text_match.group(1).strip()
            
            # Extract fields (JSON format)
            fields_match = re.search(r'FIELDS:\s*({.+?})', response_text, re.IGNORECASE | re.DOTALL)
            if fields_match:
                try:
                    fields_json = fields_match.group(1)
                    results['fields'] = json.loads(fields_json)
                except json.JSONDecodeError:
                    # If JSON parsing fails, try to extract key-value pairs manually
                    results['fields'] = self._extract_fields_manually(fields_match.group(1))
            
            # Extract entities
            entities_match = re.search(r'ENTITIES:\s*(.+?)(?=CONFIDENCE:|$)', response_text, re.IGNORECASE | re.DOTALL)
            if entities_match:
                entities_text = entities_match.group(1).strip()
                results['entities'] = self._parse_entities(entities_text)
            
        except Exception as e:
            logging.warning(f"Failed to parse Gemini response structure: {e}")
            # Fallback: use the entire response as extracted text
            results['extracted_text'] = response_text
        
        return results
    
    def _extract_fields_manually(self, fields_text: str) -> Dict[str, Any]:
        """
        Manually extract fields if JSON parsing fails
        
        Args:
            fields_text: Raw fields text
            
        Returns:
            Fields dictionary
        """
        fields = {}
        
        # Look for key: value patterns
        patterns = [
            r'"([^"]+)":\s*"([^"]*)"',  # "key": "value"
            r'(\w+):\s*([^\n,}]+)',     # key: value
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, fields_text)
            for key, value in matches:
                fields[key.strip()] = value.strip()
        
        return fields
    
    def _parse_entities(self, entities_text: str) -> list:
        """
        Parse entities from text
        
        Args:
            entities_text: Raw entities text
            
        Returns:
            List of entity dictionaries
        """
        entities = []
        
        # Simple parsing - look for patterns like "Name: John Doe (PERSON)"
        lines = entities_text.split('\n')
        for line in lines:
            line = line.strip()
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    entity_type = parts[0].strip()
                    entity_value = parts[1].strip()
                    
                    # Remove parenthetical type info if present
                    entity_value = re.sub(r'\s*\([^)]+\)$', '', entity_value)
                    
                    if entity_value:
                        entities.append({
                            'type': entity_type,
                            'value': entity_value,
                            'confidence': 0.8
                        })
        
        return entities
    
    def _calculate_confidence(self, parsed_results: Dict, raw_response: str) -> float:
        """
        Calculate confidence based on response quality
        
        Args:
            parsed_results: Parsed results
            raw_response: Raw response text
            
        Returns:
            Confidence score (0-1)
        """
        confidence = 0.5  # Base confidence
        
        # Increase confidence based on extracted content
        if parsed_results.get('extracted_text'):
            confidence += 0.2
        
        if parsed_results.get('fields'):
            confidence += 0.1 * min(len(parsed_results['fields']), 3)
        
        if parsed_results.get('entities'):
            confidence += 0.05 * min(len(parsed_results['entities']), 4)
        
        if parsed_results.get('document_type') != 'unknown':
            confidence += 0.1
        
        # Check for confidence indicators in the response
        if 'CONFIDENCE:' in raw_response.upper():
            conf_match = re.search(r'CONFIDENCE:\s*([\d.]+)', raw_response, re.IGNORECASE)
            if conf_match:
                try:
                    gemini_confidence = float(conf_match.group(1))
                    confidence = (confidence + gemini_confidence) / 2
                except ValueError:
                    pass
        
        return min(1.0, confidence)