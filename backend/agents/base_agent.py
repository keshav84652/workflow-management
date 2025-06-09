"""
Base Agent Framework for CPA Copilot
Provides foundation for building intelligent agents.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import json
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class ToolResultStatus(Enum):
    """Status of tool execution"""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


@dataclass
class ToolResult:
    """Result from tool execution"""
    status: ToolResultStatus
    data: Any
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ToolSchema:
    """Schema definition for a tool"""
    name: str
    description: str
    parameters: Dict[str, Any]
    returns: Dict[str, Any]
    examples: Optional[List[Dict[str, Any]]] = None


class BaseTool(ABC):
    """Base class for all agent tools"""
    
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Execute the tool with given parameters"""
        pass
    
    @abstractmethod
    def get_schema(self) -> ToolSchema:
        """Get tool schema for LLM understanding"""
        pass
    
    def validate_params(self, params: Dict[str, Any]) -> Optional[str]:
        """Validate parameters against schema"""
        schema = self.get_schema()
        required = schema.parameters.get("required", [])
        
        for req in required:
            if req not in params:
                return f"Missing required parameter: {req}"
        
        return None


class ToolRegistry:
    """Registry for managing available tools"""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool):
        """Register a tool"""
        schema = tool.get_schema()
        self._tools[schema.name] = tool
        logger.info(f"Registered tool: {schema.name}")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get tool by name"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List all available tool names"""
        return list(self._tools.keys())
    
    def get_schemas(self) -> List[ToolSchema]:
        """Get all tool schemas"""
        return [tool.get_schema() for tool in self._tools.values()]
    
    def get_schemas_for_llm(self) -> List[Dict[str, Any]]:
        """Get tool schemas formatted for LLM"""
        schemas = []
        for tool in self._tools.values():
            schema = tool.get_schema()
            schemas.append({
                "name": schema.name,
                "description": schema.description,
                "parameters": schema.parameters
            })
        return schemas


@dataclass
class AgentResponse:
    """Response from agent processing"""
    message: str
    tool_results: Optional[List[ToolResult]] = None
    suggested_actions: Optional[List[str]] = None
    confidence: float = 1.0
    metadata: Optional[Dict[str, Any]] = None


class ConversationMemory:
    """Manages conversation history and context"""
    
    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages
        self.messages: List[Dict[str, Any]] = []
        self.context: Dict[str, Any] = {}
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to history"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.messages.append(message)
        
        # Trim history if needed
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def get_context(self, include_system: bool = True) -> List[Dict[str, str]]:
        """Get conversation context for LLM"""
        context = []
        
        if include_system:
            context.append({
                "role": "system",
                "content": self._get_system_prompt()
            })
        
        # Add conversation history
        for msg in self.messages:
            context.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return context
    
    def update_context(self, key: str, value: Any):
        """Update persistent context"""
        self.context[key] = value
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for the agent"""
        return """You are a helpful AI assistant."""


class BaseAgent(ABC):
    """Base class for all agents"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.tool_registry = ToolRegistry()
        self.conversation_memory = ConversationMemory()
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    async def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Process a user message and return response"""
        pass
    
    def register_tool(self, tool: BaseTool):
        """Register a tool with this agent"""
        self.tool_registry.register(tool)
    
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> ToolResult:
        """Execute a tool by name"""
        from ..utils.debug_logger import log_tool_execution
        import time
        
        start_time = time.time()
        tool = self.tool_registry.get_tool(tool_name)
        
        if not tool:
            result = ToolResult(
                status=ToolResultStatus.ERROR,
                data=None,
                error=f"Unknown tool: {tool_name}"
            )
            
            # Log tool execution error
            log_tool_execution(
                tool_name=tool_name,
                parameters=params,
                result={"error": "tool_not_found"},
                execution_time_ms=(time.time() - start_time) * 1000,
                status="error",
                error=f"Unknown tool: {tool_name}"
            )
            
            return result
        
        # Validate parameters
        error = tool.validate_params(params)
        if error:
            result = ToolResult(
                status=ToolResultStatus.ERROR,
                data=None,
                error=error
            )
            
            # Log validation error
            log_tool_execution(
                tool_name=tool_name,
                parameters=params,
                result={"error": "validation_failed"},
                execution_time_ms=(time.time() - start_time) * 1000,
                status="error",
                error=error
            )
            
            return result
        
        try:
            result = await tool.execute(params)
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Log successful tool execution
            log_tool_execution(
                tool_name=tool_name,
                parameters=params,
                result=result.data if result.data else {},
                execution_time_ms=execution_time_ms,
                status=result.status.value,
                error=result.error
            )
            
            return result
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            
            self.logger.error(f"Tool execution error: {str(e)}", exc_info=True)
            
            result = ToolResult(
                status=ToolResultStatus.ERROR,
                data=None,
                error=str(e)
            )
            
            # Log tool execution error
            log_tool_execution(
                tool_name=tool_name,
                parameters=params,
                result={},
                execution_time_ms=execution_time_ms,
                status="error",
                error=str(e)
            )
            
            return result
    
    def add_to_memory(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add to conversation memory"""
        self.conversation_memory.add_message(role, content, metadata)
