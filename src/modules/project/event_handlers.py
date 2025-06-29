"""
Event Handlers for CPA WorkflowPilot
Handles event logic like notifications, logging, and real-time updates.
"""

from abc import ABC, abstractmethod
from events.base import EventHandler, BaseEvent
from events.schemas import TaskCreatedEvent, TaskUpdatedEvent


class LoggingHandler(EventHandler):
    """Handler for logging events to a file or external service"""

    def can_handle(self, event: BaseEvent) -> bool:
        # Handle all events
        return True

    async def handle(self, event: BaseEvent) -> bool:
        try:
            # Log the event type for now
            print(f"[LoggingHandler] Event received: {event.event_type}")
            return True
        except Exception as e:
            print(f"Error in LoggingHandler: {e}")
            return False


class NotificationHandler(EventHandler):
    """Handler for sending notifications based on events"""

    def can_handle(self, event: BaseEvent) -> bool:
        # Handle task-related events
        return isinstance(event, (TaskCreatedEvent, TaskUpdatedEvent))

    async def handle(self, event: BaseEvent) -> bool:
        try:
            # Send a notification for demonstration purposes
            print(f"[NotificationHandler] Sending notification for {event.event_type}")
            return True
        except Exception as e:
            print(f"Error in NotificationHandler: {e}")
            return False

