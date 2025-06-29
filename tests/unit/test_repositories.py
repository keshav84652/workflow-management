"""
Unit tests for repository layer components.
Tests repository base classes, caching logic, and data access patterns.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date

from repositories.base import BaseRepository
from repositories.task_repository import TaskRepository
from src.models import Task, Project, User, Firm


class TestBaseRepository:
    """Test BaseRepository functionality."""
    
    def test_base_repository_initialization(self):
        """Test BaseRepository initialization."""
        repo = BaseRepository()
        assert repo is not None
    
    def test_get_cache_key(self):
        """Test cache key generation."""
        repo = BaseRepository()
        
        # Test simple cache key
        key = repo._get_cache_key('tasks', firm_id=123)
        assert key == 'cache:tasks:firm:123'
        
        # Test cache key with additional params
        key = repo._get_cache_key('tasks', firm_id=123, status='active')
        assert 'firm:123' in key
        assert 'status:active' in key
    
    @patch('core.redis_client.redis_client')
    def test_get_from_cache_hit(self, mock_redis):
        """Test cache hit scenario."""
        mock_redis.is_available.return_value = True
        mock_redis.get.return_value = '{"data": "cached_value"}'
        
        repo = BaseRepository()
        result = repo._get_from_cache('test_key')
        
        assert result == {"data": "cached_value"}
        mock_redis.get.assert_called_once_with('test_key')
    
    @patch('core.redis_client.redis_client')
    def test_get_from_cache_miss(self, mock_redis):
        """Test cache miss scenario."""
        mock_redis.is_available.return_value = True
        mock_redis.get.return_value = None
        
        repo = BaseRepository()
        result = repo._get_from_cache('test_key')
        
        assert result is None
        mock_redis.get.assert_called_once_with('test_key')
    
    @patch('core.redis_client.redis_client')
    def test_get_from_cache_redis_unavailable(self, mock_redis):
        """Test cache behavior when Redis is unavailable."""
        mock_redis.is_available.return_value = False
        
        repo = BaseRepository()
        result = repo._get_from_cache('test_key')
        
        assert result is None
        mock_redis.get.assert_not_called()
    
    @patch('core.redis_client.redis_client')
    def test_set_cache_success(self, mock_redis):
        """Test successful cache setting."""
        mock_redis.is_available.return_value = True
        mock_redis.setex.return_value = True
        
        repo = BaseRepository()
        data = {"test": "data"}
        
        result = repo._set_cache('test_key', data, ttl=300)
        
        assert result is True
        mock_redis.setex.assert_called_once()
        
        # Check the call arguments
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == 'test_key'
        assert call_args[0][1] == 300  # TTL
    
    @patch('core.redis_client.redis_client')
    def test_set_cache_redis_unavailable(self, mock_redis):
        """Test cache setting when Redis is unavailable."""
        mock_redis.is_available.return_value = False
        
        repo = BaseRepository()
        data = {"test": "data"}
        
        result = repo._set_cache('test_key', data)
        
        assert result is False
        mock_redis.setex.assert_not_called()
    
    @patch('core.redis_client.redis_client')
    def test_invalidate_cache(self, mock_redis):
        """Test cache invalidation."""
        mock_redis.is_available.return_value = True
        mock_redis.delete.return_value = 1
        
        repo = BaseRepository()
        result = repo._invalidate_cache('test_key')
        
        assert result is True
        mock_redis.delete.assert_called_once_with('test_key')
    
    @patch('core.redis_client.redis_client')
    def test_invalidate_cache_pattern(self, mock_redis):
        """Test cache invalidation by pattern."""
        mock_redis.is_available.return_value = True
        mock_redis.keys.return_value = ['cache:tasks:firm:123', 'cache:tasks:firm:124']
        mock_redis.delete.return_value = 2
        
        repo = BaseRepository()
        result = repo._invalidate_cache_pattern('cache:tasks:*')
        
        assert result is True
        mock_redis.keys.assert_called_once_with('cache:tasks:*')
        mock_redis.delete.assert_called_once()
    
    def test_serialize_for_cache(self):
        """Test data serialization for cache."""
        repo = BaseRepository()
        
        # Test dict serialization
        data = {"key": "value", "number": 123}
        serialized = repo._serialize_for_cache(data)
        assert isinstance(serialized, str)
        
        # Test list serialization
        data = [1, 2, 3, "test"]
        serialized = repo._serialize_for_cache(data)
        assert isinstance(serialized, str)
    
    def test_deserialize_from_cache(self):
        """Test data deserialization from cache."""
        repo = BaseRepository()
        
        # Test dict deserialization
        serialized = '{"key": "value", "number": 123}'
        data = repo._deserialize_from_cache(serialized)
        assert data == {"key": "value", "number": 123}
        
        # Test list deserialization
        serialized = '[1, 2, 3, "test"]'
        data = repo._deserialize_from_cache(serialized)
        assert data == [1, 2, 3, "test"]
        
        # Test invalid JSON
        data = repo._deserialize_from_cache('invalid json')
        assert data is None


class TestTaskRepository:
    """Test TaskRepository functionality."""
    
    def test_task_repository_initialization(self):
        """Test TaskRepository initialization."""
        repo = TaskRepository()
        assert repo is not None
    
    @patch('core.redis_client.redis_client')
    def test_get_tasks_by_firm_cache_miss(self, mock_redis, app_context, test_firm):
        """Test getting tasks by firm with cache miss."""
        mock_redis.is_available.return_value = True
        mock_redis.get.return_value = None  # Cache miss
        mock_redis.setex.return_value = True
        
        tasks = TaskRepository.get_tasks_by_firm(test_firm.id)
        
        assert isinstance(tasks, list)
        mock_redis.get.assert_called_once()
        mock_redis.setex.assert_called_once()  # Cache was set
    
    @patch('core.redis_client.redis_client')
    def test_get_tasks_by_firm_cache_hit(self, mock_redis, app_context, test_firm):
        """Test getting tasks by firm with cache hit."""
        mock_redis.is_available.return_value = True
        
        # Mock cached data
        cached_tasks = [
            {
                'id': 1,
                'title': 'Cached Task',
                'status': 'Not Started',
                'firm_id': test_firm.id
            }
        ]
        mock_redis.get.return_value = TaskRepository()._serialize_for_cache(cached_tasks)
        
        tasks = TaskRepository.get_tasks_by_firm(test_firm.id)
        
        assert isinstance(tasks, list)
        assert len(tasks) == 1
        assert tasks[0]['title'] == 'Cached Task'
        mock_redis.get.assert_called_once()
        mock_redis.setex.assert_not_called()  # Cache was not set (hit)
    
    @patch('core.redis_client.redis_client')
    def test_get_task_by_id_with_cache(self, mock_redis, app_context, test_firm):
        """Test getting single task by ID with caching."""
        mock_redis.is_available.return_value = True
        mock_redis.get.return_value = None  # Cache miss
        mock_redis.setex.return_value = True
        
        # This would normally query the database
        task = TaskRepository.get_task_by_id(999, test_firm.id)
        
        # Should return None for non-existent task
        assert task is None
        mock_redis.get.assert_called_once()
    
    @patch('core.redis_client.redis_client')
    def test_invalidate_firm_cache(self, mock_redis, test_firm):
        """Test invalidating cache for a specific firm."""
        mock_redis.is_available.return_value = True
        mock_redis.keys.return_value = [
            f'cache:tasks:firm:{test_firm.id}',
            f'cache:tasks:firm:{test_firm.id}:status:active'
        ]
        mock_redis.delete.return_value = 2
        
        result = TaskRepository.invalidate_cache(test_firm.id)
        
        assert result is True
        mock_redis.keys.assert_called_once()
        mock_redis.delete.assert_called_once()
    
    def test_get_tasks_by_status_filter(self, app_context, test_firm):
        """Test filtering tasks by status."""
        # This tests the repository logic without caching
        with patch('core.redis_client.redis_client') as mock_redis:
            mock_redis.is_available.return_value = False  # Disable cache
            
            tasks = TaskRepository.get_tasks_by_status(test_firm.id, 'Not Started')
            assert isinstance(tasks, list)
    
    def test_get_tasks_by_project(self, app_context, test_firm, test_project):
        """Test getting tasks by project."""
        with patch('core.redis_client.redis_client') as mock_redis:
            mock_redis.is_available.return_value = False  # Disable cache
            
            tasks = TaskRepository.get_tasks_by_project(test_project.id, test_firm.id)
            assert isinstance(tasks, list)
    
    def test_get_overdue_tasks(self, app_context, test_firm):
        """Test getting overdue tasks."""
        with patch('core.redis_client.redis_client') as mock_redis:
            mock_redis.is_available.return_value = False  # Disable cache
            
            overdue_tasks = TaskRepository.get_overdue_tasks(test_firm.id)
            assert isinstance(overdue_tasks, list)
    
    def test_get_tasks_due_soon(self, app_context, test_firm):
        """Test getting tasks due soon."""
        with patch('core.redis_client.redis_client') as mock_redis:
            mock_redis.is_available.return_value = False  # Disable cache
            
            due_soon_tasks = TaskRepository.get_tasks_due_soon(test_firm.id, days=7)
            assert isinstance(due_soon_tasks, list)
    
    @patch('core.redis_client.redis_client')
    def test_cache_performance_tracking(self, mock_redis, performance_tracker, test_firm):
        """Test repository caching performance."""
        mock_redis.is_available.return_value = True
        mock_redis.get.return_value = None  # Cache miss
        mock_redis.setex.return_value = True
        
        performance_tracker.start('repository_cache_operation')
        
        # Perform repository operation
        tasks = TaskRepository.get_tasks_by_firm(test_firm.id)
        
        performance_tracker.stop()
        
        assert isinstance(tasks, list)
        performance_tracker.assert_performance('repository_cache_operation', 0.1)
    
    def test_repository_error_handling(self, app_context, test_firm):
        """Test repository error handling."""
        with patch('models.Task.query') as mock_query:
            mock_query.filter_by.side_effect = Exception("Database error")
            
            # Repository should handle database errors gracefully
            with pytest.raises(Exception):
                TaskRepository.get_tasks_by_firm(test_firm.id)
    
    @patch('core.redis_client.redis_client')
    def test_cache_serialization_edge_cases(self, mock_redis):
        """Test cache serialization with edge cases."""
        mock_redis.is_available.return_value = True
        
        repo = TaskRepository()
        
        # Test None serialization
        serialized = repo._serialize_for_cache(None)
        assert serialized == 'null'
        
        # Test empty list serialization
        serialized = repo._serialize_for_cache([])
        assert serialized == '[]'
        
        # Test empty dict serialization
        serialized = repo._serialize_for_cache({})
        assert serialized == '{}'
        
        # Test datetime serialization (should be handled)
        data_with_datetime = {
            'created_at': datetime.now().isoformat(),
            'date': date.today().isoformat()
        }
        serialized = repo._serialize_for_cache(data_with_datetime)
        assert isinstance(serialized, str)
    
    @patch('core.redis_client.redis_client')
    def test_cache_ttl_configuration(self, mock_redis, test_firm):
        """Test cache TTL configuration."""
        mock_redis.is_available.return_value = True
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        
        # Get tasks (should set cache with default TTL)
        TaskRepository.get_tasks_by_firm(test_firm.id)
        
        # Verify setex was called with TTL
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        
        # Check that TTL was provided (should be > 0)
        ttl = call_args[0][1]
        assert ttl > 0
    
    def test_repository_data_transformation(self, app_context, test_firm):
        """Test repository data transformation."""
        with patch('core.redis_client.redis_client') as mock_redis:
            mock_redis.is_available.return_value = False
            
            # Test that repository returns properly formatted data
            tasks = TaskRepository.get_tasks_by_firm(test_firm.id)
            
            assert isinstance(tasks, list)
            
            # If tasks exist, check their structure
            for task in tasks:
                if isinstance(task, dict):
                    # Should have required fields
                    assert 'id' in task or hasattr(task, 'id')
                    assert 'title' in task or hasattr(task, 'title')
                    assert 'firm_id' in task or hasattr(task, 'firm_id')


class TestRepositoryIntegration:
    """Test repository integration scenarios."""
    
    @patch('core.redis_client.redis_client')
    def test_multi_repository_cache_consistency(self, mock_redis, test_firm):
        """Test cache consistency across multiple repositories."""
        mock_redis.is_available.return_value = True
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        mock_redis.delete.return_value = 1
        
        # Get data from TaskRepository
        tasks = TaskRepository.get_tasks_by_firm(test_firm.id)
        
        # Invalidate cache
        TaskRepository.invalidate_cache(test_firm.id)
        
        # Verify cache invalidation was called
        mock_redis.delete.assert_called()
    
    def test_repository_fallback_behavior(self, app_context, test_firm):
        """Test repository fallback when cache fails."""
        with patch('core.redis_client.redis_client') as mock_redis:
            # Simulate Redis failure
            mock_redis.is_available.return_value = True
            mock_redis.get.side_effect = Exception("Redis connection failed")
            
            # Repository should fall back to database
            tasks = TaskRepository.get_tasks_by_firm(test_firm.id)
            assert isinstance(tasks, list)
    
    @patch('core.redis_client.redis_client')
    def test_concurrent_cache_access(self, mock_redis, test_firm):
        """Test concurrent cache access safety."""
        mock_redis.is_available.return_value = True
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        
        import threading
        import queue
        
        results = queue.Queue()
        
        def get_tasks_worker():
            try:
                tasks = TaskRepository.get_tasks_by_firm(test_firm.id)
                results.put(('success', len(tasks)))
            except Exception as e:
                results.put(('error', str(e)))
        
        # Create multiple threads accessing cache
        threads = []
        for i in range(3):
            thread = threading.Thread(target=get_tasks_worker)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check results
        success_count = 0
        while not results.empty():
            result_type, result_data = results.get()
            if result_type == 'success':
                success_count += 1
        
        assert success_count >= 1  # At least one should succeed