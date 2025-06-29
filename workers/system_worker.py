"""
System Worker for CPA WorkflowPilot
Background tasks for system maintenance and periodic operations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from celery_app import celery_app
from events.publisher import publish_event
from events.schemas import SystemHealthCheckEvent, ErrorEvent

logger = logging.getLogger(__name__)


@celery_app.task(name='workers.system_worker.process_recurring_tasks')
def process_recurring_tasks() -> Dict[str, Any]:
    """
    Process recurring tasks according to their schedules
    
    Returns:
        dict: Processing results
    """
    try:
        logger.info("Starting recurring task processing")
        
        # Import models and utilities (lazy import)
        from models.tasks import Task
        from utils.core import process_recurring_tasks as process_recurring
        from src.shared.database.db_import import db
        
        # Process recurring tasks using existing utility
        result = process_recurring()
        
        logger.info(f"Recurring task processing completed: {result.get('message', 'No details')}")
        
        return {
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'result': result
        }
        
    except Exception as e:
        logger.error(f"Error processing recurring tasks: {e}")
        
        # Publish error event
        error_event = ErrorEvent(
            error_type=type(e).__name__,
            error_message=str(e),
            context={'task_type': 'recurring_tasks'}
        )
        publish_event(error_event)
        
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(name='workers.system_worker.cleanup_old_events')
def cleanup_old_events() -> Dict[str, Any]:
    """
    Clean up old events and metadata from Redis
    
    Returns:
        dict: Cleanup results
    """
    try:
        logger.info("Starting old event cleanup")
        
        from core.redis_client import redis_client
        
        if not redis_client or not redis_client.is_available():
            logger.warning("Redis not available for event cleanup")
            return {
                'success': False,
                'error': 'Redis not available',
                'timestamp': datetime.utcnow().isoformat()
            }
        
        client = redis_client.get_client()
        if not client:
            return {
                'success': False,
                'error': 'Could not get Redis client',
                'timestamp': datetime.utcnow().isoformat()
            }
        
        # Clean up old event metadata (older than 7 days)
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d')
        
        # Clean up old event counters
        counter_pattern = f"event_counter:*"
        deleted_counters = 0
        
        for key in client.scan_iter(match=counter_pattern):
            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
            # Extract date from key (format: event_counter:EventType:YYYY-MM-DD)
            parts = key_str.split(':')
            if len(parts) >= 3:
                key_date = parts[2]
                if key_date < cutoff_str:
                    client.delete(key)
                    deleted_counters += 1
        
        # Clean up old event metadata
        metadata_pattern = f"event_metadata:*"
        deleted_metadata = 0
        
        for key in client.scan_iter(match=metadata_pattern):
            # Check if key has expired naturally first
            ttl = client.ttl(key)
            if ttl == -1:  # No expiration set, manually check age
                try:
                    metadata = client.get(key)
                    if metadata:
                        import json
                        data = json.loads(metadata)
                        published_at = datetime.fromisoformat(data.get('published_at', ''))
                        if published_at < cutoff_date:
                            client.delete(key)
                            deleted_metadata += 1
                except (json.JSONDecodeError, ValueError, KeyError):
                    # If we can't parse the metadata, delete it
                    client.delete(key)
                    deleted_metadata += 1
        
        logger.info(f"Cleaned up {deleted_counters} old event counters and {deleted_metadata} old metadata entries")
        
        return {
            'success': True,
            'deleted_counters': deleted_counters,
            'deleted_metadata': deleted_metadata,
            'cutoff_date': cutoff_str,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up old events: {e}")
        
        # Publish error event
        error_event = ErrorEvent(
            error_type=type(e).__name__,
            error_message=str(e),
            context={'task_type': 'cleanup_old_events'}
        )
        publish_event(error_event)
        
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(name='workers.system_worker.system_health_check')
def system_health_check() -> Dict[str, Any]:
    """
    Perform system health check and publish health events
    
    Returns:
        dict: Health check results
    """
    try:
        logger.info("Starting system health check")
        
        # Check database health
        db_health = _check_database_health()
        
        # Check Redis health
        redis_health = _check_redis_health()
        
        # Check event system health
        event_health = _check_event_system_health()
        
        # Overall status
        overall_status = 'healthy'
        if any(check['status'] == 'error' for check in [db_health, redis_health, event_health]):
            overall_status = 'error'
        elif any(check['status'] == 'warning' for check in [db_health, redis_health, event_health]):
            overall_status = 'warning'
        
        # Publish health check event
        health_event = SystemHealthCheckEvent(
            component_name='system_overall',
            status=overall_status,
            metrics={
                'database': db_health,
                'redis': redis_health,
                'events': event_health
            },
            check_time=datetime.utcnow()
        )
        publish_event(health_event)
        
        logger.info(f"System health check completed: {overall_status}")
        
        return {
            'success': True,
            'overall_status': overall_status,
            'components': {
                'database': db_health,
                'redis': redis_health,
                'events': event_health
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in system health check: {e}")
        
        # Publish error event
        error_event = ErrorEvent(
            error_type=type(e).__name__,
            error_message=str(e),
            context={'task_type': 'system_health_check'}
        )
        publish_event(error_event)
        
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


def _check_database_health() -> Dict[str, Any]:
    """Check database connectivity and basic metrics"""
    try:
        from src.shared.database.db_import import db
        from models.auth import Firm, User
        from models.tasks import Task
        from models.projects import Project
        
        # Test basic query
        firm_count = Firm.query.count()
        user_count = User.query.count()
        task_count = Task.query.count()
        project_count = Project.query.count()
        
        return {
            'status': 'healthy',
            'metrics': {
                'firms': firm_count,
                'users': user_count,
                'tasks': task_count,
                'projects': project_count
            },
            'message': 'Database queries successful'
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'message': 'Database connection failed'
        }


def _check_redis_health() -> Dict[str, Any]:
    """Check Redis connectivity and metrics"""
    try:
        from core.redis_client import redis_client
        
        if not redis_client:
            return {
                'status': 'warning',
                'message': 'Redis client not initialized'
            }
        
        return redis_client.health_check()
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'message': 'Redis health check failed'
        }


def _check_event_system_health() -> Dict[str, Any]:
    """Check event system health"""
    try:
        from events.publisher import event_publisher
        from events.subscriber import event_subscriber
        
        publisher_health = event_publisher.health_check() if event_publisher else {
            'status': 'warning', 'message': 'Publisher not initialized'
        }
        
        subscriber_health = event_subscriber.health_check() if event_subscriber else {
            'status': 'warning', 'message': 'Subscriber not initialized'
        }
        
        # Determine overall event system status
        if (publisher_health['status'] == 'healthy' and 
            subscriber_health['status'] in ['healthy', 'warning']):
            status = 'healthy'
        elif publisher_health['status'] in ['healthy', 'degraded']:
            status = 'warning'
        else:
            status = 'error'
        
        return {
            'status': status,
            'publisher': publisher_health,
            'subscriber': subscriber_health,
            'message': f'Event system status: {status}'
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'message': 'Event system health check failed'
        }


@celery_app.task(name='workers.system_worker.backup_database')
def backup_database() -> Dict[str, Any]:
    """
    Create a database backup
    
    Returns:
        dict: Backup results
    """
    try:
        logger.info("Starting database backup")
        
        import os
        import shutil
        from pathlib import Path
        
        # Source database path
        db_path = Path('instance/workflow.db')
        if not db_path.exists():
            raise FileNotFoundError("Database file not found")
        
        # Create backup directory
        backup_dir = Path('backups')
        backup_dir.mkdir(exist_ok=True)
        
        # Create backup filename with timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"workflow_backup_{timestamp}.db"
        backup_path = backup_dir / backup_filename
        
        # Copy database file
        shutil.copy2(db_path, backup_path)
        
        # Get file size
        file_size = backup_path.stat().st_size
        
        # Publish backup event
        from events.schemas import BackupCreatedEvent
        backup_event = BackupCreatedEvent(
            backup_id=backup_filename,
            backup_type='database',
            file_size_bytes=file_size,
            backup_location=str(backup_path.absolute())
        )
        publish_event(backup_event)
        
        logger.info(f"Database backup created: {backup_path}")
        
        return {
            'success': True,
            'backup_file': str(backup_path),
            'file_size_bytes': file_size,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating database backup: {e}")
        
        # Publish error event
        error_event = ErrorEvent(
            error_type=type(e).__name__,
            error_message=str(e),
            context={'task_type': 'database_backup'}
        )
        publish_event(error_event)
        
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }
