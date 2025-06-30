"""
AI Analysis Service - Comprehensive Document Analysis

Combines business workflows and AI provider orchestration for document analysis.
Handles high-level operations like analyzing checklists, managing providers,
and coordinating analysis workflows.

Consolidated from DocumentAnalysisService and AIAnalysisOrchestrator for
cleaner architecture following the Single Responsibility Principle.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .ai_providers import AIProviderFactory, AIProvider
from .result_combiner import AIResultCombiner
from .repository import DocumentAnalysisRepository
from src.shared.base import BaseService, transactional

logger = logging.getLogger(__name__)


class AIAnalysisService(BaseService):
    """
    Business service for document analysis workflows.
    
    Handles high-level operations like analyzing entire checklists,
    generating reports, and managing analysis workflows.
    """
    
    def __init__(self, config=None):
        """
        Initialize AI analysis service with provider orchestration
        
        Args:
            config: Configuration dictionary containing provider settings
        """
        super().__init__()
        self.config = config
        self.providers: List[AIProvider] = []
        self.primary_provider: Optional[AIProvider] = None
        
        # Initialize specialized components
        self.result_combiner = AIResultCombiner()
        self.repository = DocumentAnalysisRepository()
        
        # Initialize AI providers
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all available AI providers"""
        try:
            # Create all available providers
            self.providers = AIProviderFactory.create_all_available_providers(self.config)
            
            # Set primary provider (preference order: Azure, then Gemini)
            for provider in self.providers:
                if 'azure' in provider.get_provider_name().lower():
                    self.primary_provider = provider
                    break
            
            if not self.primary_provider and self.providers:
                self.primary_provider = self.providers[0]
            
            if self.providers:
                provider_names = [p.get_provider_name() for p in self.providers]
                logger.info(f"Initialized AI providers: {', '.join(provider_names)}")
                logger.info(f"Primary provider: {self.primary_provider.get_provider_name() if self.primary_provider else 'None'}")
            else:
                logger.warning("No AI providers available")
                
        except Exception as e:
            logger.error(f"Error initializing AI providers: {e}")
            self.providers = []
            self.primary_provider = None
    
    def is_available(self) -> bool:
        """Check if any AI providers are available"""
        return len(self.providers) > 0
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return [provider.get_provider_name() for provider in self.providers]
    
    def get_provider_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """Get capabilities of all available providers"""
        capabilities = {}
        for provider in self.providers:
            capabilities[provider.get_provider_name()] = provider.get_capabilities()
        return capabilities
    
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
            if not self.is_available():
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
                    document_path = self._get_document_path(document)
                    
                    if document_path and os.path.exists(document_path):
                        # Perform real AI analysis
                        logger.info(f"Starting AI analysis for document {document.id}: {os.path.basename(document_path)}")
                        results = self.analyze_document(document_path, document.id, firm_id=firm_id)
                        
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
            stats['available_providers'] = self.get_available_providers()
            stats['ai_services_available'] = self.is_available()
            
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
            return self.get_or_analyze_document(
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
    
    def analyze_document(self, document_path: str, document_id: int, 
                        preferred_providers: List[str] = None, 
                        firm_id: int = None) -> Dict[str, Any]:
        """
        Analyze a document using available AI providers
        
        Args:
            document_path: Path to the document file
            document_id: Database ID of the document
            preferred_providers: List of preferred provider names (optional)
            firm_id: Firm ID for access control
            
        Returns:
            Comprehensive analysis results dictionary
            
        Raises:
            ValueError: If no providers available or file not found
            Exception: If all providers fail
        """
        if not self.is_available():
            raise ValueError("No AI providers configured. Please configure provider credentials.")
        
        if not os.path.exists(document_path):
            raise ValueError(f"Document file not found: {document_path}")
        
        # Initialize results structure
        results = {
            'document_id': document_id,
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'providers_attempted': [],
            'providers_succeeded': [],
            'provider_results': {},
            'combined_analysis': {},
            'status': 'completed',
            'confidence_score': 0.0
        }
        
        # Determine which providers to use and in what order
        providers_to_use = self._get_providers_to_use(preferred_providers)
        
        analysis_errors = []
        successful_results = []
        
        # Attempt analysis with each provider
        for provider in providers_to_use:
            provider_name = provider.get_provider_name()
            results['providers_attempted'].append(provider_name)
            
            try:
                logger.info(f"Attempting analysis with {provider_name} for document {document_id}")
                
                # Validate document for this provider
                if not provider.validate_document(document_path):
                    logger.warning(f"Document validation failed for {provider_name}")
                    continue
                
                # Perform analysis
                provider_result = provider.analyze_document(document_path)
                
                # Store provider-specific results
                results['provider_results'][provider_name] = provider_result
                results['providers_succeeded'].append(provider_name)
                successful_results.append(provider_result)
                
                logger.info(f"Successfully analyzed document {document_id} with {provider_name}")
                
            except Exception as e:
                error_msg = f"{provider_name} analysis failed: {str(e)}"
                logger.error(f"Provider {provider_name} failed for document {document_id}: {e}")
                analysis_errors.append(error_msg)
                
                # Store error information
                results['provider_results'][provider_name] = {
                    'error': error_msg,
                    'provider': provider_name,
                    'timestamp': datetime.utcnow().isoformat()
                }
        
        # Process results
        if successful_results:
            # Combine results from successful providers
            results['combined_analysis'] = self.result_combiner.combine_provider_results(successful_results)
            results['confidence_score'] = self.result_combiner.calculate_overall_confidence(successful_results)
            
            # Include any partial errors for debugging
            if analysis_errors:
                results['partial_errors'] = analysis_errors
            
            # Save analysis results to database
            if self.repository.save_analysis_results(document_id, results):
                logger.info(f"Saved analysis results for document {document_id}")
            
            return results
        else:
            # All providers failed
            error_summary = "; ".join(analysis_errors) if analysis_errors else "All AI providers failed"
            results['status'] = 'failed'
            results['error'] = error_summary
            
            # Save failure to database
            self.repository.mark_analysis_failed(document_id, error_summary)
            
            raise Exception(f"AI analysis failed for document {document_id}: {error_summary}")
    
    def _get_providers_to_use(self, preferred_providers: List[str] = None) -> List[AIProvider]:
        """
        Determine which providers to use and in what order
        
        Args:
            preferred_providers: List of preferred provider names
            
        Returns:
            List of providers in order of preference
        """
        if not preferred_providers:
            # Use all available providers, with primary provider first
            if self.primary_provider:
                providers = [self.primary_provider]
                providers.extend([p for p in self.providers if p != self.primary_provider])
                return providers
            return self.providers
        
        # Filter providers based on preferences
        preferred = []
        for pref_name in preferred_providers:
            for provider in self.providers:
                if pref_name.lower() in provider.get_provider_name().lower():
                    preferred.append(provider)
                    break
        
        # Add any remaining providers
        remaining = [p for p in self.providers if p not in preferred]
        return preferred + remaining
    
    def get_or_analyze_document(self, document_id: int, firm_id: int, 
                               force_reanalysis: bool = False) -> Dict[str, Any]:
        """
        Get existing analysis or perform new analysis for a single document
        
        Args:
            document_id: Document ID
            firm_id: Firm ID for access control
            force_reanalysis: Force re-analysis even if results exist
            
        Returns:
            Analysis results or error information
        """
        try:
            # Check if analysis exists and force_reanalysis is not requested
            if not force_reanalysis:
                existing_results = self.repository.get_analysis_results(document_id, firm_id)
                if existing_results:
                    return {
                        'success': True,
                        'message': 'Using existing analysis results',
                        'analysis_results': existing_results,
                        'was_cached': True
                    }
            
            # Check if AI services are available
            if not self.is_available():
                return {
                    'success': False,
                    'error': 'AI services not configured',
                    'message': 'Please configure AI provider credentials'
                }
            
            # Get document and perform analysis
            document = self.repository.get_document_with_firm_check(document_id, firm_id)
            if not document:
                raise ValueError('Document not found or access denied')
            
            # Get document path
            document_path = self._get_document_path(document)
            if not document_path or not os.path.exists(document_path):
                raise ValueError(f'Document file not found: {document_path}')
            
            # Perform analysis
            results = self.analyze_document(document_path, document.id, firm_id=firm_id)
            
            return {
                'success': True,
                'message': 'Document analyzed successfully',
                'analysis_results': results,
                'was_cached': False
            }
            
        except Exception as e:
            logger.error(f"Error in get_or_analyze_document for document {document_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Analysis failed: {str(e)}'
            }
    
    def _get_document_path(self, document):
        """Get the file path for a document"""
        if document.file_path:
            # Check if it's an absolute path
            if os.path.isabs(document.file_path):
                return document.file_path
            else:
                # Relative path - assume it's relative to uploads directory
                return os.path.join('uploads', document.file_path)
        return None
    
    def add_provider(self, provider_name: str) -> bool:
        """
        Add a new provider at runtime
        
        Args:
            provider_name: Name of the provider to add
            
        Returns:
            True if provider was added successfully
        """
        try:
            new_provider = AIProviderFactory.create_provider(provider_name, self.config)
            if new_provider and new_provider.is_available():
                self.providers.append(new_provider)
                if not self.primary_provider:
                    self.primary_provider = new_provider
                logger.info(f"Added new AI provider: {provider_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to add provider {provider_name}: {e}")
            return False
    
    def is_ai_available(self) -> bool:
        """Check if AI analysis services are available"""
        return self.is_available()
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all AI providers"""
        return self.get_provider_capabilities()
    
    @staticmethod
    def get_ai_services_status(config) -> Dict[str, Any]:
        """
        Check the status of AI services
        
        Args:
            config: Application configuration
            
        Returns:
            Dict containing AI services status and availability
        """
        try:
            analysis_service = AIAnalysisService(config)
            
            # Get status from all providers
            provider_statuses = []
            azure_available = False
            gemini_available = False
            services_configured = []
            
            for provider in analysis_service.providers:
                provider_name = provider.get_provider_name().lower()
                is_available = provider.is_available()
                
                provider_statuses.append({
                    'name': provider_name,
                    'available': is_available,
                    'capabilities': provider.get_capabilities()
                })
                
                if 'azure' in provider_name and is_available:
                    azure_available = True
                    services_configured.append('Azure Document Intelligence')
                elif 'gemini' in provider_name and is_available:
                    gemini_available = True
                    services_configured.append('Google Gemini')
            
            status = {
                'ai_services_available': len(analysis_service.providers) > 0 and analysis_service.is_available(),
                'azure_available': azure_available,
                'gemini_available': gemini_available,
                'services_configured': services_configured,
                'total_providers': len(analysis_service.providers),
                'available_providers': len([p for p in analysis_service.providers if p.is_available()]),
                'provider_details': provider_statuses,
                'primary_provider': analysis_service.primary_provider.get_provider_name() if analysis_service.primary_provider else None
            }
            
            return status
            
        except Exception as e:
            return {
                'error': f'Failed to check AI services status: {str(e)}',
                'ai_services_available': False,
                'azure_available': False,
                'gemini_available': False,
                'services_configured': [],
                'total_providers': 0,
                'available_providers': 0
            }


# Aliases for backward compatibility with existing imports
DocumentAnalysisService = AIAnalysisService
AIService = AIAnalysisService