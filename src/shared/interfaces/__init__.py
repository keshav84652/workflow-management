"""
Shared Interfaces for CPA WorkflowPilot
Service contracts and interfaces for cross-module communication.
"""

from .service_interfaces import (
    IProjectService,
    ITaskService, 
    IClientService,
    IDataAggregatorService,
    ServiceRegistry
)

__all__ = [
    'IProjectService',
    'ITaskService',
    'IClientService', 
    'IDataAggregatorService',
    'ServiceRegistry'
]