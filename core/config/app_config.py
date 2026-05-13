from datetime import timezone, timedelta
from typing import List

from typing import Literal

from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings

class LoggingConfig(BaseSettings):
    """
    应用程序日志配置
    """

    LOG_LEVEL: str = Field(
        description="日志级别，默认为 INFO。在生产环境中建议设置为 ERROR。",
        default="INFO",
    )

    LOG_OUTPUT_FORMAT: Literal["text", "json"] = Field(
        description="日志输出格式：'text' 为人类可读文本，'json' 为结构化 JSON 日志。",
        default="text",
    )

    LOG_FILE: str | None = Field(
        description="日志输出的文件路径。",
        default=None,
    )

    LOG_FILE_MAX_SIZE: PositiveInt = Field(
        description="日志文件轮转保留的最大文件大小，单位为兆字节 (MB)。",
        default=20,
    )

    LOG_FILE_BACKUP_COUNT: PositiveInt = Field(
        description="日志文件轮转保留的最大备份文件数量。",
        default=5,
    )

    LOG_FORMAT: str = Field(
        description="日志消息的格式化字符串。",
        default=(
            "%(asctime)s.%(msecs)03d %(levelname)s [%(threadName)s] "
            "[%(filename)s:%(lineno)d] %(trace_id)s - %(message)s"
        ),
    )

    LOG_DATEFORMAT: str | None = Field(
        description="日志时间戳的日期格式化字符串。",
        default=None,
    )

    LOG_TZ: str | None = Field(
        description="日志时间戳的时区（例如：'Asia/Shanghai' 或 'UTC'）。",
        default="UTC",
    )

class AppSettings(BaseSettings):
    # 项目名称
    PROJECT_NAME: str = "AI 一体化平台"
    # 服务器端口
    SERVER_PORT: int = 8500
    # 是否为调试模式
    DEBUG: bool = False
    # 默认 False，生产环境务必保持 False
    CLEAN_DB_ON_START: bool = False
    # 设置时区偏移量，例如东八区 (UTC+8)
    TIMEZONE_OFFSET: int = 8
    # CORS 跨域配置
    # 格式可以是字符串 "http://localhost:3000,https://example.com"
    CORS_ORIGINS: List[str] = ["*"]

    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v

    @property
    def tz_info(self):
        return timezone(timedelta(hours=self.TIMEZONE_OFFSET))
