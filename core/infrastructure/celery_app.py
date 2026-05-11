from datetime import timedelta
from celery import Celery
from core.config import settings

celery_app = Celery(
    "multi_file_resolve",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    result_backend=settings.CELERY_RESULT_BACKEND,
    broker_connection_retry_on_startup=True,
    # worker_log_format=settings.LOG_FORMAT,
    # worker_task_log_format=settings.LOG_FORMAT,
    timezone=settings.tz_info,
    enable_utc=True,
)

imports = [
    "tasks.celery_task",
    "scheduler.schedule_task",
]

beat_schedule = {"clean_embedding_cache_task": {
    "task": "scheduler.schedule_task.clean_embedding_cache_task",
    "schedule": timedelta(seconds=10)
}}

celery_app.conf.update(
    beat_schedule=beat_schedule,
    imports=imports
)
