"""
Google Gemini provider implementation.
"""

import os
import logging
import time
import base64
import re
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
            
            # Prepare the content for Gemini (using working API from original code)
            parts = []
            
            if mime_type.startswith('image/') or mime_type == 'application/pdf':
                # Handle image/PDF formats - send actual binary data (from working version)
                parts.append(types.Part.from_bytes(
                    data=document_content,
                    mime_type=mime_type
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
            response = self.client.models.generate_content(
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
            
            # Return working format - standardize through base class  
            raw_results = {
                'service': 'gemini',
                'analysis_text': analysis_text,
                'document_type': self._extract_document_type(analysis_text),
                'confidence': 0.85,  # Use 'confidence' for base class compatibility
                'summary': clean_summary,
                'key_findings': key_findings,  # Added for frontend dropdown display
                'response_time_ms': response_time_ms
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
            'supported_models': ['gemini-1.5-flash'],
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
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        return cleaned_text
    
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