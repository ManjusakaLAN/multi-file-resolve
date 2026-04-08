import os
from typing import Tuple
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.config.app_config import AppSettings
from core.config.file_config import FileUploadSettings
from core.config.infrastructure_config import MySQLSettings, RedisSettings,MinioConfig
from core.config.web_config import AuthSettings, SecuritySettings


def get_env_files() -> Tuple[str, ...]:
    """
    动态获取环境配置文件列表
    1. 始终包含基础的 .env
    2. 如果设置了 APP_ENV，则追加对应的环境文件 (如 .env.prod)
    """
    app_env = os.getenv("APP_ENV", "").strip().lower()
    env_files = [".env"]

    if app_env:
        env_files.append(f".env.{app_env}")

    return tuple(env_files)


class Settings(
    MySQLSettings,
    RedisSettings,
    MinioConfig,
    AppSettings,
    AuthSettings,
    SecuritySettings,
    FileUploadSettings,
    BaseSettings  # 确保继承了 BaseSettings
):
    # 统一管理 .env 加载
    model_config = SettingsConfigDict(
        # 调用函数动态生成元组：(".env",) 或 (".env", ".env.prod")
        env_file=get_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )


# 实例化全局单例
settings = Settings()