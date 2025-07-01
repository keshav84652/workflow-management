"""
Health Check Blueprint for CPA WorkflowPilot
Provides endpoints for system health monitoring.
"""

from flask import Blueprint, jsonify
from utils.health_checks import check_system_health

health_bp = Blueprint('health', __name__, url_prefix='/health')


@health_bp.route('/database')
def database_health():
    """Check database connection health"""
    try:
        # Use the health check utility instead of direct db access
        health_status = check_system_health()
        
        if health_status.get('database', {}).get('status') == 'healthy':
            return jsonify({
                'status': 'healthy',
                'message': 'Database connection successful'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Database connection failed'
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


@health_bp.route('/')
def overall_health():
    """Check overall system health"""
    try:
        health_status = check_system_health()
        
        # Determine overall status
        all_healthy = all(
            component.get('status') == 'healthy' 
            for component in health_status.values()
        )
        
        return jsonify({
            'status': 'healthy' if all_healthy else 'degraded',
            'components': health_status
        }), 200 if all_healthy else 503
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 503
