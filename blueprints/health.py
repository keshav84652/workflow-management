"""
Health Check Blueprint for CPA WorkflowPilot
Provides endpoints for system health monitoring.
"""

from flask import Blueprint, jsonify
from utils.health_checks import check_system_health

health_bp = Blueprint('health', __name__, url_prefix='/health')


@health_bp.route('/check')
def health_check():
    """Perform system health check"""
    health_status = check_system_health()
    return jsonify(health_status), 200 if health_status['status'] == 'healthy' else 503


@health_bp.route('/redis')
def redis_health():
    """Check Redis connectivity"""
    from core.redis_client import redis_client
    
    if not redis_client or not redis_client.is_available():
        return jsonify({
            'status': 'error',
            'message': 'Redis not available'
        }), 503
    
    try:
        redis_client.get_client().ping()
        return jsonify({
            'status': 'healthy',
            'message': 'Redis connection successful'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 503


@health_bp.route('/database')
def database_health():
    """Check database connectivity"""
import importlib.util
import os

# Import db from root core.py file
spec = importlib.util.spec_from_file_location("core", os.path.join(os.path.dirname(os.path.dirname(__file__)), "core.py"))
core_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core_module)
db = core_module.db
    
    try:
        result = db.session.execute('SELECT 1').scalar()
        if result == 1:
            return jsonify({
                'status': 'healthy',
                'message': 'Database connection successful'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Unexpected database response'
            }), 503
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 503


@health_bp.route('/celery')
def celery_health():
    """Check Celery worker status"""
    from celery_app import celery_app
    
    try:
        # Check if workers are responsive
        inspection = celery_app.control.inspect()
        active_workers = inspection.active()
        
        if not active_workers:
            return jsonify({
                'status': 'error',
                'message': 'No Celery workers active'
            }), 503
        
        # Get worker stats
        stats = inspection.stats()
        registered_tasks = inspection.registered()
        
        return jsonify({
            'status': 'healthy',
            'message': 'Celery workers active',
            'active_workers': len(active_workers),
            'stats': stats,
            'registered_tasks': registered_tasks
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 503
