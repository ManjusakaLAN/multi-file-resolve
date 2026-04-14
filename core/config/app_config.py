from datetime import timezone, timedelta
from typing import List
from pydantic_settings import BaseSettings


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
