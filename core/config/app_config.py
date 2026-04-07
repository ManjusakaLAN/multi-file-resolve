from datetime import timezone, timedelta

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

    @property
    def tz_info(self):
        return timezone(timedelta(hours=self.TIMEZONE_OFFSET))
