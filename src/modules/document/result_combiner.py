"""
AI Result Combiner Service

Handles combining and consolidating results from multiple AI providers
using weighted algorithms and confidence scoring.

This extracts the result combination logic from the AIService God Object.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class AIResultCombiner:
    """
    Service responsible for combining results from multiple AI providers.
    
    This implements sophisticated algorithms to merge, deduplicate, and 
    score results from different AI analysis providers.
    """
    
    def __init__(self):
        """Initialize the result combiner"""
        self.combination_strategies = {
            'weighted_merge': self._weighted_merge_strategy,
            'highest_confidence': self._highest_confidence_strategy,
            'consensus': self._consensus_strategy
        }
    
    def combine_provider_results(self, results: List[Dict[str, Any]], 
                               strategy: str = 'weighted_merge') -> Dict[str, Any]:
        """
        Combine results from multiple providers into a unified result
        
        Args:
            results: List of provider results
            strategy: Combination strategy to use
            
        Returns:
            Combined analysis result
        """
        if not results:
            return {}
        
        if len(results) == 1:
            return results[0]
        
        # Use specified combination strategy
        combiner_func = self.combination_strategies.get(strategy, self._weighted_merge_strategy)
        return combiner_func(results)
    
    def _weighted_merge_strategy(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Combine results using weighted merge based on confidence scores
        
        Args:
            results: List of provider results
            
        Returns:
            Combined result using weighted averaging
        """
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
    
    def _highest_confidence_strategy(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Select the result with the highest confidence score
        
        Args:
            results: List of provider results
            
        Returns:
            Result from the provider with highest confidence
        """
        best_result = max(results, key=lambda r: r.get('confidence_score', 0))
        best_result['combination_method'] = 'highest_confidence'
        best_result['metadata'] = {
            'providers_evaluated': len(results),
            'selected_provider': best_result.get('provider', 'unknown'),
            'combination_timestamp': datetime.utcnow().isoformat()
        }
        return best_result
    
    def _consensus_strategy(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Combine results using consensus approach (majority wins)
        
        Args:
            results: List of provider results
            
        Returns:
            Combined result based on consensus
        """
        # For now, implement as weighted merge
        # TODO: Implement true consensus algorithm
        combined = self._weighted_merge_strategy(results)
        combined['combination_method'] = 'consensus'
        return combined
    
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
            if confidence > best_confidence and i < len(texts):
                best_confidence = confidence
                best_text = texts[i]
        
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
    
    def calculate_overall_confidence(self, results: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence for the analysis"""
        if not results:
            return 0.0
        
        # Simple average for overall confidence
        confidences = [r.get('confidence_score', 0) for r in results]
        return sum(confidences) / len(confidences)
    
    def validate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate provider results before combination
        
        Args:
            results: List of provider results to validate
            
        Returns:
            Validation report with any issues found
        """
        validation_report = {
            'valid': True,
            'issues': [],
            'warnings': [],
            'valid_results_count': 0
        }
        
        valid_results = []
        
        for i, result in enumerate(results):
            result_issues = []
            
            # Check required fields
            if 'provider' not in result:
                result_issues.append(f"Result {i}: Missing provider field")
            
            if 'confidence_score' not in result:
                result_issues.append(f"Result {i}: Missing confidence_score")
            elif not isinstance(result['confidence_score'], (int, float)):
                result_issues.append(f"Result {i}: Invalid confidence_score type")
            elif not 0 <= result['confidence_score'] <= 1:
                result_issues.append(f"Result {i}: confidence_score out of range [0,1]")
            
            # Check for empty results
            if not result.get('extracted_text', '').strip():
                validation_report['warnings'].append(f"Result {i}: Empty extracted text")
            
            if result_issues:
                validation_report['issues'].extend(result_issues)
                validation_report['valid'] = False
            else:
                valid_results.append(result)
                validation_report['valid_results_count'] += 1
        
        return validation_report