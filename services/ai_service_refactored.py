"""
Refactored AI Service implementing the Strategy Pattern.
This service orchestrates multiple AI providers without being tightly coupled to any specific implementation.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.db_import import db
from models import ClientDocument
from services.base import BaseService
from services.ai_providers import AIProviderFactory, AIProvider


class AIService(BaseService):
    """
    AI service that orchestrates multiple AI providers using the Strategy Pattern.
    This follows the Open/Closed Principle - new providers can be added without modifying this class.
    """
    
    def __init__(self, config=None):
        """
        Initialize AI service with configuration
        
        Args:
            config: Configuration dictionary or object containing provider settings
        """
        super().__init__()
        self.config = config
        self.providers: List[AIProvider] = []
        self.primary_provider: Optional[AIProvider] = None
        
        # Initialize all available providers
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
                logging.info(f"Initialized AI providers: {', '.join(provider_names)}")
                logging.info(f"Primary provider: {self.primary_provider.get_provider_name() if self.primary_provider else 'None'}")
            else:
                logging.warning("No AI providers available")
                
        except Exception as e:
            logging.error(f"Error initializing AI providers: {e}")
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
                        preferred_providers: List[str] = None) -> Dict[str, Any]:
        """
        Analyze a document using available AI providers
        
        Args:
            document_path: Path to the document file
            document_id: Database ID of the document
            preferred_providers: List of preferred provider names (optional)
            
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
                logging.info(f"Attempting analysis with {provider_name} for document {document_id}")
                
                # Validate document for this provider
                if not provider.validate_document(document_path):
                    logging.warning(f"Document validation failed for {provider_name}")
                    continue
                
                # Perform analysis
                provider_result = provider.analyze_document(document_path)
                
                # Store provider-specific results
                results['provider_results'][provider_name] = provider_result
                results['providers_succeeded'].append(provider_name)
                successful_results.append(provider_result)
                
                logging.info(f"Successfully analyzed document {document_id} with {provider_name}")
                
            except Exception as e:
                error_msg = f"{provider_name} analysis failed: {str(e)}"
                logging.error(f"Provider {provider_name} failed for document {document_id}: {e}")
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
            results['combined_analysis'] = self._combine_provider_results(successful_results)
            results['confidence_score'] = self._calculate_overall_confidence(successful_results)
            
            # Include any partial errors for debugging
            if analysis_errors:
                results['partial_errors'] = analysis_errors
            
            # Save analysis results to database
            self._save_analysis_results(document_id, results)
            
            return results
        else:
            # All providers failed
            error_summary = "; ".join(analysis_errors) if analysis_errors else "All AI providers failed"
            results['status'] = 'failed'
            results['error'] = error_summary
            
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
    
    def _combine_provider_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Combine results from multiple providers into a unified result
        
        Args:
            results: List of provider results
            
        Returns:
            Combined analysis result
        """
        if not results:
            return {}
        
        if len(results) == 1:
            return results[0]
        
        # Combine text from all providers
        combined_text = self._combine_extracted_text(results)
        
        # Combine fields (prioritize higher confidence fields)
        combined_fields = self._combine_fields(results)
        
        # Combine entities
        combined_entities = self._combine_entities(results)
        
        # Determine best document type
        document_type = self._determine_best_document_type(results)
        
        # Calculate combined confidence
        combined_confidence = self._calculate_combined_confidence(results)
        
        return {
            'extracted_text': combined_text,
            'fields': combined_fields,
            'entities': combined_entities,
            'document_type': document_type,
            'confidence_score': combined_confidence,
            'providers_used': [r.get('provider', 'unknown') for r in results],
            'combination_method': 'weighted_merge',
            'metadata': {
                'total_providers': len(results),
                'combination_timestamp': datetime.utcnow().isoformat()
            }
        }
    
    def _combine_extracted_text(self, results: List[Dict[str, Any]]) -> str:
        """Combine extracted text from multiple providers"""
        texts = []
        for result in results:
            text = result.get('extracted_text', '')
            if text and text.strip():
                texts.append(text.strip())
        
        if not texts:
            return ''
        
        # If texts are very similar, return the longest one
        if len(texts) == 1:
            return texts[0]
        
        # For multiple texts, return the one with highest confidence
        best_text = texts[0]
        best_confidence = results[0].get('confidence_score', 0)
        
        for i, result in enumerate(results[1:], 1):
            confidence = result.get('confidence_score', 0)
            if confidence > best_confidence:
                best_confidence = confidence
                best_text = texts[i] if i < len(texts) else best_text
        
        return best_text
    
    def _combine_fields(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine field extractions from multiple providers"""
        combined = {}
        
        for result in results:
            fields = result.get('fields', {})
            provider_confidence = result.get('confidence_score', 0)
            
            for field_name, field_data in fields.items():
                if field_name not in combined:
                    combined[field_name] = field_data
                else:
                    # Keep field with higher confidence
                    existing_confidence = combined[field_name].get('confidence', 0)
                    new_confidence = field_data.get('confidence', provider_confidence)
                    
                    if new_confidence > existing_confidence:
                        combined[field_name] = field_data
        
        return combined
    
    def _combine_entities(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Combine entities from multiple providers"""
        all_entities = []
        seen_entities = set()
        
        for result in results:
            entities = result.get('entities', [])
            for entity in entities:
                entity_key = f"{entity.get('type', '')}:{entity.get('value', '')}"
                if entity_key not in seen_entities:
                    all_entities.append(entity)
                    seen_entities.add(entity_key)
        
        return all_entities
    
    def _determine_best_document_type(self, results: List[Dict[str, Any]]) -> str:
        """Determine the best document type from multiple provider results"""
        type_votes = {}
        
        for result in results:
            doc_type = result.get('document_type', 'unknown')
            confidence = result.get('confidence_score', 0)
            
            if doc_type not in type_votes:
                type_votes[doc_type] = 0
            type_votes[doc_type] += confidence
        
        if not type_votes:
            return 'unknown'
        
        return max(type_votes.items(), key=lambda x: x[1])[0]
    
    def _calculate_combined_confidence(self, results: List[Dict[str, Any]]) -> float:
        """Calculate combined confidence score"""
        if not results:
            return 0.0
        
        confidences = [r.get('confidence_score', 0) for r in results]
        # Use weighted average, giving more weight to higher confidence scores
        total_weight = sum(confidences)
        if total_weight == 0:
            return 0.0
        
        weighted_sum = sum(c * c for c in confidences)  # Square for weighting
        return weighted_sum / total_weight
    
    def _calculate_overall_confidence(self, results: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence for the analysis"""
        if not results:
            return 0.0
        
        # Simple average for now
        confidences = [r.get('confidence_score', 0) for r in results]
        return sum(confidences) / len(confidences)
    
    def _save_analysis_results(self, document_id: int, results: Dict[str, Any]):
        """
        Save analysis results to the database
        
        Args:
            document_id: Document ID
            results: Analysis results to save
        """
        try:
            # Find the document
            document = ClientDocument.query.get(document_id)
            if not document:
                logging.warning(f"Document {document_id} not found for saving AI results")
                return
            
            # Save analysis data
            document.ai_analysis_data = json.dumps(results)
            document.ai_analysis_completed = True
            document.ai_analysis_timestamp = datetime.utcnow()
            
            # Extract and save summary fields
            combined = results.get('combined_analysis', {})
            document.ai_extracted_text = combined.get('extracted_text', '')[:2000]  # Limit length
            document.ai_confidence_score = results.get('confidence_score', 0)
            document.ai_document_type = combined.get('document_type', 'unknown')
            
            db.session.commit()
            logging.info(f"Saved AI analysis results for document {document_id}")
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Failed to save AI analysis results for document {document_id}: {e}")
    
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
                logging.info(f"Added new AI provider: {provider_name}")
                return True
            return False
        except Exception as e:
            logging.error(f"Failed to add provider {provider_name}: {e}")
            return False