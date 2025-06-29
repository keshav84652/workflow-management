"""
AI Analysis Orchestrator

Coordinates AI document analysis by managing providers, combining results,
and handling persistence. This replaces the God Object AIService with a
focused orchestration service following the Single Responsibility Principle.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .ai_providers import AIProviderFactory, AIProvider
from .result_combiner import AIResultCombiner
from .repository import DocumentAnalysisRepository
from src.shared.base import BaseService

logger = logging.getLogger(__name__)


class AIAnalysisOrchestrator(BaseService):
    """
    Orchestrates AI document analysis using the Strategy Pattern.
    
    This service coordinates between multiple AI providers, combines their results,
    and manages persistence. It follows the Single Responsibility Principle by
    focusing only on orchestration, delegating specific tasks to specialized components.
    """
    
    def __init__(self, config=None):
        """
        Initialize AI analysis orchestrator
        
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
        
        # Initialize providers
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
            orchestrator = AIAnalysisOrchestrator(config)
            
            # Get status from all providers
            provider_statuses = []
            azure_available = False
            gemini_available = False
            services_configured = []
            
            for provider in orchestrator.providers:
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
                'ai_services_available': len(orchestrator.providers) > 0 and orchestrator.is_available(),
                'azure_available': azure_available,
                'gemini_available': gemini_available,
                'services_configured': services_configured,
                'total_providers': len(orchestrator.providers),
                'available_providers': len([p for p in orchestrator.providers if p.is_available()]),
                'provider_details': provider_statuses,
                'primary_provider': orchestrator.primary_provider.get_provider_name() if orchestrator.primary_provider else None
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