from datetime import timezone, timedelta

from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    PROJECT_NAME: str = "My FastAPI Project"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True
    CLEAN_DB_ON_START: bool = False  # 默认 False，生产环境务必保持 False
    # 设置时区偏移量，例如东八区 (UTC+8)
    TIMEZONE_OFFSET: int = 8

    # 应该定义这个属性
    @property
    def tz_info(self):
        return timezone(timedelta(hours=self.TIMEZONE_OFFSET))
