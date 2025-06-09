"""
Azure Document Intelligence Service
Handles all interactions with Azure Form Recognizer for tax document processing.
"""

import logging
from typing import Dict, Any, List, Optional, BinaryIO
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import time
from io import BytesIO
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.config import settings
from ..models.document import ProcessingStatus, DocumentType
from ..utils.debug_logger import log_api_call

# Set up logging
logger = logging.getLogger(__name__)


class AzureDocumentService:
    """Service for interacting with Azure Document Intelligence API."""
    
    def __init__(self):
        """Initialize Azure Document Intelligence client."""
        self.client = DocumentIntelligenceClient(
            endpoint=settings.azure_endpoint,
            credential=AzureKeyCredential(settings.azure_key)
        )
        self.executor = ThreadPoolExecutor(max_workers=5)
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def analyze_document(
        self,
        document_content: bytes,
        model_id: str = "prebuilt-tax.us",
        content_type: str = "application/pdf"
    ) -> Dict[str, Any]:
        """
        Analyze a single document using Azure Document Intelligence.
        
        Args:
            document_content: Binary content of the document
            model_id: The model to use for analysis
            content_type: MIME type of the document
            
        Returns:
            Dictionary containing the analysis results
        """
        start_time = time.time()
        request_data = {
            "model_id": model_id,
            "content_type": content_type,
            "content_size_bytes": len(document_content)
        }
        
        try:
            logger.info(f"Starting document analysis with model: {model_id}")
            
            # Start the analysis - use body parameter with BytesIO for stable SDK
            poller = self.client.begin_analyze_document(
                model_id=model_id,
                body=BytesIO(document_content)
            )
            
            # Wait for completion
            result = poller.result()
            
            # Convert to dictionary
            result_dict = result.as_dict() if hasattr(result, 'as_dict') else self._serialize_result(result)
            
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            
            # Log API call for debugging
            log_api_call(
                service="azure",
                endpoint=f"analyze_document/{model_id}",
                method="POST",
                request_data=request_data,
                response_data={
                    "documents_found": len(result_dict.get('documents', [])),
                    "model_id": result_dict.get('model_id'),
                    "api_version": result_dict.get('api_version'),
                    "content_length": len(result_dict.get('content', ''))
                },
                response_time_ms=response_time_ms,
                status="success"
            )
            
            logger.info(f"Document analysis completed. Found {len(result_dict.get('documents', []))} documents")
            return result_dict
            
        except Exception as e:
            # Calculate response time even on error
            response_time_ms = (time.time() - start_time) * 1000
            
            # Log failed API call
            log_api_call(
                service="azure",
                endpoint=f"analyze_document/{model_id}",
                method="POST",
                request_data=request_data,
                response_data={},
                response_time_ms=response_time_ms,
                status="error",
                error=str(e)
            )
            
            logger.error(f"Error analyzing document: {str(e)}")
            raise
    
    def analyze_document_from_file(
        self,
        file_path: str,
        model_id: str = "prebuilt-tax.us"
    ) -> Dict[str, Any]:
        """
        Analyze a document from a file path.
        
        Args:
            file_path: Path to the document file
            model_id: The model to use for analysis
            
        Returns:
            Dictionary containing the analysis results
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Determine content type
            content_type = self._get_content_type(path.suffix.lower())
            
            # Read file content
            with open(file_path, 'rb') as f:
                content = f.read()
            
            return self.analyze_document(content, model_id, content_type)
            
        except Exception as e:
            logger.error(f"Error analyzing document from file: {str(e)}")
            raise
    
    async def analyze_documents_batch(
        self,
        documents: List[Dict[str, Any]],
        model_id: str = "prebuilt-tax.us"
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple documents in batch.
        
        Args:
            documents: List of document dictionaries with 'content' and 'content_type'
            model_id: The model to use for analysis
            
        Returns:
            List of analysis results
        """
        loop = asyncio.get_event_loop()
        
        # Create tasks for each document
        tasks = []
        for doc in documents:
            task = loop.run_in_executor(
                self.executor,
                self.analyze_document,
                doc['content'],
                model_id,
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
                processed_results.append({
                    'error': str(result),
                    'document_index': i
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_supported_models(self) -> List[str]:
        """
        Get list of supported tax document models.
        
        Returns:
            List of model IDs
        """
        return [
            "prebuilt-tax.us",
            "prebuilt-tax.us.w2",
            "prebuilt-tax.us.1098",
            "prebuilt-tax.us.1098E",
            "prebuilt-tax.us.1098T",
            "prebuilt-tax.us.1099",
            "prebuilt-tax.us.1099A",
            "prebuilt-tax.us.1099B",
            "prebuilt-tax.us.1099C",
            "prebuilt-tax.us.1099CAP",
            "prebuilt-tax.us.1099DIV",
            "prebuilt-tax.us.1099G",
            "prebuilt-tax.us.1099H",
            "prebuilt-tax.us.1099INT",
            "prebuilt-tax.us.1099K",
            "prebuilt-tax.us.1099LS",
            "prebuilt-tax.us.1099LTC",
            "prebuilt-tax.us.1099MISC",
            "prebuilt-tax.us.1099NEC",
            "prebuilt-tax.us.1099OID",
            "prebuilt-tax.us.1099PATR",
            "prebuilt-tax.us.1099Q",
            "prebuilt-tax.us.1099QA",
            "prebuilt-tax.us.1099R",
            "prebuilt-tax.us.1099S",
            "prebuilt-tax.us.1099SA",
            "prebuilt-tax.us.1099SB",
        ]
    
    def identify_document_type(self, api_result: Dict[str, Any]) -> Optional[str]:
        """
        Identify the document type from Azure API results.
        
        Args:
            api_result: The API analysis result
            
        Returns:
            Document type string or None
        """
        documents = api_result.get('documents', [])
        if documents and isinstance(documents[0], dict):
            return documents[0].get('docType')
        
        # Check in analyzeResult
        analyze_result = api_result.get('analyzeResult', {})
        docs = analyze_result.get('documents', [])
        if docs and isinstance(docs[0], dict):
            return docs[0].get('docType')
        
        return None
    
    def extract_confidence_scores(self, api_result: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract confidence scores for each field.
        
        Args:
            api_result: The API analysis result
            
        Returns:
            Dictionary mapping field names to confidence scores
        """
        confidence_scores = {}
        
        # Find documents
        documents = api_result.get('documents', [])
        if not documents:
            analyze_result = api_result.get('analyzeResult', {})
            documents = analyze_result.get('documents', [])
        
        for doc in documents:
            if not isinstance(doc, dict):
                continue
                
            fields = doc.get('fields', {})
            for field_name, field_data in fields.items():
                if isinstance(field_data, dict) and 'confidence' in field_data:
                    confidence_scores[field_name] = field_data['confidence']
        
        return confidence_scores
    
    def _get_content_type(self, extension: str) -> str:
        """Get MIME type from file extension."""
        mime_types = {
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
        }
        return mime_types.get(extension, 'application/pdf')
    
    def _serialize_result(self, result: Any) -> Dict[str, Any]:
        """
        Serialize Azure result object to dictionary.
        
        Args:
            result: Azure AnalyzeResult object
            
        Returns:
            Serialized dictionary
        """
        try:
            # Try to convert to JSON string first
            if hasattr(result, 'to_json'):
                return json.loads(result.to_json())
            
            # Manual serialization as fallback
            serialized = {
                'api_version': getattr(result, 'api_version', None),
                'model_id': getattr(result, 'model_id', None),
                'content': getattr(result, 'content', None),
                'documents': [],
                'pages': [],
            }
            
            # Serialize documents
            if hasattr(result, 'documents') and result.documents:
                for doc in result.documents:
                    doc_dict = {
                        'doc_type': getattr(doc, 'doc_type', None),
                        'confidence': getattr(doc, 'confidence', None),
                        'fields': {}
                    }
                    
                    # Serialize fields
                    if hasattr(doc, 'fields'):
                        for field_name, field_value in doc.fields.items():
                            doc_dict['fields'][field_name] = self._serialize_field(field_value)
                    
                    serialized['documents'].append(doc_dict)
            
            return serialized
            
        except Exception as e:
            logger.error(f"Error serializing result: {str(e)}")
            return {}
    
    def _serialize_field(self, field: Any) -> Dict[str, Any]:
        """Serialize a document field."""
        if not field:
            return {}
            
        return {
            'type': getattr(field, 'type', None),
            'value': getattr(field, 'value', None),
            'content': getattr(field, 'content', None),
            'confidence': getattr(field, 'confidence', None),
            'bounding_regions': getattr(field, 'bounding_regions', [])
        }
