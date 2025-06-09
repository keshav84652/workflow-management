"""
Document Processor Service
Main orchestrator for document processing, combining Azure and Gemini services.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import asyncio
from datetime import datetime
import json
import copy
import re

from ..services.azure_service import AzureDocumentService
from ..services.gemini_service import GeminiDocumentService
from ..services.document_visualizer import DocumentVisualizer
from ..models.document import (
    ProcessedDocument, FileUpload, ProcessingStatus,
    AzureExtractionResult, GeminiAnalysisResult,
    ValidationError, ProcessingBatch
)
from ..utils.config import settings

# Set up logging
logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Main document processing orchestrator."""
    
    def __init__(self):
        """Initialize services and processors."""
        self.azure_service = AzureDocumentService()
        self.gemini_service = GeminiDocumentService()
        self.visualizer = DocumentVisualizer()
        
        # PII patterns for basic handling
        self.pii_patterns = {
            'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b'),
            'ein': re.compile(r'\b\d{2}-\d{7}\b'),
            'phone': re.compile(r'\b\+?1?\s*\(?[2-9][0-8][0-9]\)?[-.\s]*[2-9][0-9]{2}[-.\s]*[0-9]{4}\b')
        }
        
    async def process_document(
        self,
        file_upload: FileUpload,
        enable_gemini: bool = True,
        enable_azure: bool = True,
        pii_mode: str = "mask"
    ) -> ProcessedDocument:
        """
        Process a single document through Azure and/or Gemini.
        
        Args:
            file_upload: The uploaded file information
            enable_gemini: Whether to use Gemini analysis
            enable_azure: Whether to use Azure extraction
            pii_mode: PII handling mode
            
        Returns:
            ProcessedDocument with all results
        """
        # Create processed document
        processed_doc = ProcessedDocument(
            file_upload=file_upload,
            processing_status=ProcessingStatus.PROCESSING,
            processing_start_time=datetime.now()
        )
        
        try:
            # Read file content
            if not file_upload.file_path or not Path(file_upload.file_path).exists():
                raise FileNotFoundError(f"File not found: {file_upload.file_path}")
                
            with open(file_upload.file_path, 'rb') as f:
                content = f.read()
            
            # Process with Azure
            if enable_azure:
                try:
                    logger.info(f"Processing with Azure: {file_upload.filename}")
                    azure_result = await self._process_with_azure(
                        content, file_upload.content_type
                    )
                    processed_doc.azure_result = azure_result
                except Exception as e:
                    logger.error(f"Azure processing error: {str(e)}")
                    processed_doc.validation_errors.append(
                        ValidationError(
                            field="azure_processing",
                            message=str(e),
                            severity="error"
                        )
                    )
            
            # Process with Gemini
            if enable_gemini:
                try:
                    logger.info(f"Processing with Gemini: {file_upload.filename}")
                    gemini_result = await self._process_with_gemini(
                        content, file_upload.filename, file_upload.content_type
                    )
                    processed_doc.gemini_result = gemini_result
                except Exception as e:
                    logger.error(f"Gemini processing error: {str(e)}")
                    processed_doc.validation_errors.append(
                        ValidationError(
                            field="gemini_processing",
                            message=str(e),
                            severity="error"
                        )
                    )
            
            # Compare results if both are available
            if processed_doc.azure_result and processed_doc.gemini_result:
                processed_doc.field_comparison = self.gemini_service.compare_with_azure_results(
                    processed_doc.gemini_result,
                    processed_doc.azure_result.raw_response
                )
            
            # Apply PII handling if Azure results exist
            if processed_doc.azure_result:
                processed_doc.azure_result.fields = self._apply_pii_handling(
                    processed_doc.azure_result.fields,
                    processed_doc.azure_result.doc_type,
                    pii_mode
                )
            
            # Validate extracted data
            validation_errors = self._validate_document(processed_doc)
            processed_doc.validation_errors.extend(validation_errors)
            
            # Set final status
            if processed_doc.azure_result or processed_doc.gemini_result:
                processed_doc.processing_status = ProcessingStatus.COMPLETED
            else:
                processed_doc.processing_status = ProcessingStatus.ERROR
                
        except Exception as e:
            logger.error(f"Document processing error: {str(e)}")
            processed_doc.processing_status = ProcessingStatus.ERROR
            processed_doc.validation_errors.append(
                ValidationError(
                    field="general_processing",
                    message=str(e),
                    severity="error"
                )
            )
        finally:
            processed_doc.processing_end_time = datetime.now()
            
        return processed_doc
    
    async def process_batch(
        self,
        file_uploads: List[FileUpload],
        enable_gemini: bool = True,
        enable_azure: bool = True,
        pii_mode: str = "mask"
    ) -> ProcessingBatch:
        """
        Process multiple documents in batch.
        
        Args:
            file_uploads: List of uploaded files
            enable_gemini: Whether to use Gemini analysis
            enable_azure: Whether to use Azure extraction
            pii_mode: PII handling mode
            
        Returns:
            ProcessingBatch with all results
        """
        batch = ProcessingBatch(
            total_documents=len(file_uploads),
            status=ProcessingStatus.PROCESSING
        )
        
        # Process documents concurrently
        tasks = []
        for file_upload in file_uploads:
            task = self.process_document(
                file_upload, enable_gemini, enable_azure, pii_mode
            )
            tasks.append(task)
        
        # Wait for all documents to process
        processed_docs = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Add to batch and handle exceptions
        for i, result in enumerate(processed_docs):
            if isinstance(result, Exception):
                # Create error document
                error_doc = ProcessedDocument(
                    file_upload=file_uploads[i],
                    processing_status=ProcessingStatus.ERROR,
                    validation_errors=[
                        ValidationError(
                            field="batch_processing",
                            message=str(result),
                            severity="error"
                        )
                    ]
                )
                batch.documents.append(error_doc)
            else:
                batch.documents.append(result)
        
        # Update batch statistics
        batch.update_statistics()
        batch.completed_at = datetime.now()
        
        return batch
    
    async def _process_with_azure(
        self,
        content: bytes,
        content_type: str
    ) -> AzureExtractionResult:
        """Process document with Azure Document Intelligence."""
        start_time = datetime.now()
        
        # Call Azure service
        loop = asyncio.get_event_loop()
        azure_response = await loop.run_in_executor(
            None,
            self.azure_service.analyze_document,
            content,
            "prebuilt-tax.us",
            content_type
        )
        
        # Extract fields directly from Azure response (flat structure only)
        fields = {}
        doc_type = "unknown"
        confidence = None
        page_numbers = []
        
        if "documents" in azure_response and azure_response["documents"]:
            first_doc = azure_response["documents"][0]
            doc_type = first_doc.get("docType", "unknown")
            confidence = first_doc.get("confidence", None)
            
            # Extract fields directly with flattening
            if "fields" in first_doc:
                fields = self._extract_flat_fields(first_doc["fields"])
            
            # Extract page numbers
            if "pages" in azure_response:
                page_numbers = [page.get("pageNumber", 1) for page in azure_response["pages"]]
        
        result = AzureExtractionResult(
            doc_type=doc_type,
            confidence=confidence,
            fields=fields,
            page_numbers=page_numbers,
            raw_response=azure_response,
            processing_time=(datetime.now() - start_time).total_seconds()
        )
        
        return result
    
    async def _process_with_gemini(
        self,
        content: bytes,
        filename: str,
        content_type: str
    ) -> GeminiAnalysisResult:
        """Process document with Gemini AI."""
        start_time = datetime.now()
        
        # Call Gemini service
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.gemini_service.analyze_document,
            content,
            filename,
            content_type
        )
        
        result.processing_time = (datetime.now() - start_time).total_seconds()
        return result
    
    def _apply_pii_handling(
        self,
        fields: Dict[str, Any],
        doc_type: str,
        pii_mode: str
    ) -> Dict[str, Any]:
        """Apply basic PII handling to extracted fields."""
        if pii_mode == "ignore":
            return fields
        
        processed_fields = {}
        for field_name, field_value in fields.items():
            if isinstance(field_value, str):
                # Check if field contains PII
                if self._is_pii_field(field_name, field_value):
                    if pii_mode == "mask":
                        processed_fields[field_name] = self._mask_pii_value(field_value)
                    elif pii_mode == "remove":
                        continue  # Skip this field
                    else:
                        processed_fields[field_name] = field_value
                else:
                    processed_fields[field_name] = field_value
            else:
                processed_fields[field_name] = field_value
        
        return processed_fields
    
    def _validate_document(self, document: ProcessedDocument) -> List[ValidationError]:
        """Validate extracted document data."""
        errors = []
        
        # Check for required fields based on document type
        if document.azure_result:
            doc_type = document.azure_result.doc_type
            fields = document.azure_result.fields
            
            # Basic validation for W-2
            if "w2" in doc_type.lower():
                required_fields = ["Employee_Name", "Employer_Name", "WagesTipsAndOtherCompensation"]
                for field in required_fields:
                    if field not in fields or not fields[field]:
                        errors.append(
                            ValidationError(
                                field=field,
                                message=f"Required field '{field}' is missing or empty",
                                severity="warning"
                            )
                        )
            
            # Basic validation for 1099
            elif "1099" in doc_type.lower():
                required_fields = ["Payer_Name", "Recipient_Name"]
                for field in required_fields:
                    if field not in fields or not fields[field]:
                        errors.append(
                            ValidationError(
                                field=field,
                                message=f"Required field '{field}' is missing or empty",
                                severity="warning"
                            )
                        )
        
        # Check for Gemini categorization
        if document.gemini_result:
            if document.gemini_result.document_category == "Unknown":
                errors.append(
                    ValidationError(
                        field="document_category",
                        message="Document category could not be determined",
                        severity="warning"
                    )
                )
        
        return errors
    
    def get_document_summary(self, document: ProcessedDocument) -> Dict[str, Any]:
        """Get a summary of the processed document."""
        summary = {
            "filename": document.file_upload.filename,
            "status": document.processing_status.value,
            "processing_time": document.get_processing_duration(),
            "document_type": None,
            "confidence": None,
            "category": None,
            "key_fields": {},
            "validation_issues": len(document.validation_errors)
        }
        
        # Add Azure information
        if document.azure_result:
            summary["document_type"] = document.azure_result.doc_type
            summary["confidence"] = document.azure_result.confidence
            
            # Add key fields (limit to important ones)
            key_field_names = [
                "TaxYear", "Employee_Name", "Employer_Name", "Payer_Name",
                "Recipient_Name", "TotalAmount", "WagesTipsAndOtherCompensation"
            ]
            for field in key_field_names:
                if field in document.azure_result.fields:
                    summary["key_fields"][field] = document.azure_result.fields[field]
        
        # Add Gemini information
        if document.gemini_result:
            summary["category"] = document.gemini_result.document_category
            summary["analysis_summary"] = document.gemini_result.document_analysis_summary
            summary["bookmark_path"] = document.gemini_result.suggested_bookmark_structure.to_path()
        
        return summary
    
    def _extract_flat_fields(self, fields_dict: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Extract and flatten fields from Azure response."""
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
    
    def _extract_array_values(self, array_data: List[Dict[str, Any]]) -> List[Any]:
        """Extract values from array field."""
        values = []
        for item in array_data:
            if isinstance(item, dict):
                if 'type' in item and item['type'] == 'object' and 'valueObject' in item:
                    # Flatten object in array
                    flat_obj = self._extract_flat_fields(item['valueObject'])
                    values.append(flat_obj)
                else:
                    # Extract scalar value from array item
                    value = self._extract_scalar_value(item)
                    if value is not None:
                        values.append(value)
            else:
                values.append(item)
        return values
    
    def _flatten_address(self, address_data: Dict[str, Any], prefix: str) -> Dict[str, Any]:
        """Flatten address object."""
        address_fields = {}
        address_mapping = {
            'houseNumber': 'house_number',
            'poBox': 'po_box',
            'road': 'road',
            'city': 'city',
            'state': 'state',
            'postalCode': 'postal_code',
            'countryRegion': 'country_region',
            'streetAddress': 'street_address',
            'unit': 'unit'
        }
        
        for azure_key, normalized_key in address_mapping.items():
            if azure_key in address_data:
                address_fields[f"{prefix}_{normalized_key}"] = address_data[azure_key]
        
        return address_fields
    
    def _is_pii_field(self, field_name: str, field_value: str) -> bool:
        """Check if field contains PII based on name and value patterns."""
        # Check field name patterns
        pii_field_patterns = [
            r'(?i)\b(?:ssn|tin|ein)\b',
            r'(?i)\b(?:social|security|tax(?:payer)?|employer)[\s_]*(?:number|id)\b',
            r'(?i)\b(?:phone|telephone|mobile|cell)[\s_]*(?:number)?\b',
            r'(?i)\b(?:account|routing)[\s_]*number\b'
        ]
        
        for pattern in pii_field_patterns:
            if re.search(pattern, field_name):
                return True
        
        # Check value patterns
        for pattern_name, pattern in self.pii_patterns.items():
            if pattern.search(field_value):
                return True
        
        return False
    
    def _mask_pii_value(self, value: str) -> str:
        """Mask PII in field value."""
        # Mask SSN/TIN patterns
        for pattern_name, pattern in self.pii_patterns.items():
            if pattern.search(value):
                if pattern_name == 'ssn':
                    # Keep last 4 digits for SSN
                    if '-' in value and len(value) == 11:  # XXX-XX-XXXX
                        return f"XXX-XX-{value[-4:]}"
                    elif len(value) == 9:  # XXXXXXXXX
                        return f"XXXXX{value[-4:]}"
                elif pattern_name == 'ein':
                    # Keep last 4 digits for EIN
                    if '-' in value and len(value) == 10:  # XX-XXXXXXX
                        return f"XX-XXX{value[-4:]}"
                elif pattern_name == 'phone':
                    # Mask phone numbers
                    return "XXX-XXX-XXXX"
        
        # Default masking
        return "****"
    
    def clean_azure_response(
        self,
        azure_response: Dict[str, Any],
        remove_page_details: bool = True,
        remove_confidence: bool = False,
        remove_spans: bool = True
    ) -> Dict[str, Any]:
        """
        Clean Azure response by removing verbose fields.
        Returns flat structure only.
        """
        cleaned = copy.deepcopy(azure_response)
        
        # Remove root-level verbose details
        if remove_page_details:
            cleaned.pop("pages", None)
            cleaned.pop("words", None)
            cleaned.pop("lines", None)
            cleaned.pop("paragraphs", None)
        
        # Remove styles and other metadata
        cleaned.pop("styles", None)
        cleaned.pop("barcodes", None)
        cleaned.pop("formulas", None)
        
        # Clean documents
        if "documents" in cleaned:
            for doc in cleaned["documents"]:
                if isinstance(doc, dict):
                    # Remove verbose fields from document
                    if remove_spans:
                        doc.pop("spans", None)
                    if remove_confidence:
                        doc.pop("confidence", None)
                    
                    # Clean fields recursively
                    if "fields" in doc:
                        doc["fields"] = self._clean_fields_recursive(
                            doc["fields"], remove_confidence, remove_spans
                        )
        
        return cleaned
    
    def _clean_fields_recursive(
        self,
        fields: Dict[str, Any],
        remove_confidence: bool,
        remove_spans: bool
    ) -> Dict[str, Any]:
        """Recursively clean fields, removing verbose metadata."""
        cleaned_fields = {}
        
        for field_name, field_data in fields.items():
            if isinstance(field_data, dict):
                cleaned_field = {}
                
                # Keep essential fields
                for key in ['type', 'content', 'valueString', 'valueNumber', 
                           'valueDate', 'valueTime', 'valueBoolean', 'valueObject', 
                           'valueArray', 'valueAddress']:
                    if key in field_data:
                        if key == 'valueObject' and isinstance(field_data[key], dict):
                            cleaned_field[key] = self._clean_fields_recursive(
                                field_data[key], remove_confidence, remove_spans
                            )
                        elif key == 'valueArray' and isinstance(field_data[key], list):
                            cleaned_array = []
                            for item in field_data[key]:
                                if isinstance(item, dict):
                                    cleaned_item = self._clean_fields_recursive(
                                        {k: v for k, v in item.items() if k != field_name},
                                        remove_confidence, remove_spans
                                    )
                                    cleaned_array.append(cleaned_item)
                                else:
                                    cleaned_array.append(item)
                            cleaned_field[key] = cleaned_array
                        else:
                            cleaned_field[key] = field_data[key]
                
                # Conditionally keep confidence
                if not remove_confidence and 'confidence' in field_data:
                    cleaned_field['confidence'] = field_data['confidence']
                
                cleaned_fields[field_name] = cleaned_field
            else:
                cleaned_fields[field_name] = field_data
        
        return cleaned_fields
    
    def create_flat_export(
        self,
        documents: List[ProcessedDocument],
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Create a flat export structure (no hierarchical data).
        """
        export_data = {
            "export_date": datetime.now().isoformat(),
            "document_count": len(documents),
            "documents": []
        }
        
        for doc in documents:
            doc_data = {}
            
            # Add metadata if requested
            if include_metadata:
                doc_data.update({
                    "filename": doc.file_upload.filename,
                    "processing_status": doc.processing_status.value,
                    "processing_time": doc.get_processing_duration(),
                    "document_id": doc.document_id,
                    "created_at": doc.created_at.isoformat()
                })
            
            # Add Azure fields (flat only)
            if doc.azure_result:
                doc_data.update({
                    "doc_type": doc.azure_result.doc_type,
                    "confidence": doc.azure_result.confidence,
                    "page_numbers": doc.azure_result.page_numbers
                })
                # Add all extracted fields directly (they're already flat)
                doc_data.update(doc.azure_result.fields)
            
            # Add Gemini analysis (flat structure)
            if doc.gemini_result:
                doc_data.update({
                    "gemini_category": doc.gemini_result.document_category,
                    "gemini_summary": doc.gemini_result.document_analysis_summary,
                    "bookmark_level1": doc.gemini_result.suggested_bookmark_structure.level1,
                    "bookmark_level2": doc.gemini_result.suggested_bookmark_structure.level2,
                    "bookmark_level3": doc.gemini_result.suggested_bookmark_structure.level3
                })
                # Add Gemini extracted info (flat)
                for key, value in doc.gemini_result.extracted_key_info.items():
                    doc_data[f"gemini_{key}"] = value
            
            # Add validation errors count
            doc_data["validation_errors_count"] = len(doc.validation_errors)
            
            export_data["documents"].append(doc_data)
        
        return export_data
    
    def create_document_visualization(self, processed_document: ProcessedDocument, 
                                    output_path: Optional[str] = None,
                                    visualization_type: str = 'box') -> Optional[str]:
        """
        Create a visualization of extracted fields on the document image.
        
        Args:
            processed_document: The processed document with Azure results
            output_path: Optional path to save the visualization
            visualization_type: Type of visualization ('box', 'tick', or 'both')
            
        Returns:
            Path to the saved visualization image, or None if failed
        """
        if not processed_document.azure_result:
            logger.error("No Azure result available for visualization")
            return None
            
        if not processed_document.file_upload.file_path:
            logger.error("No file path available for visualization")
            return None
            
        # Configure visualizer
        config = {
            'visualization_type': visualization_type,
            'show_label': True,
            'show_tick_with_box': visualization_type == 'both'
        }
        
        # Update visualizer config
        self.visualizer.config.update(config)
        
        # Create visualization
        return self.visualizer.create_visualization_from_processed_document(
            str(processed_document.file_upload.file_path),
            processed_document,
            output_path
        )
    
    def create_batch_visualizations(self, processed_documents: List[ProcessedDocument],
                                  visualization_type: str = 'box') -> Dict[str, Optional[str]]:
        """
        Create visualizations for a batch of processed documents.
        
        Args:
            processed_documents: List of processed documents
            visualization_type: Type of visualization ('box', 'tick', or 'both')
            
        Returns:
            Dictionary mapping document filenames to visualization paths
        """
        visualizations = {}
        
        for doc in processed_documents:
            if doc.azure_result and doc.file_upload.file_path:
                viz_path = self.create_document_visualization(
                    doc, 
                    visualization_type=visualization_type
                )
                visualizations[doc.file_upload.filename] = viz_path
            else:
                visualizations[doc.file_upload.filename] = None
                
        return visualizations
