"""
Debug Logger Utility
Provides comprehensive logging for API calls and tool executions.
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
import time

# Set up logging
logger = logging.getLogger(__name__)

# Global storage for debug data (in-memory for session)
debug_data = {
    "api_calls": [],
    "tool_executions": [],
    "session_start": datetime.now().isoformat()
}


def log_api_call(
    service: str,
    endpoint: str,
    method: str,
    request_data: Dict[str, Any],
    response_data: Dict[str, Any],
    response_time_ms: float,
    status: str,
    error: Optional[str] = None
):
    """
    Log an API call for debugging purposes.
    
    Args:
        service: Service name (azure, gemini, etc.)
        endpoint: API endpoint called
        method: HTTP method (GET, POST, etc.)
        request_data: Request data sent
        response_data: Response data received
        response_time_ms: Response time in milliseconds
        status: Call status (success, error, partial)
        error: Error message if any
    """
    call_data = {
        "timestamp": datetime.now().isoformat(),
        "service": service,
        "endpoint": endpoint,
        "method": method,
        "request_data": _sanitize_data(request_data),
        "response_data": _sanitize_data(response_data),
        "response_time_ms": response_time_ms,
        "status": status,
        "error": error
    }
    
    debug_data["api_calls"].append(call_data)
    
    # Log to console for immediate visibility
    if status == "error":
        logger.error(f"{service.upper()} API Call Failed: {endpoint} - {error}")
    else:
        logger.info(f"{service.upper()} API Call: {endpoint} - {status} ({response_time_ms:.1f}ms)")


def log_tool_execution(
    tool_name: str,
    parameters: Dict[str, Any],
    result: Dict[str, Any],
    execution_time_ms: float,
    status: str,
    error: Optional[str] = None
):
    """
    Log a tool execution for debugging purposes.
    
    Args:
        tool_name: Name of the tool executed
        parameters: Parameters passed to the tool
        result: Result data from tool execution
        execution_time_ms: Execution time in milliseconds
        status: Execution status (success, error, partial)
        error: Error message if any
    """
    execution_data = {
        "timestamp": datetime.now().isoformat(),
        "tool_name": tool_name,
        "parameters": _sanitize_data(parameters),
        "result": _sanitize_data(result),
        "execution_time_ms": execution_time_ms,
        "status": status,
        "error": error
    }
    
    debug_data["tool_executions"].append(execution_data)
    
    # Log to console for immediate visibility
    if status == "error":
        logger.error(f"Tool Execution Failed: {tool_name} - {error}")
    else:
        logger.info(f"Tool Execution: {tool_name} - {status} ({execution_time_ms:.1f}ms)")


def get_debug_data() -> Dict[str, Any]:
    """Get all debug data for export."""
    return {
        **debug_data,
        "session_duration": _calculate_session_duration(),
        "total_api_calls": len(debug_data["api_calls"]),
        "total_tool_executions": len(debug_data["tool_executions"]),
        "api_success_rate": _calculate_api_success_rate(),
        "tool_success_rate": _calculate_tool_success_rate()
    }


def clear_debug_data():
    """Clear all debug data."""
    debug_data["api_calls"].clear()
    debug_data["tool_executions"].clear()
    debug_data["session_start"] = datetime.now().isoformat()
    logger.info("Debug data cleared")


def get_api_calls_summary() -> Dict[str, Any]:
    """Get summary of API calls."""
    calls = debug_data["api_calls"]
    
    if not calls:
        return {"message": "No API calls recorded yet"}
    
    services = {}
    total_time = 0
    success_count = 0
    
    for call in calls:
        service = call["service"]
        if service not in services:
            services[service] = {"count": 0, "success": 0, "total_time": 0}
        
        services[service]["count"] += 1
        services[service]["total_time"] += call["response_time_ms"]
        
        if call["status"] == "success":
            services[service]["success"] += 1
            success_count += 1
        
        total_time += call["response_time_ms"]
    
    return {
        "total_calls": len(calls),
        "success_count": success_count,
        "success_rate": (success_count / len(calls)) * 100,
        "total_time_ms": total_time,
        "average_time_ms": total_time / len(calls),
        "services": services
    }


def get_tool_executions_summary() -> Dict[str, Any]:
    """Get summary of tool executions."""
    executions = debug_data["tool_executions"]
    
    if not executions:
        return {"message": "No tool executions recorded yet"}
    
    tools = {}
    total_time = 0
    success_count = 0
    
    for execution in executions:
        tool = execution["tool_name"]
        if tool not in tools:
            tools[tool] = {"count": 0, "success": 0, "total_time": 0}
        
        tools[tool]["count"] += 1
        tools[tool]["total_time"] += execution["execution_time_ms"]
        
        if execution["status"] == "success":
            tools[tool]["success"] += 1
            success_count += 1
        
        total_time += execution["execution_time_ms"]
    
    return {
        "total_executions": len(executions),
        "success_count": success_count,
        "success_rate": (success_count / len(executions)) * 100,
        "total_time_ms": total_time,
        "average_time_ms": total_time / len(executions),
        "tools": tools
    }


def _sanitize_data(data: Any) -> Any:
    """
    Sanitize data for logging, removing sensitive information.
    
    Args:
        data: Data to sanitize
        
    Returns:
        Sanitized data
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in ['key', 'token', 'password', 'secret']):
                sanitized[key] = "***REDACTED***"
            elif key.lower() in ['content', 'data'] and isinstance(value, (str, bytes)) and len(str(value)) > 1000:
                # Truncate large content
                sanitized[key] = f"[TRUNCATED - Length: {len(str(value))} characters]"
            else:
                sanitized[key] = _sanitize_data(value)
        return sanitized
    elif isinstance(data, list):
        return [_sanitize_data(item) for item in data]
    elif isinstance(data, (str, bytes)) and len(str(data)) > 5000:
        # Truncate very large strings
        return f"[TRUNCATED - Length: {len(str(data))} characters]"
    else:
        return data


def _calculate_session_duration() -> str:
    """Calculate session duration."""
    try:
        start_time = datetime.fromisoformat(debug_data["session_start"])
        duration = datetime.now() - start_time
        return str(duration)
    except:
        return "Unknown"


def _calculate_api_success_rate() -> float:
    """Calculate API call success rate."""
    calls = debug_data["api_calls"]
    if not calls:
        return 0.0
    
    success_count = sum(1 for call in calls if call["status"] == "success")
    return (success_count / len(calls)) * 100


def _calculate_tool_success_rate() -> float:
    """Calculate tool execution success rate."""
    executions = debug_data["tool_executions"]
    if not executions:
        return 0.0
    
    success_count = sum(1 for execution in executions if execution["status"] == "success")
    return (success_count / len(executions)) * 100


def export_debug_session() -> str:
    """Export current debug session as JSON string."""
    return json.dumps(get_debug_data(), indent=2, default=str)
