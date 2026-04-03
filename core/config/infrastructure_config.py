import os
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import quote_plus


# --- 1. 数据库专项配置 ---
class MySQLSettings(BaseSettings):
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "123456"
    MYSQL_SERVER: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_DB: str = "my_fastapi_db"

    @computed_field
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """动态生成异步连接串，并处理密码特殊字符"""
        pwd = quote_plus(self.MYSQL_PASSWORD)
        return f"mysql+aiomysql://{self.MYSQL_USER}:{pwd}@{self.MYSQL_SERVER}:{self.MYSQL_PORT}/{self.MYSQL_DB}"