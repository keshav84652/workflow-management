"""
Base AIProvider interface for implementing the Strategy Pattern.
All AI providers must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the AI provider with configuration
        
        Args:
            config: Configuration dictionary containing provider-specific settings
        """
        self.config = config
        self.is_initialized = False
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the AI provider with credentials and settings
        
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the provider is available and properly configured
        
        Returns:
            True if provider is ready for use, False otherwise
        """
        pass
    
    @abstractmethod
    def analyze_document(self, document_path: str) -> Dict[str, Any]:
        """
        Analyze a document using this provider
        
        Args:
            document_path: Path to the document file
            
        Returns:
            Analysis results dictionary with standardized format
            
        Raises:
            Exception: If analysis fails
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of this provider
        
        Returns:
            Provider name string
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get the capabilities of this provider
        
        Returns:
            Dictionary describing provider capabilities
        """
        pass
    
    def validate_document(self, document_path: str) -> bool:
        """
        Validate that the document can be processed by this provider
        
        Args:
            document_path: Path to the document file
            
        Returns:
            True if document is valid for this provider
        """
        import os
        
        if not os.path.exists(document_path):
            return False
        
        # Check file size (default max 20MB)
        max_size = self.config.get('max_file_size_mb', 20) * 1024 * 1024 if self.config else 20 * 1024 * 1024
        file_size = os.path.getsize(document_path)
        
        if file_size > max_size:
            return False
        
        # Check file extension
        supported_extensions = self.get_supported_file_types()
        file_extension = os.path.splitext(document_path)[1].lower()
        
        return file_extension in supported_extensions
    
    def get_supported_file_types(self) -> list:
        """
        Get list of supported file extensions
        
        Returns:
            List of supported file extensions (e.g., ['.pdf', '.png', '.jpg'])
        """
        # Default supported types - providers can override
        return ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp']
    
    def format_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """
        Format error information in a standardized way
        
        Args:
            error: The exception that occurred
            context: Additional context about when the error occurred
            
        Returns:
            Standardized error dictionary
        """
        return {
            'provider': self.get_provider_name(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'timestamp': self._get_timestamp()
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    def _standardize_results(self, raw_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert provider-specific results to standardized format
        
        Args:
            raw_results: Raw results from the provider
            
        Returns:
            Standardized results dictionary
        """
        return {
            'provider': self.get_provider_name(),
            'timestamp': self._get_timestamp(),
            'raw_results': raw_results,
            'extracted_text': raw_results.get('text', ''),
            'confidence_score': raw_results.get('confidence', 0.8),
            'document_type': raw_results.get('document_type', 'unknown'),
            'fields': raw_results.get('fields', {}),
            'entities': raw_results.get('entities', []),
            'metadata': raw_results.get('metadata', {})
        }