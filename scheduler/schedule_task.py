import logging
from celery import shared_task
from core.infrastructure.celery_app import celery_app
logger = logging.getLogger(__name__)


# 关键点：name 必须和 beat_schedule 里的 "task" 字符串一模一样
@shared_task(name="scheduler.schedule_task.clean_embedding_cache_task")
def clean_embedding_cache_task():
    """
    定时清理嵌入缓存的任务
    """
    logger.info("开始执行定时任务：清理 Embedding 缓存...")

    try:
        # 这里编写你的业务逻辑，例如操作数据库或删除临时文件
        # from services.file_service import FileService
        # FileService.clear_cache()

        print("--- 正在清理过期缓存数据 ---")

        logger.info("定时任务执行成功。")
    except Exception as e:
        logger.error(f"定时任务执行失败: {str(e)}")
        # 如果需要重试，可以在这里逻辑处理