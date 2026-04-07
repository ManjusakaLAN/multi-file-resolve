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