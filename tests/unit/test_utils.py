"""
Unit tests for utility functions and helper components.
Tests error handling, health checks, session management, and core utilities.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
import time

from utils.error_handling import CircuitBreaker, CircuitState, GracefulDegradation
from utils.health_checks import check_database_health, check_redis_health, check_system_health
from utils.session_helpers import get_session_firm_id, get_session_user_id
from utils.consolidated import format_currency, format_date, calculate_business_days


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""
    
    def test_circuit_breaker_initialization(self):
        """Test CircuitBreaker initialization."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 60
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
    
    def test_circuit_breaker_as_decorator(self):
        """Test CircuitBreaker as decorator."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        @cb
        def test_function():
            return "success"
        
        # Should work normally
        result = test_function()
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
    
    def test_circuit_breaker_failure_handling(self):
        """Test CircuitBreaker failure handling."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        @cb
        def failing_function():
            raise Exception("Service failed")
        
        # First failure
        with pytest.raises(Exception):
            failing_function()
        assert cb.failure_count == 1
        assert cb.state == CircuitState.CLOSED
        
        # Second failure - should open circuit
        with pytest.raises(Exception):
            failing_function()
        assert cb.failure_count == 2
        assert cb.state == CircuitState.OPEN
    
    def test_circuit_breaker_open_state(self):
        """Test CircuitBreaker behavior in open state."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1)
        
        @cb
        def failing_function():
            raise Exception("Service failed")
        
        # Trigger failure to open circuit
        with pytest.raises(Exception):
            failing_function()
        
        assert cb.state == CircuitState.OPEN
        
        # Subsequent calls should fail fast
        with pytest.raises(Exception, match="Circuit breaker is open"):
            failing_function()
    
    def test_circuit_breaker_recovery(self):
        """Test CircuitBreaker recovery mechanism."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)  # Short timeout for testing
        
        @cb
        def recovering_function():
            if cb.state == CircuitState.HALF_OPEN:
                return "recovered"
            raise Exception("Service failed")
        
        # Trigger failure
        with pytest.raises(Exception):
            recovering_function()
        assert cb.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        time.sleep(0.2)
        
        # Next call should attempt recovery
        result = recovering_function()
        assert result == "recovered"
        assert cb.state == CircuitState.CLOSED
    
    def test_circuit_breaker_half_open_failure(self):
        """Test CircuitBreaker failure in half-open state."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        
        @cb
        def still_failing_function():
            raise Exception("Still failing")
        
        # Trigger failure to open circuit
        with pytest.raises(Exception):
            still_failing_function()
        
        # Wait for recovery timeout
        time.sleep(0.2)
        
        # Next call should fail and reopen circuit
        with pytest.raises(Exception):
            still_failing_function()
        assert cb.state == CircuitState.OPEN
    
    def test_circuit_breaker_success_reset(self):
        """Test CircuitBreaker success resets failure count."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        
        @cb
        def intermittent_function(should_fail=False):
            if should_fail:
                raise Exception("Failed")
            return "success"
        
        # One failure
        with pytest.raises(Exception):
            intermittent_function(should_fail=True)
        assert cb.failure_count == 1
        
        # Success should reset count
        result = intermittent_function(should_fail=False)
        assert result == "success"
        assert cb.failure_count == 0


class TestGracefulDegradation:
    """Test GracefulDegradation functionality."""
    
    def test_handle_service_failure_with_fallback(self):
        """Test graceful degradation with fallback function."""
        def fallback():
            return "fallback_result"
        
        result = GracefulDegradation.handle_service_failure(
            "test_service", 
            Exception("Service unavailable"), 
            fallback
        )
        
        assert result == "fallback_result"
    
    def test_handle_service_failure_without_fallback(self):
        """Test graceful degradation without fallback."""
        result = GracefulDegradation.handle_service_failure(
            "test_service", 
            Exception("Service unavailable")
        )
        
        assert result is None
    
    def test_handle_service_failure_logging(self):
        """Test that service failures are logged."""
        with patch('utils.error_handling.logger') as mock_logger:
            GracefulDegradation.handle_service_failure(
                "test_service", 
                Exception("Service unavailable")
            )
            
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args[0][0]
            assert "test_service" in call_args
            assert "Service unavailable" in call_args
    
    def test_is_service_available(self):
        """Test service availability checking."""
        # Mock a service check
        def mock_service_check():
            return True
        
        available = GracefulDegradation.is_service_available("test_service", mock_service_check)
        assert available is True
        
        def failing_service_check():
            raise Exception("Service down")
        
        available = GracefulDegradation.is_service_available("test_service", failing_service_check)
        assert available is False
    
    def test_retry_with_backoff(self):
        """Test retry mechanism with exponential backoff."""
        call_count = 0
        
        def failing_then_succeeding():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = GracefulDegradation.retry_with_backoff(
            failing_then_succeeding,
            max_retries=3,
            base_delay=0.01  # Short delay for testing
        )
        
        assert result == "success"
        assert call_count == 3
    
    def test_retry_with_backoff_max_retries_exceeded(self):
        """Test retry mechanism when max retries exceeded."""
        def always_failing():
            raise Exception("Always fails")
        
        with pytest.raises(Exception, match="Always fails"):
            GracefulDegradation.retry_with_backoff(
                always_failing,
                max_retries=2,
                base_delay=0.01
            )


class TestHealthChecks:
    """Test health check utilities."""
    
    @patch('core.db_import.db.session.execute')
    def test_check_database_health_success(self, mock_execute):
        """Test successful database health check."""
        mock_execute.return_value.scalar.return_value = 1
        
        result = check_database_health()
        
        assert result['status'] == 'healthy'
        assert result['service'] == 'database'
        assert 'response_time_ms' in result
        mock_execute.assert_called_once()
    
    @patch('core.db_import.db.session.execute')
    def test_check_database_health_failure(self, mock_execute):
        """Test database health check failure."""
        mock_execute.side_effect = Exception("Database connection failed")
        
        result = check_database_health()
        
        assert result['status'] == 'unhealthy'
        assert result['service'] == 'database'
        assert 'error' in result
        assert 'Database connection failed' in result['error']
    
    @patch('core.redis_client.redis_client')
    def test_check_redis_health_success(self, mock_redis):
        """Test successful Redis health check."""
        mock_redis.is_available.return_value = True
        mock_redis.get_client.return_value.ping.return_value = True
        
        result = check_redis_health()
        
        assert result['status'] == 'healthy'
        assert result['service'] == 'redis'
        assert 'response_time_ms' in result
    
    @patch('core.redis_client.redis_client')
    def test_check_redis_health_unavailable(self, mock_redis):
        """Test Redis health check when unavailable."""
        mock_redis.is_available.return_value = False
        
        result = check_redis_health()
        
        assert result['status'] == 'unhealthy'
        assert result['service'] == 'redis'
        assert 'error' in result
    
    @patch('core.redis_client.redis_client')
    def test_check_redis_health_failure(self, mock_redis):
        """Test Redis health check failure."""
        mock_redis.is_available.return_value = True
        mock_redis.get_client.return_value.ping.side_effect = Exception("Redis ping failed")
        
        result = check_redis_health()
        
        assert result['status'] == 'unhealthy'
        assert result['service'] == 'redis'
        assert 'error' in result
    
    @patch('utils.health_checks.check_database_health')
    @patch('utils.health_checks.check_redis_health')
    def test_check_system_health_all_healthy(self, mock_redis_health, mock_db_health):
        """Test system health check when all services healthy."""
        mock_db_health.return_value = {'status': 'healthy', 'service': 'database'}
        mock_redis_health.return_value = {'status': 'healthy', 'service': 'redis'}
        
        result = check_system_health()
        
        assert result['overall_status'] == 'healthy'
        assert len(result['services']) == 2
        assert all(service['status'] == 'healthy' for service in result['services'])
    
    @patch('utils.health_checks.check_database_health')
    @patch('utils.health_checks.check_redis_health')
    def test_check_system_health_partial_failure(self, mock_redis_health, mock_db_health):
        """Test system health check with partial service failure."""
        mock_db_health.return_value = {'status': 'healthy', 'service': 'database'}
        mock_redis_health.return_value = {'status': 'unhealthy', 'service': 'redis', 'error': 'Connection failed'}
        
        result = check_system_health()
        
        assert result['overall_status'] == 'degraded'
        assert len(result['services']) == 2
        assert result['healthy_services'] == 1
        assert result['unhealthy_services'] == 1
    
    def test_health_check_performance(self, performance_tracker):
        """Test health check performance."""
        performance_tracker.start('health_check')
        
        with patch('core.db_import.db.session.execute') as mock_execute:
            mock_execute.return_value.scalar.return_value = 1
            
            result = check_database_health()
        
        performance_tracker.stop()
        
        assert result['status'] == 'healthy'
        performance_tracker.assert_performance('health_check', 0.1)


class TestSessionHelpers:
    """Test session helper functions."""
    
    def test_get_session_firm_id_success(self):
        """Test successful firm ID retrieval from session."""
        with patch('flask.session', {'firm_id': 123}):
            firm_id = get_session_firm_id()
            assert firm_id == 123
    
    def test_get_session_firm_id_missing(self):
        """Test firm ID retrieval when not in session."""
        with patch('flask.session', {}):
            with patch('flask.request') as mock_request:
                mock_request.path = '/test/path'
                
                with pytest.raises(ValueError, match="No firm_id in session"):
                    get_session_firm_id()
    
    def test_get_session_user_id_success(self):
        """Test successful user ID retrieval from session."""
        with patch('flask.session', {'user_id': 456}):
            user_id = get_session_user_id()
            assert user_id == 456
    
    def test_get_session_user_id_missing(self):
        """Test user ID retrieval when not in session."""
        with patch('flask.session', {}):
            with patch('flask.request') as mock_request:
                mock_request.path = '/test/path'
                
                with pytest.raises(ValueError, match="No user_id in session"):
                    get_session_user_id()
    
    def test_session_helpers_error_context(self):
        """Test session helpers provide helpful error context."""
        with patch('flask.session', {'other_key': 'value'}):
            with patch('flask.request') as mock_request:
                mock_request.path = '/dashboard'
                
                with pytest.raises(ValueError) as exc_info:
                    get_session_firm_id()
                
                error_message = str(exc_info.value)
                assert 'Available session keys: [\'other_key\']' in error_message
                assert 'Request path: /dashboard' in error_message


class TestCoreUtilities:
    """Test core utility functions."""
    
    def test_format_currency(self):
        """Test currency formatting."""
        assert format_currency(1234.56) == "$1,234.56"
        assert format_currency(0) == "$0.00"
        assert format_currency(1000000) == "$1,000,000.00"
        assert format_currency(-500.25) == "-$500.25"
    
    def test_format_currency_none_handling(self):
        """Test currency formatting with None values."""
        assert format_currency(None) == "$0.00"
        assert format_currency("") == "$0.00"
    
    def test_format_date(self):
        """Test date formatting."""
        test_date = date(2024, 12, 25)
        assert format_date(test_date) == "2024-12-25"
        
        test_datetime = datetime(2024, 12, 25, 15, 30, 45)
        assert format_date(test_datetime) == "2024-12-25"
    
    def test_format_date_none_handling(self):
        """Test date formatting with None values."""
        assert format_date(None) == ""
        assert format_date("") == ""
    
    def test_format_date_custom_format(self):
        """Test date formatting with custom format."""
        test_date = date(2024, 12, 25)
        assert format_date(test_date, "%B %d, %Y") == "December 25, 2024"
        assert format_date(test_date, "%m/%d/%Y") == "12/25/2024"
    
    def test_calculate_business_days(self):
        """Test business days calculation."""
        start_date = date(2024, 1, 1)  # Monday
        end_date = date(2024, 1, 5)    # Friday
        
        business_days = calculate_business_days(start_date, end_date)
        assert business_days == 4  # Mon, Tue, Wed, Thu (not including end date)
    
    def test_calculate_business_days_with_weekend(self):
        """Test business days calculation spanning weekend."""
        start_date = date(2024, 1, 5)  # Friday
        end_date = date(2024, 1, 10)   # Wednesday
        
        business_days = calculate_business_days(start_date, end_date)
        assert business_days == 3  # Fri, Mon, Tue (not including end date)
    
    def test_calculate_business_days_same_date(self):
        """Test business days calculation for same date."""
        test_date = date(2024, 1, 1)
        
        business_days = calculate_business_days(test_date, test_date)
        assert business_days == 0
    
    def test_calculate_business_days_reverse_order(self):
        """Test business days calculation with reverse date order."""
        start_date = date(2024, 1, 10)
        end_date = date(2024, 1, 5)
        
        business_days = calculate_business_days(start_date, end_date)
        assert business_days == 0  # Should handle gracefully


class TestUtilityIntegration:
    """Test utility function integration scenarios."""
    
    def test_error_handling_with_health_checks(self):
        """Test error handling integration with health checks."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        
        @cb
        def health_check_function():
            # Simulate health check that might fail
            result = check_database_health()
            if result['status'] != 'healthy':
                raise Exception("Health check failed")
            return result
        
        # Mock successful health check
        with patch('core.db_import.db.session.execute') as mock_execute:
            mock_execute.return_value.scalar.return_value = 1
            
            result = health_check_function()
            assert result['status'] == 'healthy'
            assert cb.state == CircuitState.CLOSED
    
    def test_graceful_degradation_with_session_helpers(self):
        """Test graceful degradation with session helpers."""
        def get_session_data_with_fallback():
            try:
                return {
                    'firm_id': get_session_firm_id(),
                    'user_id': get_session_user_id()
                }
            except ValueError as e:
                return GracefulDegradation.handle_service_failure(
                    "session", e, lambda: {'firm_id': None, 'user_id': None}
                )
        
        # Test with missing session data
        with patch('flask.session', {}):
            with patch('flask.request') as mock_request:
                mock_request.path = '/test'
                
                result = get_session_data_with_fallback()
                assert result == {'firm_id': None, 'user_id': None}
    
    def test_performance_monitoring_utilities(self, performance_tracker):
        """Test performance monitoring of utility functions."""
        performance_tracker.start('utility_operations')
        
        # Test multiple utility operations
        format_currency(1234.56)
        format_date(date.today())
        calculate_business_days(date(2024, 1, 1), date(2024, 1, 10))
        
        performance_tracker.stop()
        performance_tracker.assert_performance('utility_operations', 0.01)  # Should be very fast
    
    def test_utility_error_resilience(self):
        """Test utility function resilience to invalid inputs."""
        # Currency formatting with invalid inputs
        assert format_currency("invalid") == "$0.00"
        assert format_currency([]) == "$0.00"
        
        # Date formatting with invalid inputs
        assert format_date("invalid") == ""
        assert format_date(123) == ""
        
        # Business days calculation with invalid inputs
        assert calculate_business_days(None, None) == 0
        assert calculate_business_days("invalid", "invalid") == 0