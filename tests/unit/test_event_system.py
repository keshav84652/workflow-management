"""
Test cases for event system implementation
"""

import unittest
from unittest.mock import Mock, patch
from events.schemas import (
    TaskCreatedEvent, TaskUpdatedEvent, TaskDeletedEvent,
    ClientCreatedEvent, ClientUpdatedEvent,
    ProjectCreatedEvent, ProjectUpdatedEvent
)
from events.publisher import publish_event


class TestEventSchemas(unittest.TestCase):
    """Test event schema definitions"""
    
    def test_task_created_event(self):
        """Test TaskCreatedEvent schema"""
        event = TaskCreatedEvent(
            task_id=123,
            task_title="Test Task",
            priority="High",
            firm_id=456,
            user_id=789
        )
        
        self.assertEqual(event.task_id, 123)
        self.assertEqual(event.task_title, "Test Task")
        self.assertEqual(event.priority, "High")
        self.assertEqual(event.firm_id, 456)
        self.assertEqual(event.user_id, 789)
        
        # Test serialization
        event_dict = event.to_dict()
        self.assertIn('event_id', event_dict)
        self.assertIn('timestamp', event_dict)
        self.assertEqual(event_dict['event_type'], 'TaskCreatedEvent')
        self.assertEqual(event_dict['firm_id'], 456)
    
    def test_task_updated_event(self):
        """Test TaskUpdatedEvent schema"""
        changes = {'status': {'old': 'Not Started', 'new': 'In Progress'}}
        event = TaskUpdatedEvent(
            task_id=123,
            task_title="Test Task",
            changes=changes,
            firm_id=456
        )
        
        self.assertEqual(event.changes, changes)
        payload = event.get_payload()
        self.assertEqual(payload['changes'], changes)
    
    def test_client_created_event(self):
        """Test ClientCreatedEvent schema"""
        event = ClientCreatedEvent(
            client_id=123,
            firm_id=456,
            name="Test Client",
            is_active=True
        )
        
        self.assertEqual(event.client_id, 123)
        self.assertEqual(event.name, "Test Client")
        self.assertTrue(event.is_active)
        
        payload = event.get_payload()
        self.assertEqual(payload['client_id'], 123)
        self.assertEqual(payload['name'], "Test Client")
    
    def test_project_created_event(self):
        """Test ProjectCreatedEvent schema"""
        event = ProjectCreatedEvent(
            project_id=123,
            firm_id=456,
            name="Test Project",
            client_id=789,
            status="Not Started"
        )
        
        self.assertEqual(event.project_id, 123)
        self.assertEqual(event.name, "Test Project")
        self.assertEqual(event.client_id, 789)
        self.assertEqual(event.status, "Not Started")


class TestEventPublisher(unittest.TestCase):
    """Test event publishing functionality"""
    
    @patch('events.publisher.event_publisher')
    def test_publish_event(self, mock_publisher):
        """Test event publishing"""
        event = TaskCreatedEvent(
            task_id=123,
            task_title="Test Task",
            firm_id=456
        )
        
        publish_event(event)
        
        # Verify publisher was called
        mock_publisher.publish.assert_called_once_with(event)
    
    def test_event_metadata(self):
        """Test event metadata generation"""
        event = TaskCreatedEvent(
            task_id=123,
            task_title="Test Task",
            firm_id=456
        )
        
        # Check metadata fields
        self.assertIsNotNone(event.event_id)
        self.assertIsNotNone(event.timestamp)
        self.assertEqual(event.event_type, 'TaskCreatedEvent')
        self.assertEqual(event.version, '1.0')
        self.assertEqual(event.source_system, 'workflow-management')


if __name__ == '__main__':
    unittest.main()