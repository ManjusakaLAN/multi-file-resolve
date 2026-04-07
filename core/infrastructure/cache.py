import logging
from typing import Optional

# --- 关键修改点：确保导入的是异步模块 ---
import redis.asyncio as redis
from redis.asyncio import Redis

from core.config import settings

logger = logging.getLogger(__name__)

class RedisClientManager:
    """Redis 异步客户端管理类"""

    def __init__(self):
        # 这里的 Redis 类型现在正确指向了 asyncio 版本
        self._client: Optional[Redis] = None

    async def init_redis(self):
        """初始化 Redis 连接池"""
        try:
            if self._client is None:
                # 此时调用的是 redis.asyncio.from_url，返回的是异步对象
                self._client = redis.from_url(
                    settings.REDIS_URL,
                    encoding=settings.REDIS_ENCODING,
                    decode_responses=True,
                    max_connections=20
                )
                # 异步对象的 ping() 是一个协程，可以被 await
                await self._client.ping()
                logger.info("连接redis成功")
        except Exception as e:
            # 这里的打印会帮你确认最终生成的对象类型
            logger.error(f"连接redis失败: {e}")
            raise e

    async def close_redis(self):
        """关闭 Redis 连接池"""
        if self._client:
            # 异步客户端建议使用 await close()
            await self._client.close()
            logger.info("redis连接已经关闭")

    @property
    def client(self) -> Redis:
        """获取 Redis 实例"""
        if self._client is None:
            raise RuntimeError("redis客户端还没有初始化,请先初始化")
        return self._client

# 创建单例对象供全局调用
redis_manager = RedisClientManager()

def get_redis_client() -> Redis:
    """获取redis客户端"""
    return redis_manager.client