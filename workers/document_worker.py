"""
Document Worker for CPA WorkflowPilot
Background tasks for document processing and file operations.
"""

import logging
import os
import shutil
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from celery_app import celery_app
from events.publisher import publish_event
from events.schemas import ErrorEvent

logger = logging.getLogger(__name__)


@celery_app.task(name='workers.document_worker.process_large_document')
def process_large_document(document_id: int, file_path: str, 
                          firm_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Process large document files (optimize, compress, etc.)
    
    Args:
        document_id: Database ID of the document
        file_path: Path to the document file
        firm_id: Firm ID for context
        
    Returns:
        dict: Processing results
    """
    try:
        logger.info(f"Processing large document {document_id}: {file_path}")
        
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")
        
        # Get original file info
        original_size = file_path_obj.stat().st_size
        file_extension = file_path_obj.suffix.lower()
        
        # Process based on file type
        processing_result = {}
        
        if file_extension in ['.pdf']:
            processing_result = _process_pdf_document(file_path_obj)
        elif file_extension in ['.jpg', '.jpeg', '.png', '.tiff']:
            processing_result = _process_image_document(file_path_obj)
        elif file_extension in ['.doc', '.docx']:
            processing_result = _process_word_document(file_path_obj)
        else:
            # Generic processing
            processing_result = _process_generic_document(file_path_obj)
        
        # Update database with processing results
        _update_document_processing_results(document_id, processing_result, original_size)
        
        logger.info(f"Completed processing for document {document_id}")
        
        return {
            'success': True,
            'document_id': document_id,
            'original_size_bytes': original_size,
            'processing_result': processing_result,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        
        # Publish error event
        error_event = ErrorEvent(
            error_type=type(e).__name__,
            error_message=str(e),
            context={
                'task_type': 'process_large_document',
                'document_id': document_id,
                'file_path': file_path
            },
            firm_id=firm_id
        )
        publish_event(error_event)
        
        return {
            'success': False,
            'document_id': document_id,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(name='workers.document_worker.cleanup_temp_files')
def cleanup_temp_files(max_age_hours: int = 24) -> Dict[str, Any]:
    """
    Clean up temporary files older than specified age
    
    Args:
        max_age_hours: Maximum age of files to keep (in hours)
        
    Returns:
        dict: Cleanup results
    """
    try:
        logger.info(f"Starting cleanup of temporary files older than {max_age_hours} hours")
        
        from datetime import timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        # Clean up temp directories
        temp_dirs = ['uploads/temp', 'instance/temp', 'temp']
        
        total_deleted = 0
        total_size_freed = 0
        
        for temp_dir in temp_dirs:
            temp_path = Path(temp_dir)
            if not temp_path.exists():
                continue
            
            for file_path in temp_path.rglob('*'):
                if file_path.is_file():
                    try:
                        # Check file age
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_mtime < cutoff_time:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            total_deleted += 1
                            total_size_freed += file_size
                            logger.debug(f"Deleted temp file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Could not delete temp file {file_path}: {e}")
        
        # Clean up empty directories
        for temp_dir in temp_dirs:
            temp_path = Path(temp_dir)
            if temp_path.exists():
                try:
                    for dir_path in temp_path.rglob(''):
                        if dir_path.is_dir() and not any(dir_path.iterdir()):
                            dir_path.rmdir()
                            logger.debug(f"Removed empty directory: {dir_path}")
                except Exception as e:
                    logger.warning(f"Error cleaning empty directories: {e}")
        
        logger.info(f"Cleanup completed: {total_deleted} files deleted, {total_size_freed} bytes freed")
        
        return {
            'success': True,
            'files_deleted': total_deleted,
            'bytes_freed': total_size_freed,
            'cutoff_time': cutoff_time.isoformat(),
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error during temp file cleanup: {e}")
        
        # Publish error event
        error_event = ErrorEvent(
            error_type=type(e).__name__,
            error_message=str(e),
            context={'task_type': 'cleanup_temp_files'}
        )
        publish_event(error_event)
        
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(name='workers.document_worker.generate_thumbnails')
def generate_thumbnails(document_id: int, file_path: str, 
                       firm_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Generate thumbnails for document files
    
    Args:
        document_id: Database ID of the document
        file_path: Path to the document file
        firm_id: Firm ID for context
        
    Returns:
        dict: Thumbnail generation results
    """
    try:
        logger.info(f"Generating thumbnails for document {document_id}: {file_path}")
        
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")
        
        file_extension = file_path_obj.suffix.lower()
        thumbnails_generated = []
        
        # Create thumbnails directory
        thumbnails_dir = Path('uploads/thumbnails')
        thumbnails_dir.mkdir(exist_ok=True)
        
        if file_extension in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
            # Generate image thumbnails
            thumbnail_path = _generate_image_thumbnail(file_path_obj, thumbnails_dir, document_id)
            if thumbnail_path:\n                thumbnails_generated.append(thumbnail_path)\n        \n        elif file_extension == '.pdf':\n            # Generate PDF thumbnails\n            thumbnail_paths = _generate_pdf_thumbnails(file_path_obj, thumbnails_dir, document_id)\n            thumbnails_generated.extend(thumbnail_paths)\n        \n        # Update database with thumbnail paths\n        _update_document_thumbnails(document_id, thumbnails_generated)\n        \n        logger.info(f\"Generated {len(thumbnails_generated)} thumbnails for document {document_id}\")\n        \n        return {\n            'success': True,\n            'document_id': document_id,\n            'thumbnails_count': len(thumbnails_generated),\n            'thumbnail_paths': thumbnails_generated,\n            'timestamp': datetime.utcnow().isoformat()\n        }\n        \n    except Exception as e:\n        logger.error(f\"Error generating thumbnails for document {document_id}: {e}\")\n        \n        # Publish error event\n        error_event = ErrorEvent(\n            error_type=type(e).__name__,\n            error_message=str(e),\n            context={\n                'task_type': 'generate_thumbnails',\n                'document_id': document_id,\n                'file_path': file_path\n            },\n            firm_id=firm_id\n        )\n        publish_event(error_event)\n        \n        return {\n            'success': False,\n            'document_id': document_id,\n            'error': str(e),\n            'timestamp': datetime.utcnow().isoformat()\n        }\n\n\ndef _process_pdf_document(file_path: Path) -> Dict[str, Any]:\n    \"\"\"Process PDF document\"\"\"\n    try:\n        # TODO: Implement PDF processing (optimize, compress, etc.)\n        # For now, just return basic info\n        file_size = file_path.stat().st_size\n        \n        return {\n            'type': 'pdf',\n            'processed': True,\n            'optimized': False,  # Would be True if we actually optimized\n            'final_size_bytes': file_size,\n            'compression_ratio': 1.0,  # No compression applied\n            'message': 'PDF processing placeholder'\n        }\n    except Exception as e:\n        return {\n            'type': 'pdf',\n            'processed': False,\n            'error': str(e)\n        }\n\n\ndef _process_image_document(file_path: Path) -> Dict[str, Any]:\n    \"\"\"Process image document\"\"\"\n    try:\n        # TODO: Implement image processing (optimize, resize, etc.)\n        file_size = file_path.stat().st_size\n        \n        return {\n            'type': 'image',\n            'processed': True,\n            'optimized': False,\n            'final_size_bytes': file_size,\n            'compression_ratio': 1.0,\n            'message': 'Image processing placeholder'\n        }\n    except Exception as e:\n        return {\n            'type': 'image',\n            'processed': False,\n            'error': str(e)\n        }\n\n\ndef _process_word_document(file_path: Path) -> Dict[str, Any]:\n    \"\"\"Process Word document\"\"\"\n    try:\n        # TODO: Implement Word document processing\n        file_size = file_path.stat().st_size\n        \n        return {\n            'type': 'word',\n            'processed': True,\n            'final_size_bytes': file_size,\n            'message': 'Word document processing placeholder'\n        }\n    except Exception as e:\n        return {\n            'type': 'word',\n            'processed': False,\n            'error': str(e)\n        }\n\n\ndef _process_generic_document(file_path: Path) -> Dict[str, Any]:\n    \"\"\"Process generic document\"\"\"\n    try:\n        file_size = file_path.stat().st_size\n        \n        return {\n            'type': 'generic',\n            'processed': True,\n            'final_size_bytes': file_size,\n            'message': 'Generic document processing completed'\n        }\n    except Exception as e:\n        return {\n            'type': 'generic',\n            'processed': False,\n            'error': str(e)\n        }\n\n\ndef _generate_image_thumbnail(file_path: Path, thumbnails_dir: Path, document_id: int) -> Optional[str]:\n    \"\"\"Generate thumbnail for image file\"\"\"\n    try:\n        # TODO: Implement actual thumbnail generation using PIL/Pillow\n        # For now, just copy the file as a placeholder\n        thumbnail_name = f\"thumb_{document_id}_{file_path.stem}.jpg\"\n        thumbnail_path = thumbnails_dir / thumbnail_name\n        \n        # Placeholder: copy original file (in real implementation, would resize)\n        shutil.copy2(file_path, thumbnail_path)\n        \n        return str(thumbnail_path)\n    except Exception as e:\n        logger.error(f\"Error generating image thumbnail: {e}\")\n        return None\n\n\ndef _generate_pdf_thumbnails(file_path: Path, thumbnails_dir: Path, document_id: int) -> list:\n    \"\"\"Generate thumbnails for PDF file\"\"\"\n    try:\n        # TODO: Implement PDF thumbnail generation using pdf2image or similar\n        # For now, return empty list\n        return []\n    except Exception as e:\n        logger.error(f\"Error generating PDF thumbnails: {e}\")\n        return []\n\n\ndef _update_document_processing_results(document_id: int, processing_result: Dict[str, Any], original_size: int):\n    \"\"\"Update document with processing results\"\"\"\n    try:\n        from src.models.documents import ClientDocument\n        from core import db\n        import json\n        \n        document = ClientDocument.query.get(document_id)\n        if document:\n            # Store processing metadata\n            processing_metadata = {\n                'processed_at': datetime.utcnow().isoformat(),\n                'original_size_bytes': original_size,\n                'processing_result': processing_result\n            }\n            \n            # Update document record (assuming we have a processing_metadata field)\n            # document.processing_metadata = json.dumps(processing_metadata)\n            # document.processing_completed = True\n            \n            db.session.commit()\n            logger.info(f\"Updated document {document_id} with processing results\")\n        \n    except Exception as e:\n        logger.error(f\"Error updating document processing results: {e}\")\n\n\ndef _update_document_thumbnails(document_id: int, thumbnail_paths: list):\n    \"\"\"Update document with thumbnail paths\"\"\"\n    try:\n        from src.models.documents import ClientDocument\n        from core import db\n        import json\n        \n        document = ClientDocument.query.get(document_id)\n        if document:\n            # Store thumbnail paths (assuming we have a thumbnails field)\n            # document.thumbnail_paths = json.dumps(thumbnail_paths)\n            \n            db.session.commit()\n            logger.info(f\"Updated document {document_id} with {len(thumbnail_paths)} thumbnails\")\n        \n    except Exception as e:\n        logger.error(f\"Error updating document thumbnails: {e}\")"}
