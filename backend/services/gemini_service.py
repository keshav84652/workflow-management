"""
Gemini AI Service for Document Understanding
Handles document analysis, categorization, and structured output generation using Google's Gemini AI.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import base64
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
import io
import time

from google import genai
from google.genai import types
from PIL import Image
import PyPDF2
from pdf2image import convert_from_bytes
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.config import settings
from ..models.document import GeminiAnalysisResult, BookmarkStructure
from ..utils.debug_logger import log_api_call

# Set up logging
logger = logging.getLogger(__name__)


class GeminiDocumentService:
    """Service for document understanding using Google's Gemini AI."""
    
    def __init__(self):
        """Initialize Gemini client and model."""
        # Initialize the client with API key
        self.client = genai.Client(api_key=settings.gemini_api_key)
        
        # Model configuration
        self.model_name = settings.gemini_model
        
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        # Define simplified structured output schema to avoid truncation
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
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def analyze_document(
        self,
        document_content: bytes,
        document_name: str,
        content_type: str = "application/pdf",
        custom_prompt: str = None
    ) -> GeminiAnalysisResult:
        """
        Analyze a document using Gemini for understanding and structured output.
        
        Args:
            document_content: Binary content of the document
            document_name: Name of the document file
            content_type: MIME type of the document
            
        Returns:
            GeminiAnalysisResult with structured analysis
        """
        start_time = time.time()
        request_data = {
            "model": self.model_name,
            "document_name": document_name,
            "content_type": content_type,
            "content_size_bytes": len(document_content),
            "temperature": 0.1,
            "max_output_tokens": 4096
        }
        
        try:
            logger.info(f"Starting Gemini analysis for document: {document_name}")
            
            # Prepare the document for Gemini
            parts = []
            
            if content_type == "application/pdf":
                # Convert PDF to images for Gemini
                images = self._pdf_to_images(document_content)
                for img in images:
                    # Convert PIL image to bytes
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format='PNG')
                    img_byte_arr = img_byte_arr.getvalue()
                    parts.append(types.Part.from_bytes(
                        data=img_byte_arr,
                        mime_type="image/png"
                    ))
            else:
                # Handle image formats directly
                parts.append(types.Part.from_bytes(
                    data=document_content,
                    mime_type=content_type
                ))
            
            # Add the prompt (custom or default)
            if custom_prompt:
                parts.append(custom_prompt)
            else:
                prompt = self._create_analysis_prompt(document_name)
                parts.append(prompt)
            
            # Generate content with structured output - simplified for stability
            if custom_prompt:
                # For custom prompts, don't enforce JSON schema
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=parts,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        top_p=0.95,
                        top_k=32,
                        max_output_tokens=4096
                    )
                )
            else:
                # For default analysis, use structured JSON output
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=parts,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        top_p=0.95,
                        top_k=32,
                        max_output_tokens=4096,  # Reduced to ensure complete response
                        response_mime_type="application/json",
                        response_schema=self.output_schema
                    )
                )
            
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            
            # Parse the response with enhanced error handling
            if not response.text:
                raise ValueError("Empty response from Gemini API")
            
            # Handle custom prompt responses (non-JSON)
            if custom_prompt:
                # For custom prompts, return raw response in a simple structure
                from ..models.document import BookmarkStructure
                
                analysis_result = GeminiAnalysisResult(
                    document_category="Custom Analysis",
                    document_analysis_summary="Custom prompt analysis completed",
                    extracted_key_info={},
                    suggested_bookmark_structure=BookmarkStructure(
                        level1="Custom Analysis",
                        level2="CSV Output", 
                        level3=f"Custom - {document_name}"
                    ),
                    raw_response={"csv_output": response.text, "type": "custom_prompt"}
                )
                
                logger.info(f"Custom prompt analysis completed for document: {document_name}")
                return analysis_result
            
            try:
                # Log the response for debugging (first 500 chars)
                logger.debug(f"Gemini response preview: {response.text[:500]}...")
                result = json.loads(response.text)
                
                # Log successful API call
                log_api_call(
                    service="gemini",
                    endpoint=f"generate_content/{self.model_name}",
                    method="POST",
                    request_data=request_data,
                    response_data={
                        "response_length": len(response.text),
                        "document_category": result.get("document_category", "Unknown"),
                        "bookmark_structure": result.get("suggested_bookmark_structure", {}),
                        "extracted_fields_count": len(result.get("extracted_key_info", {}))
                    },
                    response_time_ms=response_time_ms,
                    status="success"
                )
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {str(e)}")
                logger.error(f"Response text: {response.text}")
                
                # Try to clean and fix common JSON issues
                cleaned_text = self._clean_json_response(response.text)
                try:
                    result = json.loads(cleaned_text)
                    logger.info("Successfully parsed cleaned JSON response")
                    
                    # Log partially successful API call
                    log_api_call(
                        service="gemini",
                        endpoint=f"generate_content/{self.model_name}",
                        method="POST",
                        request_data=request_data,
                        response_data={
                            "response_length": len(response.text),
                            "json_parse_status": "cleaned_and_parsed",
                            "document_category": result.get("document_category", "Unknown")
                        },
                        response_time_ms=response_time_ms,
                        status="success"
                    )
                    
                except json.JSONDecodeError as e2:
                    logger.error(f"Failed to parse cleaned JSON: {str(e2)}")
                    # Fallback to minimal result
                    result = self._create_fallback_result(response.text, document_name)
                    logger.warning("Using fallback result structure")
                    
                    # Log failed parsing but with fallback
                    log_api_call(
                        service="gemini",
                        endpoint=f"generate_content/{self.model_name}",
                        method="POST",
                        request_data=request_data,
                        response_data={
                            "response_length": len(response.text),
                            "json_parse_status": "failed_using_fallback"
                        },
                        response_time_ms=response_time_ms,
                        status="partial",
                        error=f"JSON parsing failed: {str(e2)}"
                    )
            
            # Create GeminiAnalysisResult with comprehensive flattened extraction
            analysis_result = GeminiAnalysisResult(
                document_category=result.get("document_category", "Unknown"),
                document_analysis_summary=result.get("document_analysis_summary", ""),
                extracted_key_info=self._flatten_comprehensive_data(result),
                suggested_bookmark_structure=BookmarkStructure(
                    level1=result["suggested_bookmark_structure"]["level1"],
                    level2=result["suggested_bookmark_structure"]["level2"],
                    level3=result["suggested_bookmark_structure"]["level3"]
                ),
                raw_response=result
            )
            
            logger.info(f"Gemini analysis completed for: {document_name}")
            return analysis_result
            
        except Exception as e:
            # Calculate response time even on error
            response_time_ms = (time.time() - start_time) * 1000
            
            # Log failed API call
            log_api_call(
                service="gemini",
                endpoint=f"generate_content/{self.model_name}",
                method="POST",
                request_data=request_data,
                response_data={},
                response_time_ms=response_time_ms,
                status="error",
                error=str(e)
            )
            
            logger.error(f"Error in Gemini analysis: {str(e)}")
            raise
    
    async def analyze_documents_batch(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[GeminiAnalysisResult]:
        """
        Analyze multiple documents in batch.
        
        Args:
            documents: List of document dictionaries with 'content', 'name', and 'content_type'
            
        Returns:
            List of GeminiAnalysisResult objects
        """
        loop = asyncio.get_event_loop()
        
        # Create tasks for each document
        tasks = []
        for doc in documents:
            task = loop.run_in_executor(
                self.executor,
                self.analyze_document,
                doc['content'],
                doc['name'],
                doc.get('content_type', 'application/pdf')
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error processing document {i}: {str(result)}")
                # Create error result
                error_result = GeminiAnalysisResult(
                    document_category="Error",
                    document_analysis_summary=f"Error analyzing document: {str(result)}",
                    extracted_key_info={"error": str(result)},
                    suggested_bookmark_structure=BookmarkStructure(
                        level1="Error Documents",
                        level2="Processing Error",
                        level3=f"Error - {documents[i]['name']}"
                    ),
                    raw_response={"error": str(result)}
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)
        
        return processed_results
    
    def compare_with_azure_results(
        self,
        gemini_result: GeminiAnalysisResult,
        azure_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare Gemini extraction with Azure results to identify discrepancies.
        
        Args:
            gemini_result: Gemini analysis result
            azure_result: Azure Document Intelligence result
            
        Returns:
            Dictionary containing comparison results
        """
        comparison = {
            "matching_fields": {},
            "discrepancies": {},
            "gemini_only_fields": {},
            "azure_only_fields": {}
        }
        
        # Extract Azure fields (simplified for comparison)
        azure_fields = self._extract_azure_fields(azure_result)
        gemini_fields = gemini_result.extracted_key_info
        
        # Find matching and discrepant fields
        for field, value in gemini_fields.items():
            if field in azure_fields:
                if str(value).lower() == str(azure_fields[field]).lower():
                    comparison["matching_fields"][field] = value
                else:
                    comparison["discrepancies"][field] = {
                        "gemini": value,
                        "azure": azure_fields[field]
                    }
            else:
                comparison["gemini_only_fields"][field] = value
        
        # Find Azure-only fields
        for field, value in azure_fields.items():
            if field not in gemini_fields:
                comparison["azure_only_fields"][field] = value
        
        return comparison
    
    def _flatten_comprehensive_data(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return the extracted key info directly since schema is now flat.
        
        Args:
            result: The complete Gemini response with flat structure
            
        Returns:
            Flattened dictionary with all extracted information
        """
        # With the simplified schema, extracted_key_info is already flat
        return result.get("extracted_key_info", {})
    
    def _create_analysis_prompt(self, document_name: str) -> str:
        """Create a concise analysis prompt for Gemini."""
        return f"""Analyze this tax document '{document_name}' and extract key information.

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
    
    def _clean_json_response(self, response_text: str) -> str:
        """
        Clean JSON response text to fix common parsing issues.
        
        Args:
            response_text: Raw response text from Gemini
            
        Returns:
            Cleaned JSON string
        """
        import re
        
        # Remove any leading/trailing whitespace
        cleaned = response_text.strip()
        
        # Fix common issues
        # 1. Remove any markdown code block markers
        cleaned = re.sub(r'^```json\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)
        
        # 2. Fix unescaped quotes in strings (basic fix)
        # This is tricky, so we'll be conservative
        
        # 3. Remove any null bytes
        cleaned = cleaned.replace('\x00', '')
        
        # 4. Fix potential trailing commas (basic fix)
        cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
        
        return cleaned
    
    def _create_fallback_result(self, response_text: str, document_name: str) -> Dict[str, Any]:
        """
        Create a fallback result when JSON parsing fails.
        
        Args:
            response_text: The raw response text
            document_name: Name of the document being processed
            
        Returns:
            Minimal valid result structure
        """
        return {
            "document_category": "Unknown",
            "document_analysis_summary": f"Document analysis completed with parsing issues. Raw response available in logs.",
            "extracted_key_info": {
                "form_type": "Unknown",
                "tax_year": "Unknown",
                "payer_name": "Unknown",
                "recipient_name": "Unknown",
                "parsing_error": "JSON parsing failed - raw response preserved"
            },
            "detailed_amounts": [],
            "tax_withholdings": [],
            "state_tax_info": [],
            "significant_amounts": [],
            "additional_fields": {
                "parsing_error": "JSON parsing failed",
                "raw_response_length": len(response_text)
            },
            "suggested_bookmark_structure": {
                "level1": "Other Tax Documents",
                "level2": "Processing Error",
                "level3": f"Error - {document_name}"
            }
        }
    
    def _pdf_to_images(self, pdf_content: bytes) -> List[Image.Image]:
        """Convert PDF bytes to list of PIL images."""
        try:
            images = convert_from_bytes(pdf_content, dpi=200, fmt='PNG')
            return images
        except Exception as e:
            logger.error(f"Error converting PDF to images: {str(e)}")
            # Fallback: try to extract text at least
            raise
    
    def _extract_azure_fields(self, azure_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract simplified fields from Azure results for comparison."""
        fields = {}
        
        # Find documents in Azure result
        documents = azure_result.get('documents', [])
        if not documents:
            analyze_result = azure_result.get('analyzeResult', {})
            documents = analyze_result.get('documents', [])
        
        for doc in documents:
            if not isinstance(doc, dict):
                continue
                
            doc_fields = doc.get('fields', {})
            for field_name, field_data in doc_fields.items():
                if isinstance(field_data, dict):
                    # Extract the value
                    value = None
                    if 'valueString' in field_data:
                        value = field_data['valueString']
                    elif 'valueNumber' in field_data:
                        value = field_data['valueNumber']
                    elif 'valueDate' in field_data:
                        value = field_data['valueDate']
                    elif 'content' in field_data:
                        value = field_data['content']
                    
                    if value is not None:
                        fields[field_name] = value
        
        return fields
    
    def generate_category_insights(
        self,
        documents: List[GeminiAnalysisResult]
    ) -> Dict[str, Any]:
        """
        Generate insights across multiple documents by category.
        
        Args:
            documents: List of analyzed documents
            
        Returns:
            Dictionary containing category-wise insights
        """
        insights = {
            "total_documents": len(documents),
            "categories": {},
            "document_types": {},
            "summary": ""
        }
        
        # Group by category
        for doc in documents:
            category = doc.suggested_bookmark_structure.level1
            doc_type = doc.suggested_bookmark_structure.level2
            
            # Category count
            if category not in insights["categories"]:
                insights["categories"][category] = {
                    "count": 0,
                    "document_types": []
                }
            insights["categories"][category]["count"] += 1
            
            if doc_type not in insights["categories"][category]["document_types"]:
                insights["categories"][category]["document_types"].append(doc_type)
            
            # Document type count
            if doc_type not in insights["document_types"]:
                insights["document_types"][doc_type] = 0
            insights["document_types"][doc_type] += 1
        
        # Generate summary
        insights["summary"] = f"Processed {len(documents)} tax documents across {len(insights['categories'])} categories. "
        insights["summary"] += f"Most common document types: {', '.join(list(insights['document_types'].keys())[:3])}"
        
        return insights
