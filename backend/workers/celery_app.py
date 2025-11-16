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
        "backend.workers.tasks.metrics",
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
    "backend.workers.tasks.metrics.*": {"queue": "metrics"},
}

if __name__ == "__main__":
    celery_app.start()
