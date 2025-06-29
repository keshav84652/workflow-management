"""
Document Analysis Business Service

Handles high-level business workflows for document analysis,
including checklist processing and income worksheet generation.

This extracts the business logic from the original AIService God Object.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from .ai_orchestrator import AIAnalysisOrchestrator
from .repository import DocumentAnalysisRepository
from services.base import BaseService, transactional

logger = logging.getLogger(__name__)


class DocumentAnalysisService(BaseService):
    """
    Business service for document analysis workflows.
    
    Handles high-level operations like analyzing entire checklists,
    generating reports, and managing analysis workflows.
    """
    
    def __init__(self, config=None):
        """
        Initialize document analysis service
        
        Args:
            config: Configuration for AI providers
        """
        super().__init__()
        self.orchestrator = AIAnalysisOrchestrator(config)
        self.repository = DocumentAnalysisRepository()
    
    @transactional
    def analyze_checklist_documents(self, checklist_id: int, firm_id: int, 
                                  force_reanalysis: bool = False) -> Dict[str, Any]:
        """
        Analyze all documents in a checklist
        
        Args:
            checklist_id: Checklist ID
            firm_id: Firm ID for access control
            force_reanalysis: Force re-analysis of already processed documents
            
        Returns:
            Dictionary with analysis results and statistics
        """
        try:
            # First check if AI services are available
            if not self.orchestrator.is_available():
                return {
                    'success': False,
                    'error': 'AI services not configured',
                    'message': 'Please configure GEMINI_API_KEY or Azure Document Intelligence to enable AI analysis',
                    'ai_services_available': False,
                    'analyzed_count': 0,
                    'total_documents': 0
                }
            
            # Get all documents for the checklist
            documents = self.repository.get_checklist_documents(checklist_id, firm_id)
            
            if not documents:
                return {
                    'success': False,
                    'message': 'No documents found in checklist',
                    'analyzed_count': 0,
                    'total_documents': 0
                }
            
            total_documents = len(documents)
            analyzed_count = 0
            real_analysis_count = 0
            errors = []
            
            for document in documents:
                # Handle force reanalysis
                if force_reanalysis:
                    self.repository.clear_analysis_results(document.id)
                
                # Check if analysis is needed
                existing_results = self.repository.get_analysis_results(document.id, firm_id)
                if existing_results and not force_reanalysis:
                    analyzed_count += 1
                    continue
                
                try:
                    # Get document path
                    document_path = self.orchestrator._get_document_path(document)
                    
                    if document_path and os.path.exists(document_path):
                        # Perform real AI analysis
                        logger.info(f"Starting AI analysis for document {document.id}: {os.path.basename(document_path)}")
                        results = self.orchestrator.analyze_document(document_path, document.id, firm_id=firm_id)
                        
                        # If we reach here, analysis succeeded
                        real_analysis_count += 1
                        analyzed_count += 1
                        logger.info(f"Document {document.id} analyzed successfully")
                    else:
                        # File not found - add to errors
                        error_msg = f"Document {document.id}: File not found at {document_path or 'No path'}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                        continue
                    
                except Exception as doc_error:
                    error_msg = f"Document {document.id}: {str(doc_error)}"
                    errors.append(error_msg)
                    logger.error(f"Error processing document {document.id}: {doc_error}")
            
            # Determine success based on what actually happened
            success_status = real_analysis_count > 0 or (analyzed_count > 0 and not force_reanalysis)
            
            if real_analysis_count == 0 and total_documents > 0:
                if errors:
                    message = f"Analysis failed - no documents could be processed. Errors: {len(errors)} documents had issues."
                else:
                    message = "Analysis failed - no documents were found to analyze."
            elif real_analysis_count == total_documents:
                message = f"AI analysis completed successfully: {real_analysis_count} documents analyzed"
            elif real_analysis_count > 0:
                failed_count = total_documents - analyzed_count
                message = f"AI analysis partially completed: {analyzed_count} documents processed ({real_analysis_count} newly analyzed), {failed_count} failed"
            else:
                message = f"Analysis completed: {analyzed_count} documents already processed"
            
            return {
                'success': success_status,
                'analyzed_count': analyzed_count,
                'newly_analyzed_count': real_analysis_count,
                'failed_count': total_documents - analyzed_count,
                'total_documents': total_documents,
                'message': message,
                'ai_services_available': True,
                'errors': errors[:10] if errors else []  # Limit error list size
            }
            
        except Exception as e:
            logger.error(f"Error analyzing checklist {checklist_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Analysis failed: {str(e)}',
                'analyzed_count': 0,
                'total_documents': 0
            }
    
    def get_analysis_summary(self, firm_id: int) -> Dict[str, Any]:
        """
        Get analysis summary statistics for a firm
        
        Args:
            firm_id: Firm ID
            
        Returns:
            Dictionary with analysis statistics
        """
        try:
            stats = self.repository.get_analysis_statistics(firm_id)
            
            # Add provider information
            stats['available_providers'] = self.orchestrator.get_available_providers()
            stats['ai_services_available'] = self.orchestrator.is_available()
            
            return {
                'success': True,
                'statistics': stats
            }
            
        except Exception as e:
            logger.error(f"Error getting analysis summary for firm {firm_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'statistics': {}
            }
    
    def analyze_single_document(self, document_id: int, firm_id: int, 
                               force_reanalysis: bool = False) -> Dict[str, Any]:
        """
        Analyze a single document
        
        Args:
            document_id: Document ID
            firm_id: Firm ID for access control
            force_reanalysis: Force re-analysis even if results exist
            
        Returns:
            Analysis results
        """
        try:
            return self.orchestrator.get_or_analyze_document(
                document_id, firm_id, force_reanalysis
            )
        except Exception as e:
            logger.error(f"Error analyzing document {document_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Analysis failed: {str(e)}'
            }
    
    def get_document_types_summary(self, firm_id: int) -> Dict[str, Any]:
        """
        Get summary of document types identified by AI analysis
        
        Args:
            firm_id: Firm ID
            
        Returns:
            Dictionary with document type statistics
        """
        try:
            stats = self.repository.get_analysis_statistics(firm_id)
            document_types = stats.get('document_types', {})
            
            # Calculate percentages
            total_analyzed = stats.get('analyzed_documents', 0)
            type_percentages = {}
            
            if total_analyzed > 0:
                for doc_type, count in document_types.items():
                    type_percentages[doc_type] = {
                        'count': count,
                        'percentage': (count / total_analyzed) * 100
                    }
            
            return {
                'success': True,
                'document_types': type_percentages,
                'total_analyzed': total_analyzed,
                'average_confidence': stats.get('average_confidence', 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting document types summary for firm {firm_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'document_types': {}
            }
    
    def is_ai_available(self) -> bool:
        """Check if AI analysis services are available"""
        return self.orchestrator.is_available()
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all AI providers"""
        return self.orchestrator.get_provider_capabilities()


# Alias for backward compatibility with existing imports
AIService = DocumentAnalysisService