"""
Celery application configuration.
Handles async tasks like firmware building.
"""

from celery import Celery
from backend.core.config import settings

# Create Celery app
celery_app = Celery(
    "openmesh",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "backend.workers.tasks.firmware",
        "backend.workers.tasks.device_monitoring",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.BUILD_TIMEOUT_SECONDS,
    task_soft_time_limit=settings.BUILD_TIMEOUT_SECONDS - 60,
    result_expires=3600,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

# Task routes (can be expanded later)
celery_app.conf.task_routes = {
    "backend.workers.tasks.firmware.*": {"queue": "firmware"},
}

# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "check-offline-devices": {
        "task": "device_monitoring.check_offline_devices",
        "schedule": 60.0,  # Run every 60 seconds
        "options": {"expires": 55},  # Expire if not run within 55 seconds
    },
    # Optional: cleanup stale data weekly
    "cleanup-stale-data": {
        "task": "device_monitoring.cleanup_stale_data",
        "schedule": 604800.0,  # Run weekly (7 days in seconds)
        "args": (90,),  # Delete devices offline for 90+ days
    },
}

if __name__ == "__main__":
    celery_app.start()
