import logging
import shutil
from uuid import uuid4
from typing import List, Optional, Any, Coroutine, Sequence, Tuple

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from models.file_task import FileRecognizeTask  # 请确保导入路径正确
from util.db_util import paginate
from util.file_util import get_file_md5, convert_with_libreoffice, get_pdf_page_count, storage_file
from util.path_util import get_workspace_path

logger = logging.getLogger(__name__)

class FileService:
    def __init__(self, db: AsyncSession):
        self.db = db


    async def create_task(self, file: UploadFile) -> FileRecognizeTask:

        md5 = await get_file_md5(file)
        # 查询是否以及解析过相同内容的文件 如果有那么直接返回结果

        """创建一个新的识别任务"""
        recognize_task = FileRecognizeTask(
            file_name=file.filename,
            md5=md5,
        )
        self.db.add(recognize_task)
        await self.db.commit()      # 提交到数据库

        # 获取任务id
        task_id = recognize_task.id
        # 创建两个目录 存放文件
        temp_workspace = get_workspace_path() / "temp" / task_id
        result_workspace = get_workspace_path() / "result" / task_id
        # 如果没有这两个目录 递归创建
        temp_workspace.mkdir(parents=True, exist_ok=True)
        result_workspace.mkdir(parents=True, exist_ok=True)

        # 上传的文件写入到 temp_workspace 目录下
        file_path =storage_file(file,temp_workspace)
        # 4. 写入文件

        return None

    # --- 查 (Read) ---
    async def get_task_by_id(self, task_id: str) -> Optional[FileRecognizeTask]:
        """根据 ID 获取单个任务"""
        result = await self.db.execute(select(FileRecognizeTask).where(FileRecognizeTask.id == task_id))
        return result.scalars().first()

    async def get_tasks_paged(self, file_name: str = None, page: int = 1, page_size: int = 10):
        # 过滤条件就像你写的那样
        query = select(FileRecognizeTask).where(FileRecognizeTask.status != 'failed')
        if file_name:
            query = query.where(FileRecognizeTask.file_name.ilike(f"%{file_name}%"))

        # 排序
        query = query.order_by(FileRecognizeTask.created_at.desc())

        # 一行调用
        items, total = await paginate(self.db, query, page, page_size)
        return items, total

    # --- 改 (Update) ---
    async def update_task_progress(self, task_id: str, progress: str, status: str = "resolving") -> Optional[FileRecognizeTask]:
        """更新任务进度和状态"""
        stmt = (
            update(FileRecognizeTask)
            .where(FileRecognizeTask.id == task_id)
            .values(progress=progress, status=status)
            .execution_options(synchronize_session="fetch")
        )
        await self.db.execute(stmt)
        await self.db.commit()
        return await self.get_task_by_id(task_id)

    async def finish_task(self, task_id: str, md_location: str) -> bool:
        """标记任务为完成并保存文件路径"""
        stmt = (
            update(FileRecognizeTask)
            .where(FileRecognizeTask.id == task_id)
            .values(status="finish", progress="100%", md_location=md_location)
        )
        await self.db.execute(stmt)
        await self.db.commit()
        return True

    # --- 删 (Delete) ---
    async def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        stmt = delete(FileRecognizeTask).where(FileRecognizeTask.id == task_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0  # 返回是否成功删除（行数 > 0）