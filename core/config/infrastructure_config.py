from typing import Optional

from pydantic import computed_field
from pydantic_settings import BaseSettings
from urllib.parse import quote_plus, quote
from pydantic import Field


# --- 1. Mysql配置 ---
class MySQLSettings(BaseSettings):
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "123456"
    MYSQL_SERVER: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_DB: str = "my_fastapi_db"
    DB_LOG: bool = False

    @computed_field
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """动态生成异步连接串，并处理密码特殊字符"""
        pwd = quote_plus(self.MYSQL_PASSWORD)
        return f"mysql+aiomysql://{self.MYSQL_USER}:{pwd}@{self.MYSQL_SERVER}:{self.MYSQL_PORT}/{self.MYSQL_DB}"


# --- 2. Redis配置 ---
class RedisSettings(BaseSettings):
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0
    REDIS_ENCODING: str = "utf-8"

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            # 对密码进行转义，!@# 会变成 %21%40%23
            encoded_password = quote(self.REDIS_PASSWORD)
            auth = f":{encoded_password}@"
        else:
            auth = ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

# --- 3. Minio配置
class MinioConfig(BaseSettings):
    """
    Minio 对象存储配置
    """
    MINIO_ENDPOINT: str = Field(
        default="127.0.0.1:9000",
        description="Minio 访问地址 (示例: 192.168.18.32:9000)"
    )

    MINIO_BUCKET: str = Field(
        default="ai-all-in-one-bucket",
        description="项目使用的存储桶名称"
    )

    MINIO_ACCESS_KEY: str = Field(
        default="minio",
        description="访问通行 Key (用户名)"
    )

    MINIO_SECRET_KEY: str = Field(
        default="hxxc!@#1309",
        description="访问密钥 (密码)"
    )

    MINIO_HTTP_SECURE: bool = Field(
        default=False,
        description="是否使用 HTTPS 请求"
    )

    # 生产环境建议增加：连接超时配置
    MINIO_CONNECT_TIMEOUT: int = Field(default=10, description="连接超时时间(秒)")

    @computed_field
    @property
    def MINIO_URL(self) -> str:
        """
        自动生成 Minio 访问前缀，方便日志记录或第三方库使用
        """
        protocol = "https" if self.MINIO_HTTP_SECURE else "http"
        return f"{protocol}://{self.MINIO_ENDPOINT}"

# --- 3. Milvus配置
class MilvusSettings(BaseSettings):
    """Milvus 配置"""
    MILVUS_HOST: str = "127.0.0.1"
    MILVUS_PORT: str = "19530"
    MILVUS_USER: Optional[str] = None
    MILVUS_PASSWORD: Optional[str] = None
    MILVUS_DATABASE: str = "default"

    # 默认向量维度（根据你的模型调整，如 OpenAI 是 1536，HuggingFace 可能是 768）
    MILVUS_VECTOR_DIM: int = 1024

    @property
    def MILVUS_URI(self) -> str:
        return f"http://{self.MILVUS_HOST}:{self.MILVUS_PORT}"