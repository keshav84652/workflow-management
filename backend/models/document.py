"""
Data Models for CPA Copilot
Defines all data structures used throughout the application.
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum
from pathlib import Path
from pydantic import BaseModel, Field, field_validator, ConfigDict
from decimal import Decimal


class ProcessingStatus(str, Enum):
    """Status of document processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    PARTIALLY_COMPLETED = "partially_completed"


class DocumentType(str, Enum):
    """Supported document types."""
    W2 = "W-2"
    FORM_1099 = "1099"
    FORM_1099_INT = "1099-INT"
    FORM_1099_DIV = "1099-DIV"
    FORM_1099_B = "1099-B"
    FORM_1099_MISC = "1099-MISC"
    FORM_1099_NEC = "1099-NEC"
    FORM_1098 = "1098"
    FORM_1098_T = "1098-T"
    SCHEDULE_K1 = "Schedule K-1"
    FORM_5498 = "5498"
    RECEIPT = "Receipt"
    INVOICE = "Invoice"
    STATEMENT = "Statement"
    OTHER = "Other"


class FileUpload(BaseModel):
    """Represents an uploaded file."""
    filename: str
    content_type: str
    size: int
    upload_timestamp: datetime = Field(default_factory=datetime.now)
    file_path: Optional[Path] = None
    
    @field_validator('content_type')
    @classmethod
    def validate_content_type(cls, v):
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/tiff']
        if v not in allowed_types:
            raise ValueError(f"Content type {v} not allowed")
        return v


class BookmarkStructure(BaseModel):
    """Hierarchical bookmark structure for workpaper organization."""
    level1: str = Field(..., description="Category (e.g., 'Income Documents')")
    level2: str = Field(..., description="File Type (e.g., 'W-2')")
    level3: str = Field(..., description="Specifics (e.g., 'W-2 - John Doe')")
    
    def to_path(self) -> str:
        """Convert to path string."""
        return f"{self.level1}/{self.level2}/{self.level3}"


class GeminiAnalysisResult(BaseModel):
    """Result from Gemini document analysis."""
    document_category: str
    document_analysis_summary: str
    extracted_key_info: Dict[str, Any]
    suggested_bookmark_structure: BookmarkStructure
    raw_response: Dict[str, Any] = Field(default_factory=dict)
    processing_time: Optional[float] = None
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class AzureExtractionResult(BaseModel):
    """Result from Azure Document Intelligence extraction."""
    doc_type: str
    confidence: Optional[float] = None
    fields: Dict[str, Any] = Field(default_factory=dict)
    page_numbers: List[int] = Field(default_factory=list)
    raw_response: Dict[str, Any] = Field(default_factory=dict)
    processing_time: Optional[float] = None
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ValidationError(BaseModel):
    """Represents a validation error."""
    field: str
    message: str
    severity: str = "error"  # error, warning, info
    code: Optional[str] = None


class ProcessedDocument(BaseModel):
    """Complete processed document with all analysis results."""
    file_upload: FileUpload
    azure_result: Optional[AzureExtractionResult] = None
    gemini_result: Optional[GeminiAnalysisResult] = None
    validation_errors: List[ValidationError] = Field(default_factory=list)
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    processing_start_time: Optional[datetime] = None
    processing_end_time: Optional[datetime] = None
    
    # Comparison results
    field_comparison: Optional[Dict[str, Any]] = None
    
    # Metadata
    document_id: str = Field(default_factory=lambda: str(datetime.now().timestamp()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def get_processing_duration(self) -> Optional[float]:
        """Get processing duration in seconds."""
        if self.processing_start_time and self.processing_end_time:
            return (self.processing_end_time - self.processing_start_time).total_seconds()
        return None
    
    def get_combined_fields(self) -> Dict[str, Any]:
        """Get combined fields from both Azure and Gemini."""
        combined = {}
        
        # Start with Azure fields
        if self.azure_result:
            combined.update(self.azure_result.fields)
        
        # Add/override with Gemini fields
        if self.gemini_result:
            combined.update(self.gemini_result.extracted_key_info)
        
        return combined
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class WorkpaperMetadata(BaseModel):
    """Metadata for generated workpaper."""
    title: str = "Tax Document Workpaper"
    tax_year: Optional[str] = None
    preparer_name: Optional[str] = None
    client_name: Optional[str] = None
    generation_date: datetime = Field(default_factory=datetime.now)
    total_documents: int = 0
    document_categories: Dict[str, int] = Field(default_factory=dict)
    
    # File information
    output_path: Optional[Path] = None
    file_size_bytes: Optional[int] = None
    page_count: Optional[int] = None


class ProcessingBatch(BaseModel):
    """Represents a batch of documents being processed."""
    batch_id: str = Field(default_factory=lambda: str(datetime.now().timestamp()))
    documents: List[ProcessedDocument] = Field(default_factory=list)
    status: ProcessingStatus = ProcessingStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    # Batch statistics
    total_documents: int = 0
    processed_documents: int = 0
    failed_documents: int = 0
    
    # Workpaper generation
    workpaper_metadata: Optional[WorkpaperMetadata] = None
    
    def update_statistics(self):
        """Update batch statistics based on document statuses."""
        self.total_documents = len(self.documents)
        self.processed_documents = sum(
            1 for doc in self.documents 
            if doc.processing_status == ProcessingStatus.COMPLETED
        )
        self.failed_documents = sum(
            1 for doc in self.documents 
            if doc.processing_status == ProcessingStatus.ERROR
        )
        
        # Update batch status
        if self.processed_documents == self.total_documents:
            self.status = ProcessingStatus.COMPLETED
        elif self.failed_documents == self.total_documents:
            self.status = ProcessingStatus.ERROR
        elif self.processed_documents > 0 or self.failed_documents > 0:
            self.status = ProcessingStatus.PARTIALLY_COMPLETED
        else:
            self.status = ProcessingStatus.PROCESSING


class ExportFormat(str, Enum):
    """Supported export formats."""
    JSON = "json"
    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"


class ExportRequest(BaseModel):
    """Request for data export."""
    format: ExportFormat
    include_raw_responses: bool = False
    include_validation_errors: bool = True
    include_gemini_analysis: bool = True
    include_azure_extraction: bool = True
    merge_fields: bool = True  # Merge Azure and Gemini fields
    
    # PII handling
    mask_pii: bool = True
    pii_fields_to_mask: List[str] = Field(
        default_factory=lambda: ["SSN", "TIN", "EIN", "AccountNumber"]
    )


# Type aliases for commonly used types
DocumentId = str
BatchId = str
FieldValue = Union[str, int, float, Decimal, bool, datetime, None]
FieldDict = Dict[str, FieldValue]
