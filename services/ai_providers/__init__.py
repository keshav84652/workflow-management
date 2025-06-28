"""
AI Providers package for implementing the Strategy Pattern.
This allows easy addition of new AI providers without modifying existing code.
"""

from .base_provider import AIProvider
from .azure_provider import AzureProvider
from .gemini_provider import GeminiProvider
from .provider_factory import AIProviderFactory

__all__ = ['AIProvider', 'AzureProvider', 'GeminiProvider', 'AIProviderFactory']