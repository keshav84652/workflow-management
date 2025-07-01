"""
Explicit Event Schema Registry for CPA WorkflowPilot
This module provides a central registry that explicitly maps event types to their handlers,
solving the "Implicit Event-Driven Complexity" identified in the architectural review.
"""

from typing import Dict, List, Type, Callable, Any, Optional
from dataclasses import dataclass
import logging

from events.base import BaseEvent, EventHandler


@dataclass
class EventHandlerRegistration:
    """Registration information for an event handler"""
    handler_class: Type[EventHandler]
    handler_name: str
    description: str
    priority: int = 0  # Higher numbers = higher priority
    is_async: bool = True
    is_critical: bool = False  # Critical handlers must succeed


@dataclass
class EventFlowDocumentation:
    """Documentation for event flow and handling"""
    event_type: str
    event_description: str
    handlers: List[EventHandlerRegistration]
    triggers: List[str]  # What actions trigger this event
    side_effects: List[str]  # What happens when this event is processed
    dependencies: List[str] = None  # Other events this depends on
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class EventSchemaRegistry:
    """
    Central registry for event types and their handlers.
    
    This registry provides:
    1. Explicit mapping of events to handlers
    2. Documentation of event flows
    3. Dependency tracking
    4. Handler priority management
    5. Event flow visualization support
    """
    
    def __init__(self):
        # Event type -> List of handler registrations
        self._event_handlers: Dict[str, List[EventHandlerRegistration]] = {}
        
        # Event type -> Flow documentation
        self._event_flows: Dict[str, EventFlowDocumentation] = {}
        
        # Handler name -> Handler instances (for performance)
        self._handler_instances: Dict[str, EventHandler] = {}
        
        # Event dependency graph
        self._dependency_graph: Dict[str, List[str]] = {}
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize with known event flows
        self._register_known_event_flows()
    
    def register_event_flow(self, flow: EventFlowDocumentation):
        """
        Register an event flow with its handlers
        
        Args:
            flow: Event flow documentation
        """
        self._event_flows[flow.event_type] = flow
        self._event_handlers[flow.event_type] = flow.handlers.copy()
        
        # Update dependency graph
        if flow.dependencies:
            self._dependency_graph[flow.event_type] = flow.dependencies
        
        self.logger.info(f"Registered event flow: {flow.event_type} with {len(flow.handlers)} handlers")
    
    def register_handler(self, event_type: str, handler_registration: EventHandlerRegistration):
        """
        Register a handler for a specific event type
        
        Args:
            event_type: Type of event to handle
            handler_registration: Handler registration information
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        
        self._event_handlers[event_type].append(handler_registration)
        
        # Sort by priority (highest first)
        self._event_handlers[event_type].sort(key=lambda x: x.priority, reverse=True)
        
        self.logger.info(f"Registered handler {handler_registration.handler_name} for event {event_type}")
    
    def get_handlers_for_event(self, event_type: str) -> List[EventHandlerRegistration]:
        """Get all handlers for a specific event type"""
        return self._event_handlers.get(event_type, [])
    
    def get_event_flow(self, event_type: str) -> Optional[EventFlowDocumentation]:
        """Get event flow documentation for a specific event type"""
        return self._event_flows.get(event_type)
    
    def get_all_event_types(self) -> List[str]:
        """Get list of all registered event types"""
        return list(self._event_flows.keys())
    
    def get_event_dependencies(self, event_type: str) -> List[str]:
        """Get dependencies for a specific event type"""
        return self._dependency_graph.get(event_type, [])
    
    def get_event_dependency_chain(self, event_type: str, visited: set = None) -> List[str]:
        """
        Get the complete dependency chain for an event type
        
        Args:
            event_type: Event type to analyze
            visited: Set of already visited events (for cycle detection)
            
        Returns:
            List of event types in dependency order
        """
        if visited is None:
            visited = set()
        
        if event_type in visited:
            # Circular dependency detected
            self.logger.warning(f"Circular dependency detected for event {event_type}")
            return []
        
        visited.add(event_type)
        chain = []
        
        dependencies = self.get_event_dependencies(event_type)
        for dep in dependencies:
            sub_chain = self.get_event_dependency_chain(dep, visited.copy())
            chain.extend(sub_chain)
        
        chain.append(event_type)
        return chain
    
    def generate_event_flow_documentation(self) -> Dict[str, Any]:
        """
        Generate comprehensive documentation of all event flows
        
        Returns:
            Dictionary containing complete event flow documentation
        """
        docs = {
            'total_events': len(self._event_flows),
            'total_handlers': sum(len(handlers) for handlers in self._event_handlers.values()),
            'event_flows': {},
            'dependency_graph': self._dependency_graph.copy(),
            'handler_coverage': {},
            'critical_events': []
        }
        
        for event_type, flow in self._event_flows.items():
            # Basic flow information
            flow_doc = {
                'description': flow.event_description,
                'triggers': flow.triggers,
                'side_effects': flow.side_effects,
                'dependencies': flow.dependencies,
                'handlers': []
            }
            
            # Handler information
            for handler in flow.handlers:
                handler_doc = {
                    'name': handler.handler_name,
                    'description': handler.description,
                    'priority': handler.priority,
                    'is_async': handler.is_async,
                    'is_critical': handler.is_critical
                }
                flow_doc['handlers'].append(handler_doc)
                
                if handler.is_critical:
                    if event_type not in docs['critical_events']:
                        docs['critical_events'].append(event_type)
            
            docs['event_flows'][event_type] = flow_doc
            docs['handler_coverage'][event_type] = len(flow.handlers)
        
        return docs
    
    def validate_event_flows(self) -> Dict[str, List[str]]:
        """
        Validate all registered event flows for consistency
        
        Returns:
            Dictionary of validation issues by category
        """
        issues = {
            'missing_handlers': [],
            'circular_dependencies': [],
            'orphaned_dependencies': [],
            'duplicate_handlers': [],
            'critical_handler_conflicts': []
        }
        
        # Check for events without handlers
        for event_type in self._event_flows:
            if not self._event_handlers.get(event_type):
                issues['missing_handlers'].append(event_type)
        
        # Check for circular dependencies
        for event_type in self._event_flows:
            try:
                chain = self.get_event_dependency_chain(event_type)
                if len(set(chain)) != len(chain):
                    issues['circular_dependencies'].append(event_type)
            except:
                issues['circular_dependencies'].append(event_type)
        
        # Check for orphaned dependencies
        all_events = set(self._event_flows.keys())
        for event_type, deps in self._dependency_graph.items():
            for dep in deps:
                if dep not in all_events:
                    issues['orphaned_dependencies'].append(f"{event_type} -> {dep}")
        
        # Check for duplicate handler names within event types
        for event_type, handlers in self._event_handlers.items():
            handler_names = [h.handler_name for h in handlers]
            if len(handler_names) != len(set(handler_names)):
                issues['duplicate_handlers'].append(event_type)
        
        # Check for multiple critical handlers (potential conflict)
        for event_type, handlers in self._event_handlers.items():
            critical_count = sum(1 for h in handlers if h.is_critical)
            if critical_count > 1:
                issues['critical_handler_conflicts'].append(event_type)
        
        return issues
    
    def _register_known_event_flows(self):
        """Register all known event flows in the system"""
        
        # Client Events
        self.register_event_flow(EventFlowDocumentation(
            event_type="ClientCreatedEvent",
            event_description="Fired when a new client is created in the system",
            triggers=["Client registration form submission", "API client creation", "Data import"],
            side_effects=["Dashboard metrics update", "Notification to admin", "Audit log entry"],
            handlers=[
                EventHandlerRegistration(
                    handler_class=None,  # Would be actual handler class
                    handler_name="DashboardUpdateHandler",
                    description="Updates dashboard client count and metrics",
                    priority=10
                ),
                EventHandlerRegistration(
                    handler_class=None,
                    handler_name="NotificationHandler", 
                    description="Sends notification to system administrators",
                    priority=5
                ),
                EventHandlerRegistration(
                    handler_class=None,
                    handler_name="AuditLogHandler",
                    description="Records client creation in audit log",
                    priority=1,
                    is_critical=True
                )
            ]
        ))
        
        # Task Events
        self.register_event_flow(EventFlowDocumentation(
            event_type="TaskCreatedEvent",
            event_description="Fired when a new task is created",
            triggers=["Manual task creation", "Project template instantiation", "API task creation"],
            side_effects=["Project progress update", "Assignee notification", "Dashboard refresh"],
            dependencies=["ProjectCreatedEvent"],
            handlers=[
                EventHandlerRegistration(
                    handler_class=None,
                    handler_name="ProjectProgressHandler",
                    description="Updates project progress calculations",
                    priority=10,
                    is_critical=True
                ),
                EventHandlerRegistration(
                    handler_class=None,
                    handler_name="AssigneeNotificationHandler",
                    description="Notifies assigned user of new task",
                    priority=8
                ),
                EventHandlerRegistration(
                    handler_class=None,
                    handler_name="DashboardAnalyticsHandler",
                    description="Updates task analytics for dashboard",
                    priority=5
                )
            ]
        ))
        
        self.register_event_flow(EventFlowDocumentation(
            event_type="TaskStatusChangedEvent",
            event_description="Fired when a task status changes",
            triggers=["Manual status update", "Workflow automation", "API status change"],
            side_effects=["Project progress recalculation", "Timeline updates", "Notification triggers"],
            dependencies=["TaskCreatedEvent"],
            handlers=[
                EventHandlerRegistration(
                    handler_class=None,
                    handler_name="ProjectProgressRecalculator",
                    description="Recalculates project completion percentage",
                    priority=10,
                    is_critical=True
                ),
                EventHandlerRegistration(
                    handler_class=None,
                    handler_name="TimelineUpdateHandler",
                    description="Updates project timeline and dependencies",
                    priority=8
                ),
                EventHandlerRegistration(
                    handler_class=None,
                    handler_name="StatusNotificationHandler",
                    description="Sends status change notifications",
                    priority=5
                )
            ]
        ))
        
        # Document Events
        self.register_event_flow(EventFlowDocumentation(
            event_type="DocumentAnalysisStartedEvent",
            event_description="Fired when AI document analysis begins",
            triggers=["Document upload", "Manual analysis trigger", "Batch processing"],
            side_effects=["Progress tracking update", "Resource allocation", "Status notification"],
            handlers=[
                EventHandlerRegistration(
                    handler_class=None,
                    handler_name="AnalysisProgressTracker",
                    description="Tracks analysis progress and ETA",
                    priority=10
                ),
                EventHandlerRegistration(
                    handler_class=None,
                    handler_name="ResourceAllocationHandler",
                    description="Allocates AI provider resources",
                    priority=8,
                    is_critical=True
                )
            ]
        ))
        
        self.register_event_flow(EventFlowDocumentation(
            event_type="DocumentAnalysisCompletedEvent",
            event_description="Fired when AI document analysis completes successfully",
            triggers=["AI provider completion", "Manual completion", "Batch completion"],
            side_effects=["Checklist updates", "Quality metrics update", "User notification"],
            dependencies=["DocumentAnalysisStartedEvent"],
            handlers=[
                EventHandlerRegistration(
                    handler_class=None,
                    handler_name="ChecklistUpdateHandler",
                    description="Updates document checklists with extracted data",
                    priority=10,
                    is_critical=True
                ),
                EventHandlerRegistration(
                    handler_class=None,
                    handler_name="QualityMetricsHandler",
                    description="Updates AI accuracy and confidence metrics",
                    priority=8
                ),
                EventHandlerRegistration(
                    handler_class=None,
                    handler_name="CompletionNotificationHandler",
                    description="Notifies user of analysis completion",
                    priority=5
                )
            ]
        ))
        
        # Project Events
        self.register_event_flow(EventFlowDocumentation(
            event_type="ProjectCreatedEvent",
            event_description="Fired when a new project is created",
            triggers=["Manual project creation", "Template instantiation", "Client onboarding"],
            side_effects=["Task generation", "Team assignment", "Dashboard update"],
            dependencies=["ClientCreatedEvent"],
            handlers=[
                EventHandlerRegistration(
                    handler_class=None,
                    handler_name="TaskGenerationHandler",
                    description="Generates tasks from project template",
                    priority=10,
                    is_critical=True
                ),
                EventHandlerRegistration(
                    handler_class=None,
                    handler_name="TeamAssignmentHandler",
                    description="Assigns team members to project",
                    priority=8
                ),
                EventHandlerRegistration(
                    handler_class=None,
                    handler_name="ProjectAnalyticsHandler",
                    description="Updates project analytics and metrics",
                    priority=5
                )
            ]
        ))
        
        # Error Events
        self.register_event_flow(EventFlowDocumentation(
            event_type="ErrorEvent",
            event_description="Generic error event for system errors",
            triggers=["System exceptions", "Validation failures", "External service errors"],
            side_effects=["Error logging", "Admin notification", "Recovery actions"],
            handlers=[
                EventHandlerRegistration(
                    handler_class=None,
                    handler_name="ErrorLogHandler",
                    description="Logs errors to system log",
                    priority=10,
                    is_critical=True
                ),
                EventHandlerRegistration(
                    handler_class=None,
                    handler_name="AdminNotificationHandler",
                    description="Notifies administrators of critical errors",
                    priority=8
                ),
                EventHandlerRegistration(
                    handler_class=None,
                    handler_name="RecoveryHandler",
                    description="Attempts automatic error recovery",
                    priority=5
                )
            ]
        ))


# Global registry instance
event_schema_registry = EventSchemaRegistry()


def get_event_registry() -> EventSchemaRegistry:
    """Get the global event schema registry instance"""
    return event_schema_registry


def register_event_flow(flow: EventFlowDocumentation):
    """
    Decorator function to register event flows
    
    Usage:
        @register_event_flow
        def define_my_event_flow():
            return EventFlowDocumentation(...)
    """
    def decorator(func):
        flow = func() if callable(func) else flow
        event_schema_registry.register_event_flow(flow)
        return func
    return decorator


def print_event_documentation():
    """Print comprehensive event documentation to console"""
    docs = event_schema_registry.generate_event_flow_documentation()
    
    print("=" * 80)
    print("CPA WORKFLOWPILOT - EVENT FLOW DOCUMENTATION")
    print("=" * 80)
    print(f"Total Events: {docs['total_events']}")
    print(f"Total Handlers: {docs['total_handlers']}")
    print(f"Critical Events: {', '.join(docs['critical_events'])}")
    print()
    
    for event_type, flow in docs['event_flows'].items():
        print(f"EVENT: {event_type}")
        print(f"  Description: {flow['description']}")
        print(f"  Triggers: {', '.join(flow['triggers'])}")
        print(f"  Side Effects: {', '.join(flow['side_effects'])}")
        
        if flow['dependencies']:
            print(f"  Dependencies: {', '.join(flow['dependencies'])}")
        
        print("  Handlers:")
        for handler in flow['handlers']:
            critical = " [CRITICAL]" if handler['is_critical'] else ""
            async_note = " [ASYNC]" if handler['is_async'] else " [SYNC]"
            print(f"    - {handler['name']} (Priority: {handler['priority']}){critical}{async_note}")
            print(f"      {handler['description']}")
        print()
    
    # Validation issues
    issues = event_schema_registry.validate_event_flows()
    if any(issues.values()):
        print("VALIDATION ISSUES:")
        for category, items in issues.items():
            if items:
                print(f"  {category.replace('_', ' ').title()}: {', '.join(items)}")
    else:
        print("✅ All event flows validated successfully")
    
    print("=" * 80)


if __name__ == "__main__":
    # Print documentation when run directly
    print_event_documentation()