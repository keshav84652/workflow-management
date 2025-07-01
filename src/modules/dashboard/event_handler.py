"""
Dashboard Event Handler for CPA WorkflowPilot
Handles events that should trigger dashboard updates.
"""

from datetime import datetime
from typing import Dict, Any
from src.shared.events.base import EventHandler, BaseEvent
from src.shared.events.schemas import (
    TaskCreatedEvent, TaskUpdatedEvent, TaskStatusChangedEvent,
    TaskDeletedEvent, TaskAssignedEvent
)
from src.shared.database.redis_client import redis_client


class DashboardEventHandler(EventHandler):
    """Handler for dashboard real-time updates"""

    def can_handle(self, event: BaseEvent) -> bool:
        """Check if this handler can process the event"""
        return isinstance(event, (
            TaskCreatedEvent,
            TaskUpdatedEvent,
            TaskStatusChangedEvent,
            TaskDeletedEvent,
            TaskAssignedEvent
        ))

    async def handle(self, event: BaseEvent) -> bool:
        """Process event and update dashboard data"""
        try:
            if not redis_client or not redis_client.is_available():
                print("Redis not available for dashboard updates")
                return False

            # Get firm and user context
            firm_id = event.firm_id
            if not firm_id:
                return False

            # Create dashboard update based on event type
            update = self._create_dashboard_update(event)
            if not update:
                return False

            # Store update in Redis for dashboard to consume
            self._store_dashboard_update(firm_id, update)

            # Notify any connected dashboard clients
            self._notify_dashboard_clients(firm_id, update)

            return True

        except Exception as e:
            print(f"Error in DashboardEventHandler: {e}")
            return False

    def _create_dashboard_update(self, event: BaseEvent) -> Dict[str, Any]:
        """Create dashboard update data based on event type"""
        base_update = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event.event_type,
            'firm_id': event.firm_id
        }

        if isinstance(event, TaskCreatedEvent):
            return {
                **base_update,
                'update_type': 'task_created',
                'task_id': event.task_id,
                'task_title': event.task_title,
                'priority': event.priority,
                'project_id': event.project_id,
                'assigned_to': event.assigned_to
            }

        elif isinstance(event, TaskStatusChangedEvent):
            return {
                **base_update,
                'update_type': 'task_status_changed',
                'task_id': event.task_id,
                'task_title': event.task_title,
                'old_status': event.old_status,
                'new_status': event.new_status
            }

        elif isinstance(event, TaskDeletedEvent):
            return {
                **base_update,
                'update_type': 'task_deleted',
                'task_id': event.task_id,
                'task_title': event.task_title,
                'project_id': event.project_id
            }

        elif isinstance(event, TaskAssignedEvent):
            return {
                **base_update,
                'update_type': 'task_assigned',
                'task_id': event.task_id,
                'task_title': event.task_title,
                'assigned_to': event.assigned_to,
                'assigned_by': event.assigned_by
            }

        return None

    def _store_dashboard_update(self, firm_id: int, update: Dict[str, Any]) -> None:
        """Store dashboard update in Redis"""
        if not redis_client or not redis_client.is_available():
            return

        # Store update in Redis list for dashboard history
        key = f"dashboard:updates:{firm_id}"
        redis_client.rpush(key, update)

        # Trim list to keep only recent updates
        redis_client.ltrim(key, -100, -1)  # Keep last 100 updates

    def _notify_dashboard_clients(self, firm_id: int, update: Dict[str, Any]) -> None:
        """Notify connected dashboard clients of update"""
        if not redis_client or not redis_client.is_available():
            return

        # Publish update to Redis channel for real-time notifications
        channel = f"dashboard:notifications:{firm_id}"
        redis_client.publish(channel, update)
