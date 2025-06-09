"""
CPA Copilot Agents Module
Contains AI agents for tax document analysis and assistance.
"""

from .base_agent import BaseAgent, BaseTool, ToolRegistry, ConversationMemory, AgentResponse, ToolResult, ToolResultStatus, ToolSchema
from .tax_document_analyst_agent import TaxDocumentAnalystAgent
from .tax_document_tools import (
    DocumentInquiryTool,
    IncomeAggregatorTool,
    DocumentComparisonTool,
    ValidationReviewTool,
    MissingDataFinderTool
)
from .workflow_tools import (
    DocumentUploadTool,
    DocumentProcessingTool,
    WorkpaperGenerationTool
)

__all__ = [
    'BaseAgent',
    'BaseTool', 
    'ToolRegistry',
    'ConversationMemory',
    'AgentResponse',
    'ToolResult',
    'ToolResultStatus',
    'ToolSchema',
    'TaxDocumentAnalystAgent',
    'DocumentInquiryTool',
    'IncomeAggregatorTool',
    'DocumentComparisonTool',
    'ValidationReviewTool',
    'MissingDataFinderTool',
    'DocumentUploadTool',
    'DocumentProcessingTool',
    'WorkpaperGenerationTool'
]
