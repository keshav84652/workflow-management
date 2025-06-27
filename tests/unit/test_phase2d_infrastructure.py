"""
Phase 2D Infrastructure Tests
Quick tests for circuit breakers, error handling, and health checks
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.error_handling import CircuitBreaker, CircuitState, GracefulDegradation
from utils.health_checks import check_database_health, check_redis_health


class TestPhase2DInfrastructure(unittest.TestCase):
    """Test Phase 2D infrastructure components"""
    
    def test_circuit_breaker_basic_functionality(self):
        """Test circuit breaker works as decorator"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        @cb
        def test_func():
            return "success"
        
        # Should work normally
        result = test_func()
        self.assertEqual(result, "success")
        self.assertEqual(cb.state, CircuitState.CLOSED)
    
    def test_graceful_degradation_fallback(self):
        """Test graceful degradation handles service failures"""
        def fallback():
            return "fallback_result"
        
        result = GracefulDegradation.handle_service_failure(
            "test_service", Exception("failed"), fallback
        )
        self.assertEqual(result, "fallback_result")
    
    @patch('core.db.session.execute')
    def test_database_health_check(self, mock_execute):
        """Test database health check works"""
        mock_execute.return_value.scalar.return_value = 1
        
        result = check_database_health()
        self.assertEqual(result['status'], 'healthy')
    
    @patch('core.redis_client.redis_client')
    def test_redis_health_check(self, mock_redis):
        """Test Redis health check works"""
        mock_redis.is_available.return_value = True
        mock_redis.get_client.return_value.ping.return_value = True
        
        result = check_redis_health()
        self.assertEqual(result['status'], 'healthy')


if __name__ == '__main__':
    unittest.main()