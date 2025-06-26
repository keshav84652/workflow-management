"""
Health Check Utilities for CPA WorkflowPilot
Facilitates system checks for database, Redis, and external services.
"""

from datetime import datetime
from typing import Dict, Any


def check_database_health() -> Dict[str, Any]:
    """Check database connectivity and return status"""
    try:
        # Import db here to avoid circular imports
        import importlib.util
        import os

        # Import db from root core.py file
        spec = importlib.util.spec_from_file_location("core", os.path.join(os.path.dirname(os.path.dirname(__file__)), "core.py"))
        core_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(core_module)
        db = core_module.db
        
        # Attempt a simple database query
        result = db.session.execute('SELECT 1').scalar()
        if result == 1:
            return {'status': 'healthy', 'message': 'Database connection successful'}
        else:
            return {'status': 'error', 'message': 'Unexpected database response'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def check_redis_health() -> Dict[str, Any]:
    """Check Redis connectivity and return status"""
    try:
        # Import redis_client here to avoid circular imports
        from core.redis_client import redis_client
        
        if not redis_client or not redis_client.is_available():
            return {'status': 'error', 'message': 'Redis not available'}

        # Ping Redis
        redis_client.get_client().ping()
        return {'status': 'healthy', 'message': 'Redis connection successful'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def check_system_health() -> Dict[str, Any]:
    """Perform comprehensive system health check"""
    db_health = check_database_health()
    redis_health = check_redis_health()

    # Overall system health is degraded if any single component is in error
    overall_status = 'healthy'
    if db_health['status'] == 'error' or redis_health['status'] == 'error':
        overall_status = 'degraded'

    return {
        'status': overall_status,
        'database': db_health,
        'redis': redis_health,
        'timestamp': datetime.utcnow().isoformat()
    }
