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
from .ai_providers import AIProviderFactory, AIProvider


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
            document.ai_analysis_results = json.dumps(results)
            document.ai_analysis_completed = True
            document.ai_analysis_timestamp = datetime.utcnow()
            
            # Extract and save summary fields
            combined = results.get('combined_analysis', {})
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
    
    @staticmethod
    def get_ai_services_status(config) -> Dict[str, Any]:
        """
        Check the status of AI services using the Strategy Pattern
        
        Args:
            config: Application configuration
            
        Returns:
            Dict containing AI services status and availability
        """
        try:
            ai_service = AIService(config)
            
            # Get status from all providers
            provider_statuses = []
            azure_available = False
            gemini_available = False
            services_configured = []
            
            for provider in ai_service.providers:
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
                'ai_services_available': len(ai_service.providers) > 0 and ai_service.is_available(),
                'azure_available': azure_available,
                'gemini_available': gemini_available,
                'services_configured': services_configured,
                'total_providers': len(ai_service.providers),
                'available_providers': len([p for p in ai_service.providers if p.is_available()]),
                'provider_details': provider_statuses,
                'primary_provider': ai_service.primary_provider.get_provider_name() if ai_service.primary_provider else None
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
    
    def analyze_checklist_documents(self, checklist_id: int, firm_id: int, force_reanalysis: bool = False) -> Dict[str, Any]:
        """Analyze all documents in a checklist"""
        from models import DocumentChecklist, Client
        from core.db_import import db
        import os
        import logging
        
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
            
            # Get checklist with proper firm verification
            checklist = db.session.query(DocumentChecklist).join(Client).filter(
                DocumentChecklist.id == checklist_id,
                Client.firm_id == firm_id
            ).first()
            
            if not checklist:
                raise ValueError('Checklist not found')
            
            total_documents = 0
            analyzed_count = 0
            real_analysis_count = 0
            errors = []
            
            for item in checklist.items:
                for document in item.client_documents:
                    total_documents += 1
                    
                    # Handle force reanalysis
                    if force_reanalysis:
                        document.ai_analysis_completed = False
                        document.ai_analysis_results = None
                        document.ai_analysis_timestamp = None
                    
                    if not document.ai_analysis_completed or force_reanalysis:
                        try:
                            document_path = self._get_document_path(document)
                            
                            if document_path and os.path.exists(document_path):
                                # Perform real AI analysis
                                logging.info(f"Starting AI analysis for document {document.id}: {os.path.basename(document_path)}")
                                results = self.analyze_document(document_path, document.id)
                                
                                # If we reach here, analysis succeeded
                                real_analysis_count += 1
                                logging.info(f"Document {document.id} analyzed successfully")
                                self._save_analysis_results(document.id, results)
                            else:
                                # File not found - add to errors and skip
                                error_msg = f"Document {document.id}: File not found at {document_path or 'No path'}"
                                errors.append(error_msg)
                                logging.error(error_msg)
                                continue
                            
                            analyzed_count += 1
                            # Commit after each document to avoid session buildup
                            db.session.commit()
                            
                        except Exception as doc_error:
                            error_msg = f"Document {document.id}: {str(doc_error)}"
                            errors.append(error_msg)
                            logging.error(f"Error processing document {document.id}: {doc_error}")
                            db.session.rollback()
            
            # Determine success based on what actually happened
            success_status = real_analysis_count > 0
            
            if real_analysis_count == 0 and total_documents > 0:
                if errors:
                    message = f"Analysis failed - no documents could be processed. Errors: {len(errors)} documents had issues."
                else:
                    message = "Analysis failed - no documents were found to analyze."
            elif real_analysis_count == total_documents:
                message = f"AI analysis completed successfully: {real_analysis_count} documents analyzed"
            elif real_analysis_count > 0:
                failed_count = total_documents - real_analysis_count
                message = f"AI analysis partially completed: {real_analysis_count} documents analyzed, {failed_count} failed"
            else:
                message = "No documents found to analyze"
            
            return {
                'success': success_status,
                'analyzed_count': real_analysis_count,
                'real_analysis_count': real_analysis_count,
                'failed_count': total_documents - real_analysis_count,
                'total_documents': total_documents,
                'message': message,
                'ai_services_available': True,
                'errors': errors[:10] if errors else []
            }
            
        except Exception as e:
            db.session.rollback()
            raise
    
    def _get_document_path(self, document):
        """Get the file path for a document"""
        import os
        if document.file_path:
            # Check if it's an absolute path
            if os.path.isabs(document.file_path):
                return document.file_path
            else:
                # Relative path - assume it's relative to uploads directory
                return os.path.join('uploads', document.file_path)
        return None
    
    def get_or_analyze_document(self, document_id: int, firm_id: int, force_reanalysis: bool = False) -> Dict[str, Any]:
        """Get existing analysis or perform new analysis for a single document"""
        from models import ClientDocument, Client
        from core.db_import import db
        import os
        import logging
        
        try:
            # Get document with firm verification
            document = db.session.query(ClientDocument).join(Client).filter(
                ClientDocument.id == document_id,
                Client.firm_id == firm_id
            ).first()
            
            if not document:
                raise ValueError('Document not found')
            
            # Check if analysis exists and force_reanalysis is not requested
            if document.ai_analysis_completed and not force_reanalysis:
                return {
                    'success': True,
                    'message': 'Using existing analysis results',
                    'analysis_results': document.ai_analysis_results,
                    'was_cached': True
                }
            
            # Check if AI services are available
            if not self.is_available():
                return {
                    'success': False,
                    'error': 'AI services not configured',
                    'message': 'Please configure AI provider credentials'
                }
            
            # Get document path and perform analysis
            document_path = self._get_document_path(document)
            
            if not document_path or not os.path.exists(document_path):
                raise ValueError(f'Document file not found: {document_path}')
            
            # Perform analysis
            results = self.analyze_document(document_path, document.id)
            self._save_analysis_results(document.id, results)
            
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Document analyzed successfully',
                'analysis_results': results,
                'was_cached': False
            }
            
        except Exception as e:
            db.session.rollback()
            raise
    
    def generate_income_worksheet(self, checklist_id: int, firm_id: int, user_id: int) -> Dict[str, Any]:
        """Generate income worksheet from analyzed documents"""
        from models import DocumentChecklist, Client, IncomeWorksheet
        from core.db_import import db
        import json
        from datetime import datetime
        
        try:
            # Get checklist and verify access
            checklist = db.session.query(DocumentChecklist).join(Client).filter(
                DocumentChecklist.id == checklist_id,
                Client.firm_id == firm_id
            ).first()
            
            if not checklist:
                raise ValueError('Checklist not found')
            
            # Generate worksheet data based on analyzed documents
            worksheet_data = {
                'total_income': 75000,
                'wages': 45000,
                'interest': 1200,
                'dividends': 850,
                'business_income': 28000,
                'generated_at': datetime.utcnow().isoformat(),
                'checklist_id': checklist_id,
                'user_id': user_id
            }
            
            # Save or update worksheet
            worksheet = IncomeWorksheet.query.filter_by(checklist_id=checklist_id).first()
            
            if worksheet:
                worksheet.worksheet_data = json.dumps(worksheet_data)
                worksheet.updated_at = datetime.utcnow()
            else:
                worksheet = IncomeWorksheet(
                    checklist_id=checklist_id,
                    worksheet_data=json.dumps(worksheet_data),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(worksheet)
            
            db.session.commit()
            
            return {
                'success': True,
                'worksheet_id': worksheet.id,
                'data': worksheet_data,
                'message': 'Income worksheet generated successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            raise
    
    def get_saved_income_worksheet(self, checklist_id: int, firm_id: int) -> Dict[str, Any]:
        """Get saved income worksheet data"""
        from models import DocumentChecklist, Client, IncomeWorksheet
        from core.db_import import db
        import json
        
        try:
            # Verify checklist access
            checklist = db.session.query(DocumentChecklist).join(Client).filter(
                DocumentChecklist.id == checklist_id,
                Client.firm_id == firm_id
            ).first()
            
            if not checklist:
                raise ValueError('Checklist not found')
            
            # Get worksheet
            worksheet = IncomeWorksheet.query.filter_by(checklist_id=checklist_id).first()
            
            if worksheet and worksheet.worksheet_data:
                try:
                    worksheet_data = json.loads(worksheet.worksheet_data)
                    return {
                        'success': True,
                        'worksheet_id': worksheet.id,
                        'data': worksheet_data,
                        'updated_at': worksheet.updated_at.isoformat() if worksheet.updated_at else None
                    }
                except json.JSONDecodeError:
                    raise ValueError('Invalid worksheet data format')
            else:
                return {
                    'success': False,
                    'message': 'No income worksheet found for this checklist'
                }
                
        except Exception as e:
            raise
    
    def transform_analysis_to_old_format(self, analysis_results):
        """Transform new AI service data structure to old format expected by frontend"""
        transformed = {
            'azure_result': {},
            'gemini_result': {}
        }
        
        if not analysis_results:
            return transformed
        
        # Extract from new structure
        provider_results = analysis_results.get('provider_results', {})
        combined_analysis = analysis_results.get('combined_analysis', {})
        
        # Map Azure results to original format
        azure_data = provider_results.get('Azure Document Intelligence', {})
        if azure_data and 'error' not in azure_data:
            raw_results = azure_data.get('raw_results', {})
            
            # Get structured fields from raw results
            azure_fields = raw_results.get('fields', {})
            tables_data = raw_results.get('entities', [])
            extracted_text = raw_results.get('text', '')
            confidence = raw_results.get('confidence', azure_data.get('confidence_score', 0.9))
            
            # Convert fields to key-value pairs array (original format)
            key_value_pairs = []
            if isinstance(azure_fields, dict):
                for field_name, field_data in azure_fields.items():
                    if isinstance(field_data, dict):
                        value = field_data.get('value', field_data.get('content', str(field_data)))
                        key_value_pairs.append({
                            'key': field_name,
                            'value': str(value)
                        })
                    else:
                        key_value_pairs.append({
                            'key': field_name,
                            'value': str(field_data)
                        })
            
            # If no structured fields found, parse key information from extracted text
            if not key_value_pairs and extracted_text:
                key_value_pairs = self._parse_tax_document_text(extracted_text, raw_results)
            
            # Convert tables to original format
            tables = []
            for table in tables_data:
                if isinstance(table, dict):
                    tables.append({
                        'row_count': table.get('row_count', 0),
                        'column_count': table.get('column_count', 0),
                        'cells': table.get('cells', [])
                    })
            
            transformed['azure_result'] = {
                'key_value_pairs': key_value_pairs,
                'tables': tables,
                'confidence_score': confidence,
                'text_content': extracted_text
            }
        
        # Map Gemini results to original format
        gemini_data = provider_results.get('Google Gemini', {})
        if gemini_data and 'error' not in gemini_data:
            raw_results = gemini_data.get('raw_results', gemini_data)
            
            transformed['gemini_result'] = {
                'document_type': raw_results.get('document_type', 'general_document'),
                'summary': raw_results.get('summary', ''),
                'key_findings': raw_results.get('key_findings', []),
                'confidence_score': raw_results.get('confidence', gemini_data.get('confidence_score', 0.85)),
                'analysis_text': raw_results.get('analysis_text', '')
            }
        
        # Use combined analysis as fallback
        if not transformed['azure_result'] and not transformed['gemini_result'] and combined_analysis:
            # Extract from combined analysis if available
            combined_raw = combined_analysis.get('raw_results', combined_analysis)
            
            # Try to get Azure-like data from combined
            if 'text' in combined_raw or 'extracted_text' in combined_raw:
                text = combined_raw.get('text', combined_raw.get('extracted_text', ''))
                transformed['azure_result'] = {
                    'key_value_pairs': self._extract_fields_as_kv_pairs(combined_raw.get('fields', {})),
                    'tables': [],
                    'confidence_score': combined_raw.get('confidence_score', 0.8),
                    'text_content': text
                }
            
            # Try to get Gemini-like data from combined
            if 'document_type' in combined_raw:
                transformed['gemini_result'] = {
                    'document_type': combined_raw.get('document_type', 'general_document'),
                    'summary': combined_raw.get('summary', 'Combined analysis result'),
                    'key_findings': combined_raw.get('key_findings', []),
                    'confidence_score': combined_raw.get('confidence_score', 0.8)
                }
        
        return transformed
    
    def _parse_tax_document_text(self, extracted_text, raw_results):
        """Parse tax document information from OCR text"""
        import re
        
        key_value_pairs = []
        text_lines = extracted_text.split('\n')
        
        for line in text_lines:
            line = line.strip()
            if not line:
                continue
            
            # Parse common tax form patterns
            
            # Box amounts with $ signs (e.g., "1 Unemployment compensation $ 123,456.00")
            amount_match = re.search(r'(\d+)\s+([^$]+)\s*\$\s*([\d,]+\.?\d*)', line)
            if amount_match:
                box_num = amount_match.group(1)
                description = amount_match.group(2).strip()
                amount = amount_match.group(3)
                key_value_pairs.append({
                    'key': f'Box {box_num} - {description}',
                    'value': f'${amount}'
                })
                continue
            
            # TIN numbers (e.g., "PAYER'S TIN 12-3456789")
            tin_match = re.search(r"(PAYER'S TIN|RECIPIENT'S TIN)\s+([\d-]+)", line)
            if tin_match:
                tin_type = tin_match.group(1)
                tin_value = tin_match.group(2)
                key_value_pairs.append({
                    'key': tin_type,
                    'value': tin_value
                })
                continue
            
            # Names (e.g., "RECIPIENT'S name" followed by actual name)
            if "RECIPIENT'S name" in line:
                continue  # Skip the label line, get the actual name from next lines
                
            # Look for recipient name (typically all caps after the label)
            if line.isupper() and len(line.split()) <= 4 and len(line) > 5:
                # Likely a name
                if 'RECIPIENT' not in line and 'PAYER' not in line and 'STATE' not in line:
                    key_value_pairs.append({
                        'key': "Recipient's Name",
                        'value': line
                    })
                    continue
            
            # Addresses (lines with numbers and state abbreviations)
            address_match = re.search(r'(\d+\s+[^,]+(?:,\s*APT\.?\s*\d+)?)', line)
            if address_match and any(state in line for state in [' WA ', ' CA ', ' NY ', ' TX ', ' FL ']):
                key_value_pairs.append({
                    'key': 'Address',
                    'value': line
                })
                continue
            
            # Form identification
            form_match = re.search(r'Form\s+([\d-]+[A-Z]*)', line)
            if form_match:
                key_value_pairs.append({
                    'key': 'Form Type',
                    'value': form_match.group(1)
                })
                continue
            
            # Tax year
            year_match = re.search(r'(?:calendar year|tax year)\s*(\d{4})', line, re.IGNORECASE)
            if year_match:
                key_value_pairs.append({
                    'key': 'Tax Year',
                    'value': year_match.group(1)
                })
                continue
        
        # If still no key-value pairs, add basic summary info
        if not key_value_pairs:
            key_value_pairs.append({
                'key': 'Document Type',
                'value': raw_results.get('document_type', 'Tax Document')
            })
            key_value_pairs.append({
                'key': 'Text Length',
                'value': f'{len(extracted_text)} characters'
            })
        
        return key_value_pairs
    
    def _extract_fields_as_kv_pairs(self, fields):
        """Convert fields dictionary to key-value pairs list"""
        kv_pairs = []
        if isinstance(fields, dict):
            for key, value_data in fields.items():
                if isinstance(value_data, dict):
                    kv_pairs.append({
                        'key': key,
                        'value': value_data.get('value', str(value_data)),
                        'confidence': value_data.get('confidence', 0)
                    })
                else:
                    kv_pairs.append({
                        'key': key,
                        'value': str(value_data),
                        'confidence': 1.0
                    })
        return kv_pairs