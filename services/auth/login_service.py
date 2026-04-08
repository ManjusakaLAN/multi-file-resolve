import base64
import logging
import secrets
from datetime import datetime, UTC, timedelta
from typing import Optional, Tuple
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exception.auth_exception import UserLoginException, CaptchaExpireOrNotExistError, UserRegisterException
from core.constant.redis_key import REDIS_KEY_ACCESS_TOKEN_PREFIX, REDIS_KEY_REFRESH_TOKEN_PREFIX
from models.user import User
from schemas.user import UserCreate
from util.auth_util import compare_password, valid_password, hash_password, PassportService

logger = logging.getLogger(__name__)


def _generate_tokens(user: User) -> Tuple[str, str]:
    """内部私有方法：生成 JWT 令牌对"""
    access_exp = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_exp = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    passport = PassportService()

    access_token = passport.generate_token({
        "id": user.id,
        "account_name": user.account_name,
        "exp_time": int(access_exp.timestamp()),
    })

    refresh_token = passport.generate_token({
        "id": user.id,
        "account_name": user.account_name,
        "exp_time": int(refresh_exp.timestamp()),
    })

    return access_token, refresh_token


class LoginService:
    def __init__(self, db: AsyncSession, redis: Redis |  None):
        self.db = db
        self.redis = redis

    async def login(self, account_name: str, password: str, login_ip: str, code: Optional[str] = None):
        """
        用户登录
        :param login_ip:
        :param account_name:
        :param password:
        :param code:
        :return:
        """
        if settings.CAPTCHA_ENABLED:
            # 格式化验证码
            cache_key = code.strip().lower()
            # 直接执行删除操作，delete 返回的是成功删除的个数
            # 这是原子操作，且只有一次网络请求
            deleted_count = await self.redis.delete(cache_key)
            if deleted_count == 0:
                raise CaptchaExpireOrNotExistError("验证码已过期或不存在")

        # 查询用户
        stmt = select(User).where(User.account_name == account_name)
        result = await self.db.execute(stmt)
        user = result.scalars().first()

        if not user:
            logger.error(f"登录失败：用户 {account_name} 不存在")
            raise UserLoginException("用户名或密码错误")

        # 验证密码
        if not compare_password(password, user.password, user.password_salt):
            logger.error(f"登录失败：用户 {account_name} 密码错误")
            raise UserLoginException("用户名或密码错误")

        # 先登出以前的
        await self.logout(user.id)

        # 更新登录信息
        user.last_login_at = datetime.now(settings.tz_info)
        user.last_login_ip = login_ip
        await self.db.commit()

        # 生成 Token 载荷
        access_token, refresh_token = _generate_tokens(user)

        # 存储到 Redis
        access_key = f"{REDIS_KEY_ACCESS_TOKEN_PREFIX}{user.id}"
        refresh_key = f"{REDIS_KEY_REFRESH_TOKEN_PREFIX}{user.id}"

        await self.redis.setex(access_key, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, access_token)
        await self.redis.setex(refresh_key, settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60, refresh_token)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }

    async def logout(self, user_id: str):
        """
        登出账号
        :param user_id:
        :return:
        """
        await self.redis.delete(f"{REDIS_KEY_ACCESS_TOKEN_PREFIX}{user_id}")
        await self.redis.delete(f"{REDIS_KEY_REFRESH_TOKEN_PREFIX}{user_id}")

    async def register(self, user_create: UserCreate):
        """
        注册用户
        :param user_create:
        :return:
        """
        if settings.CAPTCHA_ENABLED:
            cache_key = user_create.code.strip().lower()
            deleted_count = await self.redis.delete(cache_key)
            if deleted_count == 0:
                raise CaptchaExpireOrNotExistError("验证码已过期或不存在")
        # 验证密码是否符合要求
        valid_password(user_create.password)
        # 判断两次输入密码是否一致
        if user_create.password != user_create.confirm_password:
            raise UserRegisterException("两次输入的密码不一致")

        # 判断是否系统已经注册了该用户
        stmt = select(User).where(User.account_name == user_create.account_name)
        result = await self.db.execute(stmt)
        if result.scalars().first():
            raise UserRegisterException("用户已存在")

        # 进行密码加密
        # 生成密码盐
        salt = secrets.token_bytes(16)
        base64_salt = base64.b64encode(salt).decode()

        # 用盐加密密码
        password_hashed = hash_password(user_create.password, salt)
        base64_password_hashed = base64.b64encode(password_hashed).decode()

        user = User(
            account_name=user_create.account_name,
            user_name=user_create.user_name,
            email=user_create.email,
            avatar=user_create.avatar,
            password=base64_password_hashed,
            password_salt=base64_salt,
            status=user_create.status
        )
        self.db.add(user)
        try:
            await self.db.commit()
            # 【关键修复】手动刷新，强制从数据库重新加载所有字段（包括 ID 和时间戳）
            # 这样当它回到 FastAPI 序列化层时，数据已经是现成的，不需要再发起隐式查询
            await self.db.refresh(user)
        except Exception as e:
            await self.db.rollback()
            raise e
        return user
