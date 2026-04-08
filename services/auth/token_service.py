from datetime import datetime, timedelta

from redis.asyncio import Redis

from core.config import settings
from core.constant.redis_key import REDIS_KEY_ACCESS_TOKEN_PREFIX, REDIS_KEY_REFRESH_TOKEN_PREFIX
from core.exception.security_exception import TokenException
from util.auth_util import PassportService


class TokenService:

    @staticmethod
    async def verify(auth_header: str, redis: Redis) -> str:

        if auth_header is None or " " not in auth_header:
            raise TokenException("必须提供Authorization，并以'Bearer'开头")
        auth_scheme, auth_token = auth_header.split(None, 1)
        auth_scheme = auth_scheme.lower()

        if auth_scheme != "bearer":
            raise TokenException("请求头前缀格式Authorization的token前必须有'Bearer'")
        # 载荷
        payload = PassportService().verify_token(auth_token)
        # 获取换成中的token
        token_cache = await redis.get(f"{REDIS_KEY_ACCESS_TOKEN_PREFIX}{payload['id']}")

        if token_cache is None:
            raise TokenException("令牌不存在 请重新登录")

        if int(datetime.now(settings.tz_info).timestamp()) > payload["exp_time"]:
            raise TokenException("令牌过期 请重新登录")
        return payload['id']

    @staticmethod
    async def refresh_token(refresh_token: str, redis: Redis):

        refresh_payload = PassportService().verify_token(refresh_token)

        if redis.get(f"{REDIS_KEY_REFRESH_TOKEN_PREFIX}{refresh_payload['id']}") is None:
            raise TokenException("刷新令牌不存在 请重新登录")

        refresh_payload["exp_time"] = int(
            (datetime.now(settings.tz_info) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp())

        new_access_token = PassportService().generate_token(refresh_payload)

        # 存储token 到 redis
        await redis.setex(f"{REDIS_KEY_ACCESS_TOKEN_PREFIX}{refresh_payload['id']}",
                           settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                           new_access_token)
        return new_access_token