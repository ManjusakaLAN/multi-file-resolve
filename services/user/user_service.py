import base64
import logging
import secrets
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from fastapi import HTTPException
from core.config import settings
from core.exception.auth_exception import UserEditException
from models.user import User as UserModel
from schemas.general import PageResponse
from schemas.user import UserCreate, User
from core.enum.status import UserStatus
from services.auth.login_service import LoginService
from util.auth_util import compare_password, valid_password, hash_password
from util.db_util import paginate

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, db: AsyncSession, redis: Redis, login_service: LoginService):
        self.db = db
        self.redis = redis
        self.login_service = login_service

    async def page_list_user(
            self,
            account_name: Optional[str],
            user_name: Optional[str],
            user_status: Optional[UserStatus],
            page: int,
            page_size: int
    ) -> PageResponse:
        """
        分页条件查询用户信息
        """
        stmt = select(UserModel)
        if account_name:
            stmt = stmt.where(UserModel.account_name.contains(account_name))
        if user_name:
            stmt = stmt.where(UserModel.user_name.contains(user_name))
        if user_status:
            stmt = stmt.where(UserModel.status == user_status.value)

        stmt = stmt.order_by(UserModel.created_at.desc())

        # 使用你项目中的 paginate 通用工具
        return await paginate(self.db, stmt, page, page_size)

    async def get_user_by_id(self, user_id: str) -> UserModel:
        """
        根据id查询用户模型
        """
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return user

    async def create_user(self, user_create: UserCreate) -> User:
        """
        新增用户：包含密码加盐处理和逻辑校验
        """
        return await self.login_service.register(user_create)

    async def update_user(self, user_id: str, user_name: str, email: str, avatar: str, status: UserStatus) -> UserModel:
        """
        更新用户信息
        """
        user = await self.get_user_by_id(user_id)
        user.user_name = user_name
        user.email = email
        user.avatar = avatar
        user.status = status
        user.updated_at = datetime.now(settings.tz_info)
        await self.db.commit()
        return user

    async def delete_user(self, user_id: str):
        """
        删除用户
        """
        user = await self.get_user_by_id(user_id)
        await self.db.delete(user)
        await self.db.commit()
        return True

    async def update_user_password(self, user: UserModel, password: str) -> UserModel:
        """
        更新用户密码
        :param user:
        :param password:
        :return:
        """
        # 验证密码是否符合要求
        valid_password(password)
        # 进行密码加密
        # 生成密码盐
        salt = secrets.token_bytes(16)
        base64_salt = base64.b64encode(salt).decode()

        # 用盐加密密码
        password_hashed = hash_password(password, salt)
        base64_password_hashed = base64.b64encode(password_hashed).decode()

        user.password = base64_password_hashed
        user.password_salt = base64_salt
        user.updated_at = datetime.now(settings.tz_info)
        await self.db.commit()
        await self.login_service.logout(user.id)
        await self.db.refresh(user)
        return user

    async def change_password(self, user_id: str, old_password: str, new_password: str, confirm_password: str):
        """
        修改密码
        :param user_id: 用户id
        :param old_password: 旧密码
        :param new_password: 新密码
        :param confirm_password: 确认新密码
        :return:
        """
        user = await self.get_user_by_id(user_id)

        # 验证密码
        if not compare_password(old_password, user.password, user.password_salt):
            logger.error(f"修改密码失败：用户 {user.account_name} 密码错误")
            raise UserEditException("旧密码错误")

        # 两次新密码必须一致
        if new_password != confirm_password:
            logger.error(f"修改密码失败：用户 {user.account_name} 两次新密码不一致")
            raise UserEditException("两次新密码不一致")

        return await self.update_user_password(user, new_password)

    async def reset_password(self, user_id, password):
        """
        管理员重置密码
        :param user_id:
        :param password:
        :return:
        """
        user = await self.get_user_by_id(user_id)
        # 验证密码是否符合要求
        return await self.update_user_password(user, password)
