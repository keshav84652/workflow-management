"""
AI Worker for CPA WorkflowPilot
Background tasks for AI document analysis and processing.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional

from celery import Task
from celery_app import celery_app
from events.publisher import publish_event
from events.schemas import (
    DocumentAnalysisStartedEvent,
    DocumentAnalysisCompletedEvent,
    DocumentAnalysisFailedEvent,
    ErrorEvent
)

logger = logging.getLogger(__name__)


class AIAnalysisTask(Task):
    """Custom task class for AI analysis with retry logic"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        logger.error(f"AI analysis task {task_id} failed: {exc}")
        
        # Publish failure event
        if len(args) >= 3:  # document_id, document_name, file_path
            document_id, document_name = args[0], args[1]
            
            failure_event = DocumentAnalysisFailedEvent(
                document_id=document_id,
                document_name=document_name,
                error_message=str(exc),
                error_type=type(exc).__name__,
                retry_count=self.request.retries
            )
            publish_event(failure_event)


@celery_app.task(bind=True, base=AIAnalysisTask, name='workers.ai_worker.analyze_document')
def analyze_document(self, document_id: int, document_name: str, file_path: str, 
                    checklist_id: Optional[int] = None, firm_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Analyze a document using AI services in the background
    
    Args:
        document_id: Database ID of the document
        document_name: Name of the document file
        file_path: Path to the document file
        checklist_id: Optional checklist ID this document belongs to
        firm_id: Firm ID for context
        
    Returns:
        dict: Analysis results
    """
    start_time = time.time()
    
    try:
        logger.info(f"Starting AI analysis for document {document_id}: {document_name}")
        
        # Publish analysis started event
        started_event = DocumentAnalysisStartedEvent(
            document_id=document_id,
            document_name=document_name,
            file_type=file_path.split('.')[-1] if '.' in file_path else 'unknown',
            checklist_id=checklist_id,
            analysis_service="ai_worker",
            firm_id=firm_id
        )
        publish_event(started_event)
        
        # Import AI service (lazy import to avoid circular dependencies)
        from services.ai_service import AIService
        from config import get_config
        
        # Initialize AI service
        config = get_config()()
        ai_service = AIService(config.__dict__)
        
        if not ai_service.is_available():
            raise RuntimeError("AI services not available - no API keys configured")
        
        # Perform the analysis
        analysis_result = ai_service.analyze_document_file(file_path)
        
        if not analysis_result.get('success', False):
            raise RuntimeError(f"AI analysis failed: {analysis_result.get('error', 'Unknown error')}")
        
        # Extract results
        document_type = analysis_result.get('document_type', 'Unknown')
        confidence_score = analysis_result.get('confidence_score', 0.0)
        analysis_data = analysis_result.get('analysis_results', {})
        
        # Update database
        _update_document_analysis_results(
            document_id=document_id,
            document_type=document_type,
            confidence_score=confidence_score,
            analysis_results=analysis_data
        )
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000
        
        # Publish completion event
        completed_event = DocumentAnalysisCompletedEvent(
            document_id=document_id,
            document_name=document_name,
            analysis_results=analysis_data,
            confidence_score=confidence_score,
            document_type=document_type,
            processing_time_ms=processing_time,
            firm_id=firm_id
        )
        publish_event(completed_event)
        
        logger.info(f"Completed AI analysis for document {document_id} in {processing_time:.2f}ms")
        
        return {
            'success': True,
            'document_id': document_id,
            'document_type': document_type,
            'confidence_score': confidence_score,
            'processing_time_ms': processing_time,
            'analysis_results': analysis_data
        }
        
    except Exception as e:
        logger.error(f"Error analyzing document {document_id}: {e}")
        
        # Publish failure event
        failure_event = DocumentAnalysisFailedEvent(
            document_id=document_id,
            document_name=document_name,
            error_message=str(e),
            error_type=type(e).__name__,
            retry_count=self.request.retries,
            firm_id=firm_id
        )
        publish_event(failure_event)
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying AI analysis for document {document_id} (retry {self.request.retries + 1})")
            raise self.retry(countdown=60 * (self.request.retries + 1))  # Exponential backoff
        
        # Max retries reached
        return {
            'success': False,
            'document_id': document_id,
            'error': str(e),
            'retry_count': self.request.retries
        }


@celery_app.task(name='workers.ai_worker.analyze_checklist')
def analyze_checklist(checklist_id: int, firm_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Analyze all documents in a checklist
    
    Args:
        checklist_id: Database ID of the checklist
        firm_id: Firm ID for context
        
    Returns:
        dict: Analysis summary
    """
    try:
        logger.info(f"Starting checklist analysis for checklist {checklist_id}")
        
        # Import models (lazy import)
        from models.documents import DocumentChecklist, ClientDocument
        from src.shared.database.db_import import db
        
        # Get checklist and documents
        checklist = DocumentChecklist.query.get(checklist_id)
        if not checklist:
            raise ValueError(f"Checklist {checklist_id} not found")
        
        # Queue analysis tasks for all documents
        analysis_tasks = []
        total_documents = 0
        
        for item in checklist.items:
            for document in item.client_documents:
                if not document.ai_analysis_completed and document.file_path:
                    # Queue background analysis
                    task = analyze_document.delay(
                        document_id=document.id,
                        document_name=document.original_filename or f"document_{document.id}",
                        file_path=document.file_path,
                        checklist_id=checklist_id,
                        firm_id=firm_id
                    )
                    analysis_tasks.append(task.id)
                    total_documents += 1
        
        logger.info(f"Queued {total_documents} documents for analysis from checklist {checklist_id}")
        
        return {
            'success': True,
            'checklist_id': checklist_id,
            'queued_documents': total_documents,
            'task_ids': analysis_tasks
        }
        
    except Exception as e:
        logger.error(f"Error analyzing checklist {checklist_id}: {e}")
        
        # Publish error event
        error_event = ErrorEvent(
            error_type=type(e).__name__,
            error_message=str(e),
            context={'checklist_id': checklist_id, 'firm_id': firm_id},
            firm_id=firm_id
        )
        publish_event(error_event)
        
        return {
            'success': False,
            'checklist_id': checklist_id,
            'error': str(e)
        }


@celery_app.task(name='workers.ai_worker.batch_analyze_documents')
def batch_analyze_documents(document_ids: list, firm_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Analyze multiple documents in batch
    
    Args:
        document_ids: List of document IDs to analyze
        firm_id: Firm ID for context
        
    Returns:
        dict: Batch analysis summary
    """
    try:
        logger.info(f"Starting batch analysis for {len(document_ids)} documents")
        
        # Import models (lazy import)
        from models.documents import ClientDocument
        
        analysis_tasks = []
        successful_queued = 0
        
        for doc_id in document_ids:
            try:
                document = ClientDocument.query.get(doc_id)
                if document and not document.ai_analysis_completed and document.file_path:
                    # Queue background analysis
                    task = analyze_document.delay(
                        document_id=document.id,
                        document_name=document.original_filename or f"document_{document.id}",
                        file_path=document.file_path,
                        checklist_id=document.checklist_item.checklist_id if document.checklist_item else None,
                        firm_id=firm_id
                    )
                    analysis_tasks.append(task.id)
                    successful_queued += 1
                    
            except Exception as e:
                logger.warning(f"Could not queue document {doc_id} for analysis: {e}")
        
        logger.info(f"Successfully queued {successful_queued} documents for batch analysis")
        
        return {
            'success': True,
            'requested_documents': len(document_ids),
            'queued_documents': successful_queued,
            'task_ids': analysis_tasks
        }
        
    except Exception as e:
        logger.error(f"Error in batch document analysis: {e}")
        
        return {
            'success': False,
            'error': str(e),
            'requested_documents': len(document_ids)
        }


def _update_document_analysis_results(document_id: int, document_type: str, 
                                     confidence_score: float, analysis_results: Dict[str, Any]):
    """
    Update document with AI analysis results
    
    Args:
        document_id: Document ID
        document_type: Detected document type
        confidence_score: Analysis confidence score
        analysis_results: Full analysis results
    """
    try:
        # Import models and database (lazy import)
        from models.documents import ClientDocument
        from src.shared.database.db_import import db
        import json
        
        document = ClientDocument.query.get(document_id)
        if document:
            document.ai_analysis_completed = True
            document.ai_analysis_timestamp = datetime.utcnow()
            document.ai_document_type = document_type
            document.ai_confidence_score = confidence_score
            document.ai_analysis_results = json.dumps(analysis_results)
            
            db.session.commit()
            logger.info(f"Updated document {document_id} with AI analysis results")
        else:
            logger.warning(f"Document {document_id} not found for result update")
            
    except Exception as e:
        logger.error(f"Error updating document {document_id} with AI results: {e}")
        # Don't raise here - we don't want to fail the task if DB update fails
