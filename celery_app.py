"""
Celery Configuration for CPA WorkflowPilot
Background task processing using Celery with Redis broker.
"""

import os
from celery import Celery
from datetime import timedelta

# Create Celery app
celery_app = Celery('workflow_management')

# Celery configuration
celery_app.conf.update(
    # Broker settings (Redis)
    broker_url=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/1'),
    result_backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1'),
    
    # Task routing
    task_routes={
        'workers.ai_worker.*': {'queue': 'ai_analysis'},
        'workers.document_worker.*': {'queue': 'document_processing'},
        'workers.notification_worker.*': {'queue': 'notifications'},
        'workers.system_worker.*': {'queue': 'system'},
    },
    
    # Task execution settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task result settings
    result_expires=3600,  # Results expire after 1 hour
    task_track_started=True,
    task_send_sent_event=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Task time limits
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes
    
    # Retry settings
    task_default_retry_delay=60,    # 1 minute
    task_max_retries=3,
    
    # Periodic tasks (if needed)
    beat_schedule={
        'process-recurring-tasks': {
            'task': 'workers.system_worker.process_recurring_tasks',
            'schedule': timedelta(hours=1),  # Run every hour
        },
        'cleanup-old-events': {
            'task': 'workers.system_worker.cleanup_old_events',
            'schedule': timedelta(days=1),   # Run daily
        },
        'health-check': {
            'task': 'workers.system_worker.system_health_check',
            'schedule': timedelta(minutes=15),  # Run every 15 minutes
        },
    },
    
    # Security settings
    worker_hijack_root_logger=False,
    worker_log_color=False,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Auto-discover tasks from workers modules
celery_app.autodiscover_tasks(['workers'])

# Task annotations for specific configurations
celery_app.conf.task_annotations = {
    'workers.ai_worker.analyze_document': {
        'rate_limit': '10/m',  # Max 10 AI analysis tasks per minute
        'time_limit': 300,     # 5 minutes max for AI analysis
        'soft_time_limit': 240, # 4 minutes soft limit
    },
    'workers.document_worker.process_large_document': {
        'rate_limit': '5/m',   # Max 5 large document processing per minute
        'time_limit': 600,     # 10 minutes max
    },
    'workers.notification_worker.send_email': {
        'rate_limit': '100/m', # Max 100 emails per minute
        'retry_backoff': True,
        'retry_jitter': True,
    },
}


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery functionality"""
    print(f'Request: {self.request!r}')
    return 'Debug task completed'


if __name__ == '__main__':
    celery_app.start()
