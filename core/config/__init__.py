from pydantic_settings import SettingsConfigDict

from core.config.app_config import AppSettings
from core.config.infrastructure_config import MySQLSettings


class Settings(
    MySQLSettings,
    AppSettings
):
    # 统一管理 .env 加载
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # 允许 .env 有多余字段不报错
        case_sensitive=True  # 区分大小写（可选）
    )


# 实例化全局单例
settings = Settings()
