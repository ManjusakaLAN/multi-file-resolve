import logging
from pathlib import Path

from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from core.config import settings
from core.enum.kb import AnalysisStatus
from core.infrastructure.celery_app import celery_app
from celery import shared_task

from core.infrastructure.database import AsyncSessionLocal
from core.infrastructure.storage import MinioClient
from models.file import FileRecord
from models.knowledge import FileResolveTask
from util import file_util, ocr_util

logger = logging.getLogger(__name__)

@shared_task(name="file_resolve_task")
async def file_resolve_task(task_id: str, minio_client: MinioClient):
    async with AsyncSessionLocal() as db:

        task = (await db.execute(select(FileResolveTask).where(FileResolveTask.id == task_id))).scalars().first()
        if task is None:
            return

        base_dir = Path.cwd()
        task_dir = base_dir / "temp" / f"ocr_{task.id}"
        task_dir_input = task_dir / "input"
        task_dir_output = task_dir / "output"

        source_file_path = task_dir_input / task.file_name
        # 准确定位生成的 PDF 路径
        pdf_path = task_dir_output / f"{source_file_path.stem}.pdf"

        # 创建所有文件夹
        task_dir.mkdir(parents=True, exist_ok=True)
        task_dir_input.mkdir(parents=True, exist_ok=True)
        task_dir_output.mkdir(parents=True, exist_ok=True)

        file_info = (await db.execute(select(FileRecord).where(FileRecord.file_key == task.file_key))).scalars().first()
        if file_info is None:
            task.analysis_status = AnalysisStatus.FAILED
            await db.commit()
            return

        # 如果是pdf则直接下载到output 用户后续ocr识别即可
        if file_info.name.endswith(".pdf"):
            if not pdf_path.exists():
                # 文件转换状态
                task.analysis_status = AnalysisStatus.CONVERT
                await db.commit()
                await run_in_threadpool(
                    minio_client.download,  # 确保你的 minio_client 有此方法
                    object_name=task.file_key,
                    target_filepath=str(pdf_path)
                )
        else:
            # 如果源文件没下载，则进行下载
            if not source_file_path.exists():
                await run_in_threadpool(
                    minio_client.download,  # 确保你的 minio_client 有此方法
                    object_name=task.file_key,
                    target_filepath=str(source_file_path)
                )

        # 执行文件转换 (LibreOffice -> PDF) 如果没有则进行转换
        if not pdf_path.exists():
            # 文件转换状态
            task.analysis_status = AnalysisStatus.CONVERT
            await db.commit()
            await run_in_threadpool(file_util.convert_with_libreoffice, str(source_file_path), str(task_dir_output))

        # 拿到md文件路径
        md_path = task.md_file_path
        if md_path is None:
            # 文件OCR识别
            task.analysis_status = AnalysisStatus.OCR_RESOLVE
            await db.commit()
            logger.info(f"开始执行文件{file_info.name}的OCR识别任务")
            md_path = await ocr_util.invoke_mineru_to_markdown(
                file_path=str(pdf_path),
                save_directory=str(task_dir_output),
                api_url=settings.MINERU_API_URL
            )
            logger.info(f"文件{file_info.name}的OCR识别任务执行完成")
            task.md_file_path = md_path
            await db.commit()