"""
Celery configuration for O11CE Stock B2B project.
"""
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('bff')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat schedule configuration
app.conf.beat_schedule = {
    'scan-near-expiry-products': {
        'task': 'apps.stock.tasks.scan_near_expiry',
        'schedule': 3600.0,  # Every hour
        'options': {'queue': 'stock'}
    },
    'scan-low-stock-products': {
        'task': 'apps.stock.tasks.scan_low_stock',
        'schedule': 1800.0,  # Every 30 minutes
        'options': {'queue': 'stock'}
    },
}

# Task configuration with fault tolerance
app.conf.update(
    # Retry configuration
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Task routing
    task_routes={
        'apps.notifications.tasks.*': {'queue': 'notifications'},
        'apps.stock.tasks.*': {'queue': 'stock'},
    },
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    
    # Time limits
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,  # 10 minutes
    
    # Serialization
    accept_content=['json'],
    task_serializer='json',
    result_serializer='json',
    timezone=settings.TIME_ZONE,
)


# Timezone
app.conf.timezone = 'UTC'

# Celery Beat Schedule - Scheduled Tasks
app.conf.beat_schedule = {
    'scan-near-expiry': {
        'task': 'apps.stock.tasks.scan_near_expiry',
        'schedule': 3600.0,  # Every hour
        'args': (7,),  # 7 days ahead warning
        'options': {
            'queue': 'stock_queue',
            'routing_key': 'stock.scan_expiry',
        }
    },
    'scan-low-stock': {
        'task': 'apps.stock.tasks.scan_low_stock',
        'schedule': 1800.0,  # Every 30 minutes
        'args': (10.0,),  # Alert when stock below 10 units
        'options': {
            'queue': 'stock_queue',
            'routing_key': 'stock.scan_low',
        }
    },
    'cleanup-expired-lots': {
        'task': 'apps.stock.tasks.cleanup_expired_lots',
        'schedule': 86400.0,  # Daily at midnight
        'options': {
            'queue': 'maintenance_queue',
            'routing_key': 'maintenance.cleanup',
        }
    },
    'update-stock-metrics': {
        'task': 'apps.stock.tasks.update_stock_metrics',
        'schedule': 900.0,  # Every 15 minutes
        'options': {
            'queue': 'metrics_queue',
            'routing_key': 'metrics.stock',
        }
    },
}

# Debug task for testing
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
    return 'Debug task completed successfully'