"""
Tax Document Workflow Tools
Tools for managing document upload and processing workflows through the AI assistant.
"""

import asyncio
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
import tempfile
import shutil

from .base_agent import BaseTool, ToolResult, ToolResultStatus, ToolSchema
from ..models.document import FileUpload, ProcessedDocument, ProcessingStatus
from ..services.document_processor import DocumentProcessor
from ..utils.config import settings


class DocumentUploadTool(BaseTool):
    """Tool for handling document uploads through the AI assistant"""
    
    def __init__(self, upload_callback=None):
        self.upload_callback = upload_callback
        self.processor = DocumentProcessor()
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Handle document upload workflow"""
        action = params.get("action", "status")
        
        if action == "status":
            return await self._get_upload_status()
        elif action == "clear":
            return await self._clear_uploads()
        elif action == "list":
            return await self._list_uploaded_files()
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                data=None,
                error=f"Unknown upload action: {action}"
            )
    
    async def _get_upload_status(self) -> ToolResult:
        """Get current upload status"""
        # This would be called by the UI when user wants to upload files
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            data={
                "message": "Ready to receive document uploads",
                "supported_formats": ["PDF", "JPG", "JPEG", "PNG", "TIFF"],
                "max_file_size": f"{settings.max_file_size / (1024*1024):.0f}MB",
                "upload_location": str(settings.upload_folder)
            },
            metadata={"action": "upload_ready"}
        )
    
    async def _clear_uploads(self) -> ToolResult:
        """Clear all uploaded files"""
        try:
            upload_folder = Path(settings.upload_folder)
            if upload_folder.exists():
                for file_path in upload_folder.glob("*"):
                    if file_path.is_file():
                        file_path.unlink()
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                data={
                    "message": "All uploaded files have been cleared",
                    "cleared_location": str(upload_folder)
                },
                metadata={"action": "files_cleared"}
            )
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                data=None,
                error=f"Error clearing uploads: {str(e)}"
            )
    
    async def _list_uploaded_files(self) -> ToolResult:
        """List currently uploaded files"""
        try:
            upload_folder = Path(settings.upload_folder)
            uploaded_files = []
            
            if upload_folder.exists():
                for file_path in upload_folder.glob("*"):
                    if file_path.is_file():
                        stat = file_path.stat()
                        uploaded_files.append({
                            "filename": file_path.name,
                            "size": stat.st_size,
                            "size_mb": round(stat.st_size / (1024*1024), 2),
                            "upload_time": stat.st_mtime
                        })
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                data={
                    "uploaded_files": uploaded_files,
                    "total_files": len(uploaded_files),
                    "total_size_mb": sum(f["size_mb"] for f in uploaded_files)
                }
            )
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                data=None,
                error=f"Error listing files: {str(e)}"
            )
    
    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="document_upload",
            description="Manage document uploads and file status",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["status", "clear", "list"],
                        "description": "Upload management action to perform"
                    }
                },
                "required": ["action"]
            },
            returns={
                "type": "object",
                "description": "Upload status and file information"
            }
        )


class DocumentProcessingTool(BaseTool):
    """Tool for managing document processing workflows through the AI assistant"""
    
    def __init__(self, processing_callback=None):
        self.processing_callback = processing_callback
        self.processor = DocumentProcessor()
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Handle document processing workflow"""
        action = params.get("action", "process")
        
        if action == "process":
            return await self._process_documents(params)
        elif action == "status":
            return await self._get_processing_status()
        elif action == "configure":
            return await self._configure_processing(params)
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                data=None,
                error=f"Unknown processing action: {action}"
            )
    
    async def _process_documents(self, params: Dict[str, Any]) -> ToolResult:
        """Process uploaded documents"""
        try:
            # Get processing configuration
            enable_azure = params.get("enable_azure", True)
            enable_gemini = params.get("enable_gemini", True)
            pii_mode = params.get("pii_mode", "mask")
            
            # Find uploaded files
            upload_folder = Path(settings.upload_folder)
            uploaded_files = []
            
            if not upload_folder.exists():
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    data=None,
                    error="No upload folder found. Please upload documents first."
                )
            
            # Convert uploaded files to FileUpload objects
            for file_path in upload_folder.glob("*"):
                if file_path.is_file() and file_path.suffix.lower() in ['.pdf', '.jpg', '.jpeg', '.png', '.tiff']:
                    # Determine content type
                    content_type = self._get_content_type(file_path.suffix.lower())
                    
                    file_upload = FileUpload(
                        filename=file_path.name,
                        content_type=content_type,
                        size=file_path.stat().st_size,
                        file_path=file_path
                    )
                    uploaded_files.append(file_upload)
            
            if not uploaded_files:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    data=None,
                    error="No valid documents found to process. Upload PDF, JPG, PNG, or TIFF files."
                )
            
            # Process documents
            batch = await self.processor.process_batch(
                uploaded_files,
                enable_gemini=enable_gemini,
                enable_azure=enable_azure,
                pii_mode=pii_mode
            )
            
            # Notify callback if provided (for UI updates)
            if self.processing_callback:
                await self.processing_callback(batch)
            
            # Prepare results
            successful = batch.processed_documents
            failed = batch.failed_documents
            total_time = sum(
                doc.get_processing_duration() or 0 
                for doc in batch.documents
            )
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                data={
                    "processing_complete": True,
                    "total_documents": len(uploaded_files),
                    "successful": successful,
                    "failed": failed,
                    "total_processing_time": round(total_time, 1),
                    "average_time_per_doc": round(total_time / len(uploaded_files), 1) if uploaded_files else 0,
                    "batch_id": batch.batch_id,
                    "configuration": {
                        "azure_enabled": enable_azure,
                        "gemini_enabled": enable_gemini,
                        "pii_mode": pii_mode
                    }
                },
                metadata={"action": "processing_complete", "batch": batch}
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                data=None,
                error=f"Error processing documents: {str(e)}"
            )
    
    async def _get_processing_status(self) -> ToolResult:
        """Get current processing status"""
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            data={
                "ready_to_process": True,
                "available_options": {
                    "azure_intelligence": "Extract structured data using Azure's prebuilt tax models",
                    "gemini_analysis": "Analyze documents with Gemini for categorization and insights",
                    "pii_modes": ["ignore", "mask", "remove"]
                },
                "default_configuration": {
                    "enable_azure": True,
                    "enable_gemini": True,
                    "pii_mode": "mask"
                }
            }
        )
    
    async def _configure_processing(self, params: Dict[str, Any]) -> ToolResult:
        """Configure processing options"""
        config = {
            "enable_azure": params.get("enable_azure", True),
            "enable_gemini": params.get("enable_gemini", True),
            "pii_mode": params.get("pii_mode", "mask")
        }
        
        # Validate PII mode
        if config["pii_mode"] not in ["ignore", "mask", "remove"]:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                data=None,
                error="Invalid PII mode. Must be 'ignore', 'mask', or 'remove'"
            )
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            data={
                "configuration_updated": True,
                "current_config": config,
                "message": f"Processing configured with Azure: {'enabled' if config['enable_azure'] else 'disabled'}, "
                          f"Gemini: {'enabled' if config['enable_gemini'] else 'disabled'}, "
                          f"PII handling: {config['pii_mode']}"
            }
        )
    
    def _get_content_type(self, extension: str) -> str:
        """Get MIME type from file extension"""
        mime_types = {
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
        }
        return mime_types.get(extension.lower(), 'application/pdf')
    
    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="document_processing",
            description="Process uploaded documents with AI analysis",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["process", "status", "configure"],
                        "description": "Processing action to perform"
                    },
                    "enable_azure": {
                        "type": "boolean",
                        "description": "Enable Azure Document Intelligence"
                    },
                    "enable_gemini": {
                        "type": "boolean", 
                        "description": "Enable Gemini AI analysis"
                    },
                    "pii_mode": {
                        "type": "string",
                        "enum": ["ignore", "mask", "remove"],
                        "description": "PII handling mode"
                    }
                },
                "required": ["action"]
            },
            returns={
                "type": "object",
                "description": "Processing results and status"
            }
        )


class WorkpaperGenerationTool(BaseTool):
    """Tool for generating workpapers through the AI assistant"""
    
    def __init__(self, workpaper_callback=None):
        self.workpaper_callback = workpaper_callback
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Generate workpaper from processed documents"""
        try:
            from ..services.workpaper_generator import WorkpaperGenerator
            
            # Get batch information (this would come from session state)
            # For now, we'll need to get it from the callback or session
            if not self.workpaper_callback:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    data=None,
                    error="Workpaper generation requires a processing batch. Process documents first."
                )
            
            # Get parameters
            title = params.get("title", "Tax Document Workpaper")
            client_name = params.get("client_name")
            tax_year = params.get("tax_year", "2024")
            preparer_name = params.get("preparer_name")
            
            # This would need to be integrated with session state
            # For now, return a placeholder response
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                data={
                    "workpaper_configured": True,
                    "title": title,
                    "client_name": client_name,
                    "tax_year": tax_year,
                    "preparer_name": preparer_name,
                    "message": "Workpaper configuration set. Use the Generate Workpaper tab to create the PDF."
                },
                metadata={"action": "workpaper_configured"}
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                data=None,
                error=f"Error configuring workpaper: {str(e)}"
            )
    
    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="workpaper_generation",
            description="Generate consolidated PDF workpapers",
            parameters={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Workpaper title"
                    },
                    "client_name": {
                        "type": "string",
                        "description": "Client name"
                    },
                    "tax_year": {
                        "type": "string",
                        "description": "Tax year"
                    },
                    "preparer_name": {
                        "type": "string",
                        "description": "Preparer name"
                    }
                },
                "required": []
            },
            returns={
                "type": "object",
                "description": "Workpaper generation status"
            }
        )
