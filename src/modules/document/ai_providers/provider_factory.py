"""
AI Provider Factory for creating and managing AI providers.
Implements the Factory Pattern to simplify provider instantiation.
"""

import logging
from typing import Dict, Any, List, Optional

from .base_provider import AIProvider
from .azure_provider import AzureProvider
from .gemini_provider import GeminiProvider


class AIProviderFactory:
    """Factory for creating and managing AI providers"""
    
    # Registry of available providers
    AVAILABLE_PROVIDERS = {
        'azure': AzureProvider,
        'gemini': GeminiProvider
    }
    
    @classmethod
    def create_provider(cls, provider_name: str, config: Optional[Dict[str, Any]] = None) -> Optional[AIProvider]:
        """
        Create a specific AI provider
        
        Args:
            provider_name: Name of the provider ('azure', 'gemini')
            config: Configuration dictionary
            
        Returns:
            Initialized AIProvider instance or None if failed
        """
        provider_name = provider_name.lower()
        
        if provider_name not in cls.AVAILABLE_PROVIDERS:
            logging.error(f"Unknown provider: {provider_name}")
            return None
        
        try:
            provider_class = cls.AVAILABLE_PROVIDERS[provider_name]
            provider = provider_class(config)
            
            if provider.initialize():
                logging.info(f"Successfully created {provider_name} provider")
                return provider
            else:
                logging.warning(f"Failed to initialize {provider_name} provider")
                return None
                
        except Exception as e:
            logging.error(f"Error creating {provider_name} provider: {e}")
            return None
    
    @classmethod
    def create_all_available_providers(cls, config: Optional[Dict[str, Any]] = None) -> List[AIProvider]:
        """
        Create all available providers that can be initialized
        
        Args:
            config: Configuration dictionary
            
        Returns:
            List of successfully initialized providers
        """
        providers = []
        
        for provider_name in cls.AVAILABLE_PROVIDERS.keys():
            provider = cls.create_provider(provider_name, config)
            if provider and provider.is_available():
                providers.append(provider)
        
        logging.info(f"Created {len(providers)} available AI providers")
        return providers
    
    @classmethod
    def get_provider_capabilities(cls, provider_name: str, config: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Get capabilities of a specific provider without full initialization
        
        Args:
            provider_name: Name of the provider
            config: Configuration dictionary
            
        Returns:
            Provider capabilities or None if provider not available
        """
        provider = cls.create_provider(provider_name, config)
        if provider:
            return provider.get_capabilities()
        return None
    
    @classmethod
    def get_all_capabilities(cls, config: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get capabilities of all available providers
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Dictionary mapping provider names to their capabilities
        """
        capabilities = {}
        
        for provider_name in cls.AVAILABLE_PROVIDERS.keys():
            provider_caps = cls.get_provider_capabilities(provider_name, config)
            if provider_caps:
                capabilities[provider_name] = provider_caps
        
        return capabilities
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """
        Register a new provider class
        
        Args:
            name: Name for the provider
            provider_class: Provider class that implements AIProvider
        """
        if not issubclass(provider_class, AIProvider):
            raise ValueError(f"Provider class must inherit from AIProvider")
        
        cls.AVAILABLE_PROVIDERS[name.lower()] = provider_class
        logging.info(f"Registered new AI provider: {name}")
    
    @classmethod
    def get_available_provider_names(cls) -> List[str]:
        """
        Get list of available provider names
        
        Returns:
            List of provider names
        """
        return list(cls.AVAILABLE_PROVIDERS.keys())
    
    @classmethod
    def is_provider_available(cls, provider_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if a specific provider is available and can be initialized
        
        Args:
            provider_name: Name of the provider
            config: Configuration dictionary
            
        Returns:
            True if provider is available, False otherwise
        """
        provider = cls.create_provider(provider_name, config)
        return provider is not None and provider.is_available()