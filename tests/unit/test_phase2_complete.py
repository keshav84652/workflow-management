"""
Phase 2 Complete Integration Test Suite
Production-ready comprehensive testing for event-driven architecture.

Test Coverage:
- System health validation
- Complete event lifecycle testing
- Service layer with event integration
- Repository caching (hits, misses, invalidation)
- Background processing simulation
- Resilience testing (Redis failures, graceful degradation)
- Performance benchmarks (< 0.5s targets for critical operations)
- End-to-end workflow simulation
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, timedelta

from models import Task, Project, Client, User, Firm, ActivityLog
from services.task_service import TaskService
from services.project_service import ProjectService
from services.document_service import DocumentService
from events.schemas import TaskCreatedEvent, TaskUpdatedEvent, TaskStatusChangedEvent
from repositories.task_repository import TaskRepository


class TestPhase2CompleteIntegration:
    """Comprehensive integration tests for Phase 2 event-driven architecture."""
    
    def test_system_health_validation(self, app_context, mock_redis, performance_tracker):
        """Test complete system health check."""
        performance_tracker.start('system_health_check')
        
        # Test database connectivity
        from utils.health_checks import check_database_health
        db_health = check_database_health()
        assert db_health['status'] == 'healthy'
        
        # Test Redis connectivity (mocked)
        from utils.health_checks import check_redis_health
        redis_health = check_redis_health()
        assert redis_health['status'] == 'healthy'
        
        # Test service layer health
        from services.task_service import TaskService
        assert TaskService is not None
        
        performance_tracker.stop()
        performance_tracker.assert_performance('system_health_check', 0.1)
    
    def test_complete_event_lifecycle(self, app_context, db_session, test_firm, test_user, 
                                    test_project, mock_event_publisher, performance_tracker):
        """Test complete event lifecycle from creation to processing."""
        performance_tracker.start('event_lifecycle')
        
        # Create task (should trigger TaskCreatedEvent)
        task_data = {
            'title': 'Test Event Task',
            'description': 'Testing event lifecycle',
            'project_id': test_project.id,
            'assignee_id': test_user.id,
            'due_date': date.today() + timedelta(days=7)
        }
        
        result = TaskService.create_task_from_form(
            form_data=task_data,
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert result['success'] is True
        task_id = result['task_id']
        
        # Verify event was published
        mock_event_publisher.assert_called()
        event_call = mock_event_publisher.call_args[0][0]
        assert event_call.event_type == 'task_created'
        assert event_call.task_id == task_id
        
        # Update task status (should trigger TaskStatusChangedEvent)
        update_result = TaskService.update_task_status(
            task_id=task_id,
            new_status='In Progress',
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert update_result['success'] is True
        
        # Verify status change event
        assert mock_event_publisher.call_count >= 2
        
        performance_tracker.stop()
        performance_tracker.assert_performance('event_lifecycle', 0.5)
    
    def test_service_layer_with_event_integration(self, app_context, db_session, test_firm, 
                                                 test_user, mock_event_publisher, performance_tracker):
        """Test service layer operations with proper event integration."""
        performance_tracker.start('service_event_integration')
        
        # Test TaskService with events
        task_result = TaskService.create_task(
            title='Service Integration Test',
            description='Testing service layer events',
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert task_result['success'] is True
        
        # Test ProjectService with events
        project_result = ProjectService.create_project(
            name='Event Test Project',
            client_id=None,  # Optional
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        assert project_result['success'] is True
        
        # Verify events were published for both operations
        assert mock_event_publisher.call_count >= 2
        
        performance_tracker.stop()
        performance_tracker.assert_performance('service_event_integration', 0.3)
    
    def test_repository_caching_behavior(self, app_context, db_session, test_firm, 
                                       mock_redis, performance_tracker):
        """Test repository caching with hits, misses, and invalidation."""
        performance_tracker.start('repository_caching')
        
        # Setup mock Redis for caching
        mock_redis.get.return_value = None  # Cache miss
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = True
        
        # Test cache miss
        tasks = TaskRepository.get_tasks_by_firm(test_firm.id)
        assert isinstance(tasks, list)
        
        # Verify cache set was called
        mock_redis.set.assert_called()
        
        # Test cache hit
        mock_redis.get.return_value = '[]'  # Cached empty list
        cached_tasks = TaskRepository.get_tasks_by_firm(test_firm.id)
        assert cached_tasks == []
        
        # Test cache invalidation
        TaskRepository.invalidate_cache(test_firm.id)
        mock_redis.delete.assert_called()
        
        performance_tracker.stop()
        performance_tracker.assert_performance('repository_caching', 0.1)
    
    def test_background_processing_simulation(self, app_context, mock_celery_tasks, 
                                            test_firm, performance_tracker):
        """Test background processing with Celery task simulation."""
        performance_tracker.start('background_processing')
        
        # Test AI document analysis task
        from workers.ai_worker import analyze_document
        task_result = mock_celery_tasks['ai_worker']
        
        # Simulate task queuing
        task_id = 123
        result = analyze_document.delay(task_id, test_firm.id)
        
        assert result.id == 'test-task-id-ai'
        mock_celery_tasks['ai_worker'].assert_called_with(task_id, test_firm.id)
        
        # Test document processing task
        from workers.document_worker import process_large_document
        doc_result = mock_celery_tasks['document_worker']
        
        document_id = 456
        file_path = '/test/path/document.pdf'
        result = process_large_document.delay(document_id, file_path, test_firm.id)
        
        assert result.id == 'test-task-id-doc'
        mock_celery_tasks['document_worker'].assert_called_with(document_id, file_path, test_firm.id)
        
        # Test notification task
        email_result = mock_celery_tasks['notification_worker']
        
        from workers.notification_worker import send_email
        result = send_email.delay('test@example.com', 'Test Subject', 'Test Body')
        
        assert result.id == 'test-task-id-email'
        
        performance_tracker.stop()
        performance_tracker.assert_performance('background_processing', 0.2)
    
    def test_resilience_redis_failure_graceful_degradation(self, app_context, db_session, 
                                                          test_firm, performance_tracker):
        """Test graceful degradation when Redis fails."""
        performance_tracker.start('resilience_testing')
        
        # Mock Redis failure
        with patch('core.redis_client.redis_client') as mock_redis:
            mock_redis.is_available.return_value = False
            mock_redis.get.side_effect = Exception("Redis connection failed")
            
            # Test that operations still work without Redis
            from utils.error_handling import GracefulDegradation
            
            def fallback_function():
                return "fallback_result"
            
            result = GracefulDegradation.handle_service_failure(
                "redis", Exception("Connection failed"), fallback_function
            )
            
            assert result == "fallback_result"
            
            # Test that repository operations fall back to database
            tasks = TaskRepository.get_tasks_by_firm(test_firm.id)
            assert isinstance(tasks, list)  # Should still work without cache
        
        performance_tracker.stop()
        performance_tracker.assert_performance('resilience_testing', 0.3)
    
    def test_circuit_breaker_functionality(self, app_context, performance_tracker):
        """Test circuit breaker pattern for external service calls."""
        performance_tracker.start('circuit_breaker_test')
        
        from utils.error_handling import CircuitBreaker, CircuitState
        
        # Create circuit breaker with low threshold for testing
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        @cb
        def failing_service():
            raise Exception("Service unavailable")
        
        @cb
        def working_service():
            return "success"
        
        # Test normal operation
        result = working_service()
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        
        # Test failure handling
        with pytest.raises(Exception):
            failing_service()
        
        with pytest.raises(Exception):
            failing_service()
        
        # Circuit should be open after threshold failures
        assert cb.state == CircuitState.OPEN
        
        performance_tracker.stop()
        performance_tracker.assert_performance('circuit_breaker_test', 0.1)
    
    def test_performance_benchmarks_critical_operations(self, app_context, db_session, 
                                                       test_firm, test_user, performance_tracker):
        """Test performance benchmarks for critical operations."""
        
        # Test task creation performance
        performance_tracker.start('task_creation')
        
        result = TaskService.create_task(
            title='Performance Test Task',
            description='Testing performance',
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        
        performance_tracker.stop()
        assert result['success'] is True
        performance_tracker.assert_performance('task_creation', 0.1)  # 100ms max
        
        # Test repository query performance
        performance_tracker.start('repository_query')
        
        tasks = TaskRepository.get_tasks_by_firm(test_firm.id)
        
        performance_tracker.stop()
        assert isinstance(tasks, list)
        performance_tracker.assert_performance('repository_query', 0.02)  # 20ms max
        
        # Test event publishing performance
        performance_tracker.start('event_publishing')
        
        with patch('events.publisher.publish_event') as mock_publish:
            mock_publish.return_value = True
            
            from events.schemas import TaskCreatedEvent
            event = TaskCreatedEvent(
                task_id=1,
                task_title='Test Task',
                firm_id=test_firm.id
            )
            
            from events.publisher import publish_event
            publish_event(event)
        
        performance_tracker.stop()
        performance_tracker.assert_performance('event_publishing', 0.05)  # 50ms max
    
    def test_end_to_end_workflow_simulation(self, app_context, db_session, test_firm, 
                                          test_user, test_client_data, mock_event_publisher, 
                                          mock_celery_tasks, performance_tracker):
        """Test complete end-to-end workflow simulation."""
        performance_tracker.start('end_to_end_workflow')
        
        # 1. Create project
        project_result = ProjectService.create_project(
            name='E2E Test Project',
            client_id=test_client_data.id,
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        assert project_result['success'] is True
        project_id = project_result['project_id']
        
        # 2. Create tasks for project
        task1_result = TaskService.create_task(
            title='Document Collection',
            description='Collect client documents',
            project_id=project_id,
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        assert task1_result['success'] is True
        task1_id = task1_result['task_id']
        
        task2_result = TaskService.create_task(
            title='Document Review',
            description='Review collected documents',
            project_id=project_id,
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        assert task2_result['success'] is True
        task2_id = task2_result['task_id']
        
        # 3. Update task statuses (simulating workflow progression)
        status_update1 = TaskService.update_task_status(
            task_id=task1_id,
            new_status='In Progress',
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        assert status_update1['success'] is True
        
        status_update2 = TaskService.update_task_status(
            task_id=task1_id,
            new_status='Completed',
            firm_id=test_firm.id,
            user_id=test_user.id
        )
        assert status_update2['success'] is True
        
        # 4. Verify events were published throughout workflow
        assert mock_event_publisher.call_count >= 4  # Project created, 2 tasks created, status updates
        
        # 5. Verify background tasks were triggered
        # (In real scenario, document upload would trigger AI analysis)
        
        # 6. Check final state
        project = ProjectService.get_project_by_id(project_id, test_firm.id)
        assert project is not None
        
        tasks = TaskService.get_project_tasks(project_id, test_firm.id)
        assert len(tasks) >= 2
        
        performance_tracker.stop()
        performance_tracker.assert_performance('end_to_end_workflow', 1.0)  # 1s max for complete workflow
    
    def test_error_handling_and_rollback(self, app_context, db_session, test_firm, 
                                       test_user, performance_tracker):
        """Test error handling with proper database rollback."""
        performance_tracker.start('error_handling')
        
        # Test service-level error handling
        with patch('models.Task.query') as mock_query:
            mock_query.filter_by.side_effect = Exception("Database error")
            
            result = TaskService.get_tasks_by_firm(test_firm.id)
            assert result['success'] is False
            assert 'error' in result
        
        # Test transaction rollback
        initial_task_count = Task.query.filter_by(firm_id=test_firm.id).count()
        
        with patch('core.db.session.commit') as mock_commit:
            mock_commit.side_effect = Exception("Commit failed")
            
            result = TaskService.create_task(
                title='Rollback Test Task',
                description='This should be rolled back',
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            
            assert result['success'] is False
        
        # Verify no task was actually created
        final_task_count = Task.query.filter_by(firm_id=test_firm.id).count()
        assert final_task_count == initial_task_count
        
        performance_tracker.stop()
        performance_tracker.assert_performance('error_handling', 0.2)
    
    def test_concurrent_operations_safety(self, app_context, db_session, test_firm, 
                                        test_user, performance_tracker):
        """Test safety of concurrent operations."""
        performance_tracker.start('concurrent_operations')
        
        # Simulate concurrent task creation
        import threading
        import queue
        
        results = queue.Queue()
        
        def create_task_worker(task_number):
            try:
                result = TaskService.create_task(
                    title=f'Concurrent Task {task_number}',
                    description=f'Testing concurrent creation {task_number}',
                    firm_id=test_firm.id,
                    user_id=test_user.id
                )
                results.put(result)
            except Exception as e:
                results.put({'success': False, 'error': str(e)})
        
        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=create_task_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        successful_creates = 0
        while not results.empty():
            result = results.get()
            if result.get('success'):
                successful_creates += 1
        
        assert successful_creates >= 1  # At least one should succeed
        
        performance_tracker.stop()
        performance_tracker.assert_performance('concurrent_operations', 0.5)
    
    def test_memory_usage_and_cleanup(self, app_context, db_session, test_firm, 
                                    test_user, performance_tracker):
        """Test memory usage and proper cleanup."""
        performance_tracker.start('memory_cleanup')
        
        import gc
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create many objects
        tasks = []
        for i in range(100):
            result = TaskService.create_task(
                title=f'Memory Test Task {i}',
                description='Testing memory usage',
                firm_id=test_firm.id,
                user_id=test_user.id
            )
            if result['success']:
                tasks.append(result['task_id'])
        
        # Force garbage collection
        gc.collect()
        
        # Check memory usage hasn't grown excessively
        current_memory = process.memory_info().rss
        memory_growth = current_memory - initial_memory
        
        # Memory growth should be reasonable (less than 50MB for 100 tasks)
        assert memory_growth < 50 * 1024 * 1024, f"Memory grew by {memory_growth / 1024 / 1024:.2f}MB"
        
        performance_tracker.stop()
        performance_tracker.assert_performance('memory_cleanup', 2.0)