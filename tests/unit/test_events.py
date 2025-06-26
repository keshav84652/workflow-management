"""
Unit tests for event system components.
Tests event schemas, publishers, subscribers, and event handlers.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from events.base import BaseEvent, EventHandler, EventRegistry, event_registry
from events.publisher import EventPublisher, publish_event
from events.subscriber import EventSubscriber
from events.schemas import (
    TaskCreatedEvent, TaskUpdatedEvent, TaskStatusChangedEvent,
    TaskDeletedEvent, TaskAssignedEvent, DocumentUploadedEvent,
    ProjectCreatedEvent, ErrorEvent
)


class TestEventSchemas:
    """Test event schema definitions and validation."""
    
    def test_base_event_creation(self):
        """Test BaseEvent creation and properties."""
        event = BaseEvent(
            event_type='test_event',
            firm_id=123,
            user_id=456,
            timestamp=datetime.utcnow()
        )
        
        assert event.event_type == 'test_event'
        assert event.firm_id == 123
        assert event.user_id == 456
        assert isinstance(event.timestamp, datetime)
        assert isinstance(event.event_id, str)
    
    def test_task_created_event(self):
        """Test TaskCreatedEvent schema."""
        event = TaskCreatedEvent(
            task_id=123,
            task_title='Test Task',
            project_id=456,
            assignee_id=789,
            priority='High',
            firm_id=1
        )
        
        assert event.event_type == 'task_created'
        assert event.task_id == 123
        assert event.task_title == 'Test Task'
        assert event.project_id == 456
        assert event.assignee_id == 789
        assert event.priority == 'High'
        assert event.firm_id == 1
    
    def test_task_status_changed_event(self):
        """Test TaskStatusChangedEvent schema."""
        event = TaskStatusChangedEvent(
            task_id=123,
            task_title='Test Task',
            old_status='Not Started',
            new_status='In Progress',
            firm_id=1
        )
        
        assert event.event_type == 'task_status_changed'
        assert event.task_id == 123
        assert event.old_status == 'Not Started'
        assert event.new_status == 'In Progress'
    
    def test_document_uploaded_event(self):
        """Test DocumentUploadedEvent schema."""
        event = DocumentUploadedEvent(
            document_id=123,
            document_name='test.pdf',
            file_size=1024,
            client_id=456,
            firm_id=1
        )
        
        assert event.event_type == 'document_uploaded'
        assert event.document_id == 123
        assert event.document_name == 'test.pdf'
        assert event.file_size == 1024
        assert event.client_id == 456
    
    def test_error_event(self):
        """Test ErrorEvent schema."""
        event = ErrorEvent(
            error_type='ValidationError',
            error_message='Invalid input data',
            context={'field': 'email'},
            firm_id=1
        )
        
        assert event.event_type == 'error'
        assert event.error_type == 'ValidationError'
        assert event.error_message == 'Invalid input data'
        assert event.context == {'field': 'email'}
    
    def test_event_serialization(self):
        """Test event serialization to dict."""
        event = TaskCreatedEvent(
            task_id=123,
            task_title='Test Task',
            firm_id=1
        )
        
        event_dict = event.to_dict()
        
        assert isinstance(event_dict, dict)
        assert event_dict['event_type'] == 'task_created'
        assert event_dict['task_id'] == 123
        assert event_dict['task_title'] == 'Test Task'
        assert event_dict['firm_id'] == 1
        assert 'timestamp' in event_dict
        assert 'event_id' in event_dict


class TestEventPublisher:
    """Test event publisher functionality."""
    
    @patch('core.redis_client.redis_client')
    def test_event_publisher_initialization(self, mock_redis):
        """Test EventPublisher initialization."""
        mock_redis.is_available.return_value = True
        
        publisher = EventPublisher(mock_redis)
        assert publisher.redis_client == mock_redis
    
    @patch('core.redis_client.redis_client')
    def test_publish_event_success(self, mock_redis):
        """Test successful event publishing."""
        mock_redis.is_available.return_value = True
        mock_redis.publish.return_value = 1
        
        publisher = EventPublisher(mock_redis)
        event = TaskCreatedEvent(task_id=123, task_title='Test', firm_id=1)
        
        result = publisher.publish(event)
        
        assert result is True
        mock_redis.publish.assert_called_once()
        
        # Check the published data
        call_args = mock_redis.publish.call_args
        channel = call_args[0][0]
        assert channel == 'events:task_created'
    
    @patch('core.redis_client.redis_client')
    def test_publish_event_redis_unavailable(self, mock_redis):
        """Test event publishing when Redis is unavailable."""
        mock_redis.is_available.return_value = False
        
        publisher = EventPublisher(mock_redis)
        event = TaskCreatedEvent(task_id=123, task_title='Test', firm_id=1)
        
        result = publisher.publish(event)
        
        assert result is False
        mock_redis.publish.assert_not_called()
    
    @patch('core.redis_client.redis_client')
    def test_publish_event_with_retry(self, mock_redis):
        """Test event publishing with retry logic."""
        mock_redis.is_available.return_value = True
        mock_redis.publish.side_effect = [Exception("Connection error"), 1]
        
        publisher = EventPublisher(mock_redis)
        event = TaskCreatedEvent(task_id=123, task_title='Test', firm_id=1)
        
        result = publisher.publish(event)
        
        assert result is True
        assert mock_redis.publish.call_count == 2
    
    @patch('events.publisher.event_publisher')
    def test_publish_event_function(self, mock_publisher):
        """Test the publish_event convenience function."""
        mock_publisher.publish.return_value = True
        
        event = TaskCreatedEvent(task_id=123, task_title='Test', firm_id=1)
        result = publish_event(event)
        
        assert result is True
        mock_publisher.publish.assert_called_once_with(event)


class TestEventSubscriber:
    """Test event subscriber functionality."""
    
    @patch('core.redis_client.redis_client')
    def test_event_subscriber_initialization(self, mock_redis):
        """Test EventSubscriber initialization."""
        mock_redis.is_available.return_value = True
        
        subscriber = EventSubscriber(mock_redis)
        assert subscriber.redis_client == mock_redis
        assert subscriber.subscriptions == {}
    
    @patch('core.redis_client.redis_client')
    def test_subscribe_to_event(self, mock_redis):
        """Test subscribing to events."""
        mock_redis.is_available.return_value = True
        mock_pubsub = Mock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        subscriber = EventSubscriber(mock_redis)
        
        def test_handler(event_data):
            return True
        
        result = subscriber.subscribe('task_created', test_handler)
        
        assert result is True
        assert 'task_created' in subscriber.subscriptions
        mock_pubsub.subscribe.assert_called_with('events:task_created')
    
    @patch('core.redis_client.redis_client')
    def test_unsubscribe_from_event(self, mock_redis):
        """Test unsubscribing from events."""
        mock_redis.is_available.return_value = True
        mock_pubsub = Mock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        subscriber = EventSubscriber(mock_redis)
        
        # First subscribe
        def test_handler(event_data):
            return True
        
        subscriber.subscribe('task_created', test_handler)
        
        # Then unsubscribe
        result = subscriber.unsubscribe('task_created')
        
        assert result is True
        assert 'task_created' not in subscriber.subscriptions
        mock_pubsub.unsubscribe.assert_called_with('events:task_created')


class TestEventHandlers:
    """Test event handler base class and registry."""
    
    def test_event_handler_base_class(self):
        """Test EventHandler base class."""
        class TestHandler(EventHandler):
            def can_handle(self, event):
                return event.event_type == 'test_event'
            
            async def handle(self, event):
                return True
        
        handler = TestHandler()
        
        # Test can_handle
        test_event = BaseEvent(event_type='test_event', firm_id=1)
        other_event = BaseEvent(event_type='other_event', firm_id=1)
        
        assert handler.can_handle(test_event) is True
        assert handler.can_handle(other_event) is False
    
    def test_event_registry_registration(self):
        """Test event handler registration."""
        class TestHandler(EventHandler):
            def can_handle(self, event):
                return True
            
            async def handle(self, event):
                return True
        
        handler = TestHandler()
        
        # Register handler
        event_registry.register_handler('test_event', handler)
        
        # Check registration
        handlers = event_registry.get_handlers('test_event')
        assert handler in handlers
    
    def test_event_registry_get_handlers(self):
        """Test getting handlers from registry."""
        class Handler1(EventHandler):
            def can_handle(self, event):
                return True
            async def handle(self, event):
                return True
        
        class Handler2(EventHandler):
            def can_handle(self, event):
                return True
            async def handle(self, event):
                return True
        
        handler1 = Handler1()
        handler2 = Handler2()
        
        # Register multiple handlers
        event_registry.register_handler('multi_event', handler1)
        event_registry.register_handler('multi_event', handler2)
        
        # Get all handlers
        handlers = event_registry.get_handlers('multi_event')
        assert len(handlers) >= 2
        assert handler1 in handlers
        assert handler2 in handlers
    
    def test_event_registry_clear_handlers(self):
        """Test clearing handlers from registry."""
        class TestHandler(EventHandler):
            def can_handle(self, event):
                return True
            async def handle(self, event):
                return True
        
        handler = TestHandler()
        
        # Register and then clear
        event_registry.register_handler('clear_test', handler)
        assert len(event_registry.get_handlers('clear_test')) > 0
        
        event_registry.clear_handlers('clear_test')
        assert len(event_registry.get_handlers('clear_test')) == 0


class TestEventIntegration:
    """Test event system integration scenarios."""
    
    @patch('core.redis_client.redis_client')
    def test_end_to_end_event_flow(self, mock_redis):
        """Test complete event flow from publish to handling."""
        mock_redis.is_available.return_value = True
        mock_redis.publish.return_value = 1
        
        # Create publisher and subscriber
        publisher = EventPublisher(mock_redis)
        subscriber = EventSubscriber(mock_redis)
        
        # Create handler
        handled_events = []
        
        def test_handler(event_data):
            handled_events.append(event_data)
            return True
        
        # Subscribe to events
        subscriber.subscribe('task_created', test_handler)
        
        # Publish event
        event = TaskCreatedEvent(task_id=123, task_title='Test', firm_id=1)
        result = publisher.publish(event)
        
        assert result is True
        mock_redis.publish.assert_called_once()
    
    def test_event_filtering_by_firm(self):
        """Test event filtering by firm_id."""
        firm1_event = TaskCreatedEvent(task_id=123, task_title='Firm 1 Task', firm_id=1)
        firm2_event = TaskCreatedEvent(task_id=124, task_title='Firm 2 Task', firm_id=2)
        
        class FirmFilterHandler(EventHandler):
            def __init__(self, firm_id):
                self.firm_id = firm_id
            
            def can_handle(self, event):
                return event.firm_id == self.firm_id
            
            async def handle(self, event):
                return True
        
        firm1_handler = FirmFilterHandler(1)
        firm2_handler = FirmFilterHandler(2)
        
        # Test filtering
        assert firm1_handler.can_handle(firm1_event) is True
        assert firm1_handler.can_handle(firm2_event) is False
        
        assert firm2_handler.can_handle(firm1_event) is False
        assert firm2_handler.can_handle(firm2_event) is True
    
    def test_event_error_handling(self):
        """Test error handling in event processing."""
        class FailingHandler(EventHandler):
            def can_handle(self, event):
                return True
            
            async def handle(self, event):
                raise Exception("Handler failed")
        
        handler = FailingHandler()
        event = TaskCreatedEvent(task_id=123, task_title='Test', firm_id=1)
        
        # Handler should raise exception
        with pytest.raises(Exception, match="Handler failed"):
            import asyncio
            asyncio.run(handler.handle(event))
    
    def test_event_performance_tracking(self, performance_tracker):
        """Test event processing performance."""
        performance_tracker.start('event_processing')
        
        # Create multiple events
        events = []
        for i in range(100):
            event = TaskCreatedEvent(
                task_id=i,
                task_title=f'Task {i}',
                firm_id=1
            )
            events.append(event)
        
        # Process events
        for event in events:
            event_dict = event.to_dict()
            assert isinstance(event_dict, dict)
        
        performance_tracker.stop()
        performance_tracker.assert_performance('event_processing', 0.1)  # 100ms for 100 events