import hashlib
import logging
import re
import os
import time
import uuid
from io import BytesIO
from sqlalchemy import select
from fastapi import UploadFile, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse
from urllib.parse import quote
from core.config import settings
from models.file import FileRecord
from core.infrastructure.storage import MinioClient

logger = logging.getLogger(__name__)


def _get_human_size(size: int) -> str:
    """字节单位转换逻辑"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f}{unit}"
        size /= 1024.0
    return f"{size:.2f}PB"


class FileService:
    def __init__(self, db: AsyncSession, minio_client: MinioClient):
        self.db = db
        self.minio_client = minio_client

    async def upload_file(self, file: UploadFile, user_id: str) -> FileRecord:
        """
        处理文件上传：包含大小拦截、流式MD5计算、秒传及存储
        """
        # 尝试从 Header 获取大小进行初步拦截
        if file.size and file.size > settings.MAX_UPLOAD_SIZE * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"文件过大，最大允许 {settings.MAX_UPLOAD_SIZE}MB (当前: {file.size / 1024 / 1024:.2f}MB)"
            )

        # 2. 流式计算 MD5 并二次校验大小
        md5_obj = hashlib.md5()
        file_size = 0
        chunks = []  # 用于临时存放数据，避免多次调用 seek(0)

        # 分块读取：每次读 1MB
        while chunk := await file.read(1024 * 1024):
            file_size += len(chunk)
            if file_size > settings.MAX_UPLOAD_SIZE * 1024 * 1024:
                await file.close()
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="文件内容超过 50MB 限制"
                )
            md5_obj.update(chunk)
            chunks.append(chunk)

        final_md5 = md5_obj.hexdigest()

        # 3. 秒传校验
        stmt = select(FileRecord).where(FileRecord.md5.__eq__(final_md5))
        result = await self.db.execute(stmt)
        existing_file = result.scalar_one_or_none()

        if existing_file:
            logger.info(f"触发秒传：{existing_file.name} (MD5: {final_md5})")
            return existing_file

        # 4. 文件名清洗与截断 判断文件名称是否包含特殊字符 有的话去除 "/", "\\", ":", "*", "?", '"', "<", ">", "|"]
        original_name = file.filename or "unnamed_file"
        base_name, extension = os.path.splitext(original_name)
        # 判断文件名称是否包含特殊字符 有的话去除 "/", "\\", ":", "*", "?", '"', "<", ">", "|"]
        clean_name = re.sub(r'[/\\:*?"<>|]', '', base_name)
        if len(clean_name) > 200:
            clean_name = clean_name[:200]
            # 去除空格
            clean_name = clean_name.replace(" ", "")
        final_filename = f"{clean_name}{extension}"

        # 5. 生成存储路径
        now = time.localtime()
        timestamp = f"{now.tm_year}_{now.tm_mon:02d}"  # 补零格式化: 2026_04
        storage_key = f"general/{timestamp}/{uuid.uuid4().hex}_{final_filename}"

        # 6. 上传到 MinIO
        # 将刚才读取的 chunks 合并为 BytesIO 给同步驱动使用
        full_content = b"".join(chunks)
        data_stream = BytesIO(full_content)

        await run_in_threadpool(
            self.minio_client.upload_file,
            object_name=storage_key,
            data=data_stream,
            length=file_size,
            content_type=file.content_type or "application/octet-stream"
        )

        # 7. 记录数据库
        new_file_record = FileRecord(
            file_key=storage_key,
            name=final_filename,
            size=file_size,
            extension=extension.lstrip('.').lower(),
            mime_type=file.content_type,
            md5=final_md5,
            created_by=user_id
        )

        self.db.add(new_file_record)
        await self.db.commit()
        await self.db.refresh(new_file_record)

        return new_file_record

    async def download_file(self, file_key: str):
        """
        文件下载
        :param file_key:
        :return:
        """
        # 1. 从数据库获取文件原始名称，用于下载时的文件名显示
        stmt = select(FileRecord).where(FileRecord.file_key.__eq__(file_key))
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            raise HTTPException(status_code=404, detail="文件记录不存在")

        try:
            # 2. 调用同步 Minio 客户端获取对象流
            # run_in_threadpool 确保同步 IO 不阻塞事件循环
            response = await run_in_threadpool(self.minio_client.download_file, file_key)

            # 3. 构造流式响应
            # 使用生成器逐步读取 MinIO 流，防止大文件撑爆内存
            def iter_file():
                try:
                    yield from response.stream(amt=1024 * 1024)  # 每次读取 1MB
                finally:
                    response.close()
                    response.release_conn()

            # 4. 处理中文件名下载乱码 (RFC 5987 标准)
            # 这样前端下载时，文件名会显示为 record.name 而不是随机的 key
            filename_utf8 = quote(record.name)
            headers = {
                'Content-Disposition': f"attachment; filename*=utf-8''{filename_utf8}"
            }

            return StreamingResponse(
                iter_file(),
                media_type=record.mime_type or "application/octet-stream",
                headers=headers
            )

        except Exception as e:
            logger.error(f"下载文件失败: {e}")
            raise HTTPException(status_code=500, detail="从存储服务器获取文件失败")

    async def delete_file(self, file_id: str) -> bool:
        """
        删除文件：包含数据库记录移除与 MinIO 物理存储清理
        :param file_id: 数据库中的文件 ID (UUID 或自增 ID)
        """
        # 1. 查询数据库获取记录
        stmt = select(FileRecord).where(FileRecord.id == file_id)
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            logger.warning(f"删除失败：未找到 ID 为 {file_id} 的文件记录")
            return False

        file_key = record.file_key

        try:
            # 2. 检查是否有其他记录也指向同一个物理文件 (秒传场景下的安全保护)
            # 如果你的逻辑是每个记录对应唯一物理文件，可跳过此步直接删除
            duplicate_stmt = select(FileRecord).where(
                FileRecord.file_key == file_key,
                FileRecord.id != file_id
            )
            duplicate_result = await self.db.execute(duplicate_stmt)
            other_ref = duplicate_result.first()

            # 3. 物理删除：如果没有其他记录引用此 key，则从 MinIO 删除
            if not other_ref:
                await run_in_threadpool(
                    self.minio_client.delete_file,  # 确保你的 minio_client 有此方法
                    object_name=file_key
                )
                logger.info(f"物理文件已从存储删除: {file_key}")
            else:
                logger.info(f"物理文件仍有其他引用，仅删除数据库记录: {file_key}")

            # 4. 删除数据库记录
            await self.db.delete(record)
            await self.db.commit()

            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"删除文件任务失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"文件删除过程中发生错误: {str(e)}"
            )
