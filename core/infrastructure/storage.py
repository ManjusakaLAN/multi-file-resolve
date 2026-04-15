import logging
from typing import Optional, Any
from minio import Minio
from core.config import settings

logger = logging.getLogger(__name__)


class MinioClient:
    def __init__(self):
        self._client: Optional[Minio] = None

    def init_client(self):
        """
        同步初始化方法，在 lifespan 启动时调用
        """
        try:
            self._client = Minio(
                endpoint=settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_HTTP_SECURE
            )
            self._ensure_bucket_exists()
            logger.info(f"MinIO 客户端同步初始化成功: {settings.MINIO_URL}")
        except Exception as e:
            logger.error(f"MinIO 初始化失败: {e}")
            raise e

    def _ensure_bucket_exists(self):
        """确保存储桶存在"""
        bucket_name = settings.MINIO_BUCKET
        if not self._client.bucket_exists(bucket_name):
            self._client.make_bucket(bucket_name)
            logger.info(f"MinIO 自动创建存储桶: {bucket_name}")
        else:
            logger.info(f"MinIO 存储桶已就绪: {bucket_name}")

    def upload_file(self, object_name: str, data: Any, length: int, content_type: str = "application/octet-stream"):
        """
        上传文件
        :param content_type:
        :param length:
        :param object_name:
        :param data: 可以是字节流对象（如 BytesIO）或文件句柄
        """
        return self._client.put_object(
            settings.MINIO_BUCKET,
            object_name,
            data,
            length,
            content_type
        )

    def download_file(self, object_name: str):
        """
        下载文件
        :return: urllib3.response.HTTPResponse 对象
        """
        return self._client.get_object(
            settings.MINIO_BUCKET,
            object_name
        )

    def delete_file(self, object_name: str):
        """
        删除文件
        """
        return self._client.remove_object(
            settings.MINIO_BUCKET,
            object_name
        )

    def exists(self, object_name: str) -> bool:
        """
        判断文件是否存在
        """
        try:
            self._client.stat_object(settings.MINIO_BUCKET, object_name)
            return True
        except Exception as e:
            logger.warning(f"文件不存在: {object_name} {e}")
            return False
