"""
Base AI Provider interface implementing the Strategy Pattern.

This module defines the abstract base class for all AI providers,
ensuring consistent interfaces for document analysis.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path


class AIProvider(ABC):
    """
    Abstract base class for AI document analysis providers.
    
    This implements the Strategy Pattern, allowing different AI providers
    to be used interchangeably while maintaining consistent interfaces.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the AI provider
        
        Args:
            config: Configuration dictionary containing provider-specific settings
        """
        self.config = config or {}
        self._capabilities = {}
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of this provider
        
        Returns:
            str: Provider name (e.g., "Azure Document Intelligence", "Google Gemini")
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this provider is available and properly configured
        
        Returns:
            bool: True if provider can be used, False otherwise
        """
        pass
    
    @abstractmethod
    def analyze_document(self, document_path: str) -> Dict[str, Any]:
        """
        Analyze a document using this provider
        
        Args:
            document_path: Path to the document file to analyze
            
        Returns:
            Dict containing analysis results with standardized format:
            {
                'provider': str,
                'confidence_score': float,
                'extracted_text': str,
                'fields': Dict[str, Any],
                'entities': List[Dict[str, Any]],
                'document_type': str,
                'raw_results': Dict[str, Any],  # Provider-specific raw data
                'analysis_timestamp': str
            }
            
        Raises:
            ValueError: If document path is invalid
            Exception: If analysis fails
        """
        pass
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get the capabilities of this provider
        
        Returns:
            Dict describing what this provider can do
        """
        return self._capabilities.copy()
    
    def validate_document(self, document_path: str) -> bool:
        """
        Validate that the document can be processed by this provider
        
        Args:
            document_path: Path to the document file
            
        Returns:
            bool: True if document can be processed, False otherwise
        """
        try:
            # Basic file existence and format checks
            path = Path(document_path)
            if not path.exists():
                return False
            
            # Check file size (most providers have limits)
            max_size_mb = self.config.get('max_file_size_mb', 50)
            file_size_mb = path.stat().st_size / (1024 * 1024)
            if file_size_mb > max_size_mb:
                return False
            
            # Check supported file types
            supported_extensions = self.get_supported_extensions()
            if supported_extensions and path.suffix.lower() not in supported_extensions:
                return False
            
            return True
            
        except Exception:
            return False
    
    def get_supported_extensions(self) -> List[str]:
        """
        Get file extensions supported by this provider
        
        Returns:
            List of supported file extensions (e.g., ['.pdf', '.jpg', '.png'])
        """
        # Default supported formats for most document analysis providers
        return ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp']
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on this provider
        
        Returns:
            Dict containing health status information
        """
        return {
            'provider': self.get_provider_name(),
            'available': self.is_available(),
            'capabilities': self.get_capabilities(),
            'supported_extensions': self.get_supported_extensions()
        }


class ProviderError(Exception):
    """Exception raised when a provider encounters an error"""
    
    def __init__(self, provider_name: str, message: str, original_error: Optional[Exception] = None):
        self.provider_name = provider_name
        self.original_error = original_error
        super().__init__(f"{provider_name}: {message}")


class ProviderUnavailableError(ProviderError):
    """Exception raised when a provider is not available or misconfigured"""
    pass


class DocumentValidationError(ProviderError):
    """Exception raised when a document cannot be processed by a provider"""
    pass