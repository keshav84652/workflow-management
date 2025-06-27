"""
Health Check Blueprint for CPA WorkflowPilot
Provides endpoints for system health monitoring.
"""

from flask import Blueprint, jsonify
from utils.health_checks import check_system_health
from core.db_import import db
    
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
