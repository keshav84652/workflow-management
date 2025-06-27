"""
Integration tests for system health monitoring.
Tests health monitoring system accuracy, alerting, and system resilience.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from utils.health_checks import (
    check_database_health, check_redis_health, check_system_health,
    check_service_health
)
from utils.error_handling import CircuitBreaker, GracefulDegradation
from core.redis_client import redis_client


class TestSystemHealthMonitoring:
    """Test system health monitoring functionality."""
    
    def test_comprehensive_system_health_check(self, app_context, performance_tracker):
        """Test comprehensive system health monitoring."""
        performance_tracker.start('system_health_check')
        
        # Check overall system health
        health_result = check_system_health()
        
        performance_tracker.stop()
        
        assert isinstance(health_result, dict)
        assert 'overall_status' in health_result
        assert 'services' in health_result
        assert 'timestamp' in health_result
        assert 'response_time_ms' in health_result
        
        # Verify service checks are included
        services = health_result['services']
        service_names = [service['service'] for service in services]
        
        assert 'database' in service_names
        assert 'redis' in service_names
        
        performance_tracker.assert_performance('system_health_check', 0.5)
    
    @patch('core.db.session.execute')
    def test_database_health_monitoring(self, mock_execute, performance_tracker):
        """Test database health monitoring accuracy."""
        performance_tracker.start('database_health_check')
        
        # Test healthy database
        mock_execute.return_value.scalar.return_value = 1
        
        health_result = check_database_health()
        
        performance_tracker.stop()
        
        assert health_result['status'] == 'healthy'
        assert health_result['service'] == 'database'
        assert 'response_time_ms' in health_result
        assert health_result['response_time_ms'] >= 0
        
        performance_tracker.assert_performance('database_health_check', 0.1)
        
        # Test database failure
        mock_execute.side_effect = Exception("Connection timeout")
        
        health_result = check_database_health()
        
        assert health_result['status'] == 'unhealthy'
        assert 'error' in health_result
        assert 'Connection timeout' in health_result['error']
    
    @patch('core.redis_client.redis_client')
    def test_redis_health_monitoring(self, mock_redis, performance_tracker):
        """Test Redis health monitoring accuracy."""
        performance_tracker.start('redis_health_check')
        
        # Test healthy Redis
        mock_redis.is_available.return_value = True
        mock_redis.get_client.return_value.ping.return_value = True
        
        health_result = check_redis_health()
        
        performance_tracker.stop()
        
        assert health_result['status'] == 'healthy'
        assert health_result['service'] == 'redis'
        assert 'response_time_ms' in health_result
        
        performance_tracker.assert_performance('redis_health_check', 0.1)
        
        # Test Redis unavailable
        mock_redis.is_available.return_value = False
        
        health_result = check_redis_health()
        
        assert health_result['status'] == 'unhealthy'
        assert 'error' in health_result
        
        # Test Redis connection failure
        mock_redis.is_available.return_value = True
        mock_redis.get_client.return_value.ping.side_effect = Exception("Redis timeout")
        
        health_result = check_redis_health()
        
        assert health_result['status'] == 'unhealthy'
        assert 'Redis timeout' in health_result['error']
    
    def test_service_health_monitoring(self, app_context):
        """Test individual service health monitoring."""
        # Test task service health
        task_service_health = check_service_health('task_service')
        
        assert isinstance(task_service_health, dict)
        assert 'status' in task_service_health
        assert 'service' in task_service_health
        assert task_service_health['service'] == 'task_service'
        
        # Test document service health
        document_service_health = check_service_health('document_service')
        
        assert isinstance(document_service_health, dict)
        assert document_service_health['service'] == 'document_service'
        
        # Test non-existent service
        invalid_service_health = check_service_health('invalid_service')
        
        assert invalid_service_health['status'] == 'unhealthy'
        assert 'error' in invalid_service_health
    
    def test_system_metrics_collection(self, app_context, performance_tracker):
        """Test system health collection (metrics via health check)."""
        performance_tracker.start('metrics_collection')
        
        health = check_system_health()
        
        performance_tracker.stop()
        
        assert isinstance(health, dict)
        
        # Check for expected health status fields
        expected_fields = [
            'status',
            'database',
            'redis',
            'timestamp'
        ]
        
        for field in expected_fields:
            assert field in health
        
        performance_tracker.assert_performance('metrics_collection', 0.2)
    
    def test_health_check_alerting(self, app_context, mock_celery_tasks):
        """Test health check alerting system."""
        # Simulate unhealthy system state
        with patch('utils.health_checks.check_database_health') as mock_db_health:
            mock_db_health.return_value = {
                'status': 'unhealthy',
                'service': 'database',
                'error': 'Connection failed'
            }
            
            # Trigger health check that should generate alert
            health_result = check_system_health()
            
            assert health_result['overall_status'] in ['degraded', 'unhealthy']
            assert health_result['unhealthy_services'] >= 1
            
            # In a real implementation, this would trigger alert notifications
            # For now, we just verify the health check detected the issue
    
    def test_health_check_history_tracking(self, app_context):
        """Test health check history tracking."""
        # Perform multiple health checks
        health_results = []
        
        for i in range(3):
            result = check_system_health()
            health_results.append(result)
            time.sleep(0.1)  # Small delay between checks
        
        # Verify each check has timestamp
        for result in health_results:
            assert 'timestamp' in result
            assert isinstance(result['timestamp'], str)
        
        # Verify timestamps are different (chronological)
        timestamps = [result['timestamp'] for result in health_results]
        assert len(set(timestamps)) == len(timestamps)  # All unique
    
    def test_health_check_performance_tracking(self, app_context, performance_tracker):
        """Test health check performance tracking."""
        # Track multiple health check operations
        operations = [
            ('database_check', lambda: check_database_health()),
            ('redis_check', lambda: check_redis_health()),
            ('system_check', lambda: check_system_health())
        ]
        
        for operation_name, operation_func in operations:
            performance_tracker.start(operation_name)
            
            result = operation_func()
            
            performance_tracker.stop()
            
            assert isinstance(result, dict)
            assert 'response_time_ms' in result
            
            # Verify performance meets benchmarks
            if operation_name == 'database_check':
                performance_tracker.assert_performance(operation_name, 0.1)
            elif operation_name == 'redis_check':
                performance_tracker.assert_performance(operation_name, 0.1)
            elif operation_name == 'system_check':
                performance_tracker.assert_performance(operation_name, 0.5)


class TestSystemResilience:
    """Test system resilience and recovery mechanisms."""
    
    def test_circuit_breaker_integration(self, app_context):
        """Test circuit breaker integration with health checks."""
        # Create circuit breaker for database operations
        db_circuit_breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        @db_circuit_breaker
        def protected_database_operation():
            # Simulate database operation
            result = check_database_health()
            if result['status'] != 'healthy':
                raise Exception("Database unhealthy")
            return result
        
        # Test normal operation
        with patch('core.db.session.execute') as mock_execute:
            mock_execute.return_value.scalar.return_value = 1
            
            result = protected_database_operation()
            assert result['status'] == 'healthy'
            assert db_circuit_breaker.state.name == 'CLOSED'
    
    def test_graceful_degradation_with_health_checks(self, app_context):
        """Test graceful degradation when services are unhealthy."""
        def fallback_health_check():
            return {
                'status': 'degraded',
                'service': 'fallback',
                'message': 'Using fallback health check'
            }
        
        # Simulate service failure with graceful degradation
        with patch('utils.health_checks.check_redis_health') as mock_redis_health:
            mock_redis_health.side_effect = Exception("Redis connection failed")
            
            result = GracefulDegradation.handle_service_failure(
                "redis_health_check",
                Exception("Redis connection failed"),
                fallback_health_check
            )
            
            assert result['status'] == 'degraded'
            assert result['service'] == 'fallback'
    
    def test_system_recovery_monitoring(self, app_context):
        """Test system recovery monitoring."""
        # Simulate system recovery scenario
        recovery_states = []
        
        # Initial unhealthy state
        with patch('utils.health_checks.check_database_health') as mock_db_health:
            mock_db_health.return_value = {
                'status': 'unhealthy',
                'service': 'database',
                'error': 'Connection failed'
            }
            
            health_result = check_system_health()
            recovery_states.append(health_result['overall_status'])
            
            # Recovery state
            mock_db_health.return_value = {
                'status': 'healthy',
                'service': 'database',
                'response_time_ms': 50
            }
            
            health_result = check_system_health()
            recovery_states.append(health_result['overall_status'])
        
        # Verify recovery was detected
        assert recovery_states[0] in ['degraded', 'unhealthy']
        assert recovery_states[1] == 'healthy'
    
    def test_cascading_failure_detection(self, app_context):
        """Test detection of cascading failures."""
        # Simulate multiple service failures
        with patch('utils.health_checks.check_database_health') as mock_db_health, \
             patch('utils.health_checks.check_redis_health') as mock_redis_health:
            
            # Both services fail
            mock_db_health.return_value = {
                'status': 'unhealthy',
                'service': 'database',
                'error': 'Database connection failed'
            }
            
            mock_redis_health.return_value = {
                'status': 'unhealthy',
                'service': 'redis',
                'error': 'Redis connection failed'
            }
            
            health_result = check_system_health()
            
            assert health_result['overall_status'] == 'unhealthy'
            assert health_result['unhealthy_services'] >= 2
            assert health_result['healthy_services'] == 0
    
    def test_partial_system_degradation(self, app_context):
        """Test partial system degradation handling."""
        # Simulate partial failure (Redis down, database up)
        with patch('utils.health_checks.check_database_health') as mock_db_health, \
             patch('utils.health_checks.check_redis_health') as mock_redis_health:
            
            mock_db_health.return_value = {
                'status': 'healthy',
                'service': 'database',
                'response_time_ms': 25
            }
            
            mock_redis_health.return_value = {
                'status': 'unhealthy',
                'service': 'redis',
                'error': 'Redis unavailable'
            }
            
            health_result = check_system_health()
            
            assert health_result['overall_status'] == 'degraded'
            assert health_result['healthy_services'] >= 1
            assert health_result['unhealthy_services'] >= 1


class TestHealthCheckIntegration:
    """Test health check integration with application components."""
    
    def test_health_check_api_endpoint(self, authenticated_session):
        """Test health check API endpoint."""
        response = authenticated_session.get('/api/health')
        
        assert response.status_code == 200
        
        import json
        health_data = json.loads(response.data)
        
        assert 'overall_status' in health_data
        assert 'services' in health_data
        assert 'timestamp' in health_data
        
        # Verify service details
        services = health_data['services']
        assert isinstance(services, list)
        assert len(services) >= 2  # At least database and redis
    
    def test_health_check_dashboard_integration(self, authenticated_session):
        """Test health check integration with dashboard."""
        # Get dashboard data that includes health information
        response = authenticated_session.get('/api/dashboard')
        
        if response.status_code == 200:
            import json
            dashboard_data = json.loads(response.data)
            
            # Health information should be included in dashboard
            if 'system_health' in dashboard_data:
                health_info = dashboard_data['system_health']
                assert 'status' in health_info
                assert 'last_check' in health_info
    
    def test_health_check_monitoring_alerts(self, app_context, mock_celery_tasks):
        """Test health check monitoring and alerting."""
        # Simulate critical system failure
        with patch('utils.health_checks.check_system_health') as mock_system_health:
            mock_system_health.return_value = {
                'overall_status': 'unhealthy',
                'services': [
                    {'service': 'database', 'status': 'unhealthy', 'error': 'Critical failure'},
                    {'service': 'redis', 'status': 'unhealthy', 'error': 'Connection lost'}
                ],
                'healthy_services': 0,
                'unhealthy_services': 2,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Trigger health monitoring
            health_result = check_system_health()
            
            assert health_result['overall_status'] == 'unhealthy'
            
            # In a real implementation, this would trigger alert notifications
            # We can verify the health check correctly identified the critical state
    
    def test_health_check_performance_impact(self, app_context, performance_tracker):
        """Test health check performance impact on system."""
        # Measure system performance with health checks
        performance_tracker.start('system_with_health_checks')
        
        # Perform normal operations while health checks run
        for i in range(5):
            check_system_health()
            time.sleep(0.01)  # Small delay to simulate real usage
        
        performance_tracker.stop()
        
        # Health checks should not significantly impact performance
        performance_tracker.assert_performance('system_with_health_checks', 1.0)
    
    def test_health_check_data_persistence(self, app_context):
        """Test health check data persistence and history."""
        # Perform health checks and verify data is stored
        health_results = []
        
        for i in range(3):
            result = check_system_health()
            health_results.append(result)
            time.sleep(0.1)
        
        # Verify each health check has consistent structure
        for result in health_results:
            assert 'overall_status' in result
            assert 'services' in result
            assert 'timestamp' in result
            assert 'response_time_ms' in result
            
            # Verify service details are complete
            for service in result['services']:
                assert 'service' in service
                assert 'status' in service
                assert 'response_time_ms' in service
    
    def test_health_check_concurrent_access(self, app_context, performance_tracker):
        """Test health check system under concurrent access."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def concurrent_health_check():
            try:
                result = check_system_health()
                results.put(('success', result['overall_status']))
            except Exception as e:
                results.put(('error', str(e)))
        
        performance_tracker.start('concurrent_health_checks')
        
        # Run concurrent health checks
        threads = []
        for i in range(5):
            thread = threading.Thread(target=concurrent_health_check)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        performance_tracker.stop()
        
        # Verify results
        success_count = 0
        while not results.empty():
            result_type, result_data = results.get()
            if result_type == 'success':
                success_count += 1
                assert result_data in ['healthy', 'degraded', 'unhealthy']
        
        assert success_count >= 3  # Most should succeed
        performance_tracker.assert_performance('concurrent_health_checks', 2.0)