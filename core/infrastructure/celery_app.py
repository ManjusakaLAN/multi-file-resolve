# core/infrastructure/celery_app.py
from celery import Celery
from core.config import settings

celery_app = Celery(
    "multi_file_resolve",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# 关键：配置 Celery 自动去各个模块找任务
# 我们约定任务放在名为 tasks.py 的文件中
celery_app.autodiscover_tasks(["scheduler.tasks.celery_task"], force=True)

celery_app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone=settings.tz_info,
    enable_utc=True,
)