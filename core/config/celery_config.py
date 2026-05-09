from typing import Any
from pydantic import Field, PositiveFloat, computed_field
from pydantic_settings import BaseSettings

class CelerySettings(BaseSettings):
    # --- 基础配置 ---
    CELERY_BACKEND: str = Field(
        description="Celery 任务结果的后端类型。可选值: 'database' (数据库), 'redis', 'rabbitmq'。",
        default="redis",
    )

    CELERY_BROKER_URL: str | None = Field(
        description="Celery 消息代理（中间人）的 URL 地址，例如 redis://localhost:6379/0。",
        default=None,
    )

    # --- Redis 哨兵模式配置 (用于高可用) ---
    CELERY_USE_SENTINEL: bool | None = Field(
        description="是否使用 Redis Sentinel（哨兵）实现高可用。",
        default=False,
    )

    CELERY_SENTINEL_MASTER_NAME: str | None = Field(
        description="Redis 哨兵主节点的名称。",
        default=None,
    )

    CELERY_SENTINEL_PASSWORD: str | None = Field(
        description="Redis 哨兵主节点的密码。",
        default=None,
    )

    CELERY_SENTINEL_SOCKET_TIMEOUT: PositiveFloat | None = Field(
        description="Redis 哨兵套接字操作的超时时间（秒）。",
        default=0.1,
    )

    # --- 任务特定配置 ---
    CELERY_TASK_ANNOTATIONS: dict[str, Any] | None = Field(
        description=(
            "Celery 任务的注解配置，使用 JSON 映射格式：任务名 -> 配置项。"
            "（例如：设置特定任务的速率限制 rate_limits 或其他选项）。"
        ),
        default=None,
    )

    # --- 计算属性 (逻辑处理) ---
    @computed_field
    def CELERY_RESULT_BACKEND(self) -> str | None:
        """
        根据指定的 CELERY_BACKEND 自动生成结果存储的完整 URL。
        """
        # 如果是数据库或 RabbitMQ，格式通常为 db+数据库连接串
        if self.CELERY_BACKEND in ("database", "rabbitmq"):
            return f"db+{self.SQLALCHEMY_DATABASE_URI}"
        # 如果是 Redis，结果后端通常和代理地址一致
        elif self.CELERY_BACKEND == "redis":
            return self.CELERY_BROKER_URL
        else:
            return None

    @property
    def BROKER_USE_SSL(self) -> bool:
        """
        根据 Broker 协议头自动判断是否开启 SSL 加密传输。
        如果是 'rediss://' (双 s) 则返回 True。
        """
        return self.CELERY_BROKER_URL.startswith("rediss://") if self.CELERY_BROKER_URL else False