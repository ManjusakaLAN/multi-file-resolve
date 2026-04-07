from typing import AsyncGenerator

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request
from core.infrastructure.database import AsyncSessionLocal
from core.infrastructure.cache import redis_manager
from services.auth.login_service import LoginService


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_remote_ip(request: Request) -> str:
    """
    通用 IP 获取依赖
    """
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    return request.client.host if request.client else "127.0.0.1"

async def get_redis() -> Redis:
    """获取 Redis 异步客户端单例"""
    return redis_manager.client

def get_login_service(
        db: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis)
) -> LoginService:
    """
    获取登录服务层对象
    :param db:
    :param redis:
    :return:
    """
    return LoginService(db,redis)
