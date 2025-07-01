"""
Auto-Discovery Event Registry for CPA WorkflowPilot
Simple decorator-based event handler registration that eliminates manual registry maintenance.
"""

from typing import Dict, List, Callable, Type, Any
from dataclasses import dataclass
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class HandlerInfo:
    """Information about a registered handler"""
    handler_func: Callable
    handler_name: str
    priority: int = 0
    is_async: bool = True
    is_critical: bool = False


class AutoEventRegistry:
    """
    Simplified event registry using decorator-based auto-discovery.
    Eliminates the need for manual event flow registration.
    """
    
    def __init__(self):
        # Event class name -> List of handler info
        self._handlers: Dict[str, List[HandlerInfo]] = defaultdict(list)
        self._handler_count = 0
    
    def register_handler_for(self, event_class: Type, priority: int = 0, 
                           is_async: bool = True, is_critical: bool = False):
        """
        Decorator to register a handler for a specific event type
        
        Args:
            event_class: The event class this handler processes
            priority: Handler priority (higher = runs first)
            is_async: Whether the handler is async
            is_critical: Whether this handler must succeed
        
        Usage:
            @auto_registry.register_handler_for(TaskCreatedEvent, priority=10)
            def handle_task_creation_notification(event: TaskCreatedEvent):
                # Handler logic here
                pass
        """
        def decorator(handler_func: Callable):
            event_name = event_class.__name__
            handler_info = HandlerInfo(
                handler_func=handler_func,
                handler_name=handler_func.__name__,
                priority=priority,
                is_async=is_async,
                is_critical=is_critical
            )
            
            self._handlers[event_name].append(handler_info)
            # Sort by priority (highest first)
            self._handlers[event_name].sort(key=lambda x: x.priority, reverse=True)
            
            self._handler_count += 1
            logger.info(f"Auto-registered handler '{handler_func.__name__}' for event '{event_name}'")
            return handler_func
        
        return decorator
    
    def get_handlers_for_event(self, event_name: str) -> List[HandlerInfo]:
        """Get all handlers for a specific event type"""
        return self._handlers.get(event_name, [])
    
    def get_all_event_types(self) -> List[str]:
        """Get list of all registered event types"""
        return list(self._handlers.keys())
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get statistics about the registry"""
        return {
            'total_events': len(self._handlers),
            'total_handlers': self._handler_count,
            'events': {
                event_name: {
                    'handler_count': len(handlers),
                    'handlers': [
                        {
                            'name': h.handler_name,
                            'priority': h.priority,
                            'is_critical': h.is_critical,
                            'is_async': h.is_async
                        }
                        for h in handlers
                    ]
                }
                for event_name, handlers in self._handlers.items()
            }
        }
    
    def validate_registry(self) -> Dict[str, List[str]]:
        """Validate the registry for common issues"""
        issues = {
            'events_without_handlers': [],
            'multiple_critical_handlers': [],
            'handler_name_conflicts': []
        }
        
        for event_name, handlers in self._handlers.items():
            if not handlers:
                issues['events_without_handlers'].append(event_name)
            
            # Check for multiple critical handlers
            critical_count = sum(1 for h in handlers if h.is_critical)
            if critical_count > 1:
                issues['multiple_critical_handlers'].append(event_name)
            
            # Check for handler name conflicts within the same event
            handler_names = [h.handler_name for h in handlers]
            if len(handler_names) != len(set(handler_names)):
                issues['handler_name_conflicts'].append(event_name)
        
        return issues
    
    def clear_registry(self):
        """Clear all registered handlers (useful for testing)"""
        self._handlers.clear()
        self._handler_count = 0
        logger.info("Event registry cleared")


# Global auto-discovery registry instance
auto_registry = AutoEventRegistry()


def register_handler_for(event_class: Type, priority: int = 0, 
                        is_async: bool = True, is_critical: bool = False):
    """
    Global decorator function for registering event handlers
    
    Usage:
        from events.auto_registry import register_handler_for
        from events.schemas import TaskCreatedEvent
        
        @register_handler_for(TaskCreatedEvent, priority=10, is_critical=True)
        def handle_task_creation_notification(event: TaskCreatedEvent):
            # Send notification logic
            pass
    """
    return auto_registry.register_handler_for(event_class, priority, is_async, is_critical)


def get_registry() -> AutoEventRegistry:
    """Get the global auto-discovery registry instance"""
    return auto_registry


def print_registry_documentation():
    """Print auto-discovered event documentation"""
    stats = auto_registry.get_registry_stats()
    
    print("=" * 60)
    print("AUTO-DISCOVERED EVENT HANDLERS")
    print("=" * 60)
    print(f"Total Events: {stats['total_events']}")
    print(f"Total Handlers: {stats['total_handlers']}")
    print()
    
    for event_name, event_info in stats['events'].items():
        print(f"EVENT: {event_name}")
        print(f"  Handlers: {event_info['handler_count']}")
        
        for handler in event_info['handlers']:
            critical = " [CRITICAL]" if handler['is_critical'] else ""
            async_note = " [ASYNC]" if handler['is_async'] else " [SYNC]"
            print(f"    - {handler['name']} (Priority: {handler['priority']}){critical}{async_note}")
        print()
    
    # Show validation issues
    issues = auto_registry.validate_registry()
    if any(issues.values()):
        print("VALIDATION ISSUES:")
        for category, items in issues.items():
            if items:
                print(f"  {category.replace('_', ' ').title()}: {', '.join(items)}")
    else:
        print("✅ All handlers validated successfully")
    
    print("=" * 60)


# Example usage (for documentation)
if __name__ == "__main__":
    # Example of how handlers would be registered
    
    class ExampleEvent:
        pass
    
    @register_handler_for(ExampleEvent, priority=10, is_critical=True)
    def handle_example_critical(event):
        """Critical handler for example event"""
        pass
    
    @register_handler_for(ExampleEvent, priority=5)
    def handle_example_normal(event):
        """Normal handler for example event"""
        pass
    
    print_registry_documentation()
