
import time

from celery import shared_task

@shared_task(name="scheduler.tasks.resolve_file_task")
def resolve_file_task(file_id: str):
    """
    模拟耗时的文件识别任务
    """
    print(f"--- 开始异步识别文件: {file_id} ---")
    time.sleep(10)  # 模拟解析耗时
    print(f"--- 文件 {file_id} 识别完成 ---")
    return {"status": "success", "file_id": file_id}