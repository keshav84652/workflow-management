"""
Configuration management for CPA Copilot application.
Centralizes all configuration settings and environment variables.
"""

import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import field_validator

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings with validation and type hints."""
    
    # Azure Document Intelligence
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: str = "https://cpa-flow.cognitiveservices.azure.com/"
    AZURE_DOCUMENT_INTELLIGENCE_KEY: str = ""  # Optional - AI features disabled if not set
    
    # Google Gemini AI
    GEMINI_API_KEY: str = ""  # Optional - AI features disabled if not set
    GEMINI_MODEL: str = "gemini-2.5-flash-preview-05-20"
    
    # Application
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # File Upload
    UPLOAD_FOLDER: str = "uploads"
    MAX_FILE_SIZE: int = 10485760  # 10MB
    ALLOWED_EXTENSIONS: str = "pdf,jpg,jpeg,png,tiff"
    MAX_BATCH_SIZE: int = 20
    
    # Processing
    ENABLE_PII_MASKING: bool = True
    PII_HANDLING_MODE: str = "mask"
    PROCESSING_TIMEOUT: int = 300
    
    # Workpaper Generation
    WORKPAPER_OUTPUT_FOLDER: str = "temp/workpapers"
    BOOKMARK_LEVELS: int = 3
    DEFAULT_PAGE_SIZE: str = "letter"
    
    # API Rate Limiting
    AZURE_RATE_LIMIT: int = 10
    GEMINI_RATE_LIMIT: int = 60
    
    # Session
    SESSION_TIMEOUT: int = 3600
    CLEANUP_INTERVAL: int = 1800
    
    # Feature Flags
    ENABLE_GEMINI_ANALYSIS: bool = True
    ENABLE_COMPARISON_VIEW: bool = True
    ENABLE_EXCEL_EXPORT: bool = True
    ENABLE_BATCH_PROCESSING: bool = True
    
    @field_validator('AZURE_DOCUMENT_INTELLIGENCE_KEY')
    @classmethod
    def validate_azure_key(cls, v: str) -> str:
        """Validate Azure Document Intelligence API key."""
        if not v or not v.strip():
            print("WARNING: AZURE_DOCUMENT_INTELLIGENCE_KEY is not set. Azure AI features will be disabled.")
            return ""
        return v.strip()
    
    @field_validator('GEMINI_API_KEY')
    @classmethod
    def validate_gemini_key(cls, v: str) -> str:
        """Validate Gemini API key."""
        if not v or not v.strip():
            print("WARNING: GEMINI_API_KEY is not set. Gemini features will be disabled.")
            return ""
        return v.strip()
    
    @field_validator('PII_HANDLING_MODE')
    @classmethod
    def validate_pii_mode(cls, v: str) -> str:
        """Validate PII handling mode."""
        valid_modes = ["ignore", "mask", "remove"]
        if v not in valid_modes:
            raise ValueError(f"PII handling mode must be one of {valid_modes}")
        return v
    
    @property
    def azure_endpoint(self) -> str:
        """Get Azure endpoint for backward compatibility."""
        return self.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
    
    @property
    def azure_key(self) -> str:
        """Get Azure key for backward compatibility."""
        return self.AZURE_DOCUMENT_INTELLIGENCE_KEY
    
    @property
    def gemini_api_key(self) -> str:
        """Get Gemini API key for backward compatibility."""
        return self.GEMINI_API_KEY
    
    @property
    def gemini_model(self) -> str:
        """Get Gemini model for backward compatibility."""
        return self.GEMINI_MODEL
    
    @property
    def upload_folder(self) -> Path:
        """Get upload folder as Path object."""
        return Path(self.UPLOAD_FOLDER)
    
    @property
    def workpaper_output_folder(self) -> Path:
        """Get workpaper output folder as Path object."""
        return Path(self.WORKPAPER_OUTPUT_FOLDER)
    
    @property
    def allowed_extensions(self) -> List[str]:
        """Get allowed extensions as list."""
        return self.ALLOWED_EXTENSIONS.split(",")
    
    @property
    def max_file_size(self) -> int:
        """Get max file size."""
        return self.MAX_FILE_SIZE
    
    @property
    def pii_handling_mode(self) -> str:
        """Get PII handling mode."""
        return self.PII_HANDLING_MODE
    
    @property
    def debug(self) -> bool:
        """Get debug mode."""
        return self.DEBUG
    
    @property
    def log_level(self) -> str:
        """Get log level."""
        return self.LOG_LEVEL
    
    def create_directories(self):
        """Create necessary directories if they don't exist."""
        directories = [
            self.upload_folder,
            self.workpaper_output_folder,
            Path("logs"),
            Path("temp"),
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def is_allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed."""
        if '.' not in filename:
            return False
        extension = filename.rsplit('.', 1)[1].lower()
        return extension in self.allowed_extensions
    
    def get_file_size_limit_mb(self) -> float:
        """Get file size limit in MB."""
        return self.max_file_size / (1024 * 1024)
    
    class Config:
        """Pydantic configuration."""
        case_sensitive = False
        env_file = ".env"

# Create global settings instance
settings = Settings()

# Create directories on initialization
settings.create_directories()

# Export settings instance and commonly used values
__all__ = ["settings"]
