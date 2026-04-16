import logging
import uuid
from typing import List, Optional
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.exception.llm_exception import CredentialException
from models.llm import LLMCredential, LLMModel
from schemas.general import PageResponse
from schemas.llm import (
    LLMCredentialCreate,
    LLMCredentialResponse, LLMCredentialUpdate,
)
from util.db_util import paginate
from util.secret_util import cipher_client

logger = logging.getLogger(__name__)


async def stmt_condition_combine(user_id: str, name: str, provider: str):
    stmt = select(LLMCredential).where(LLMCredential.user_id.__eq__(user_id))

    if name:
        stmt = stmt.where(LLMCredential.name.contains(name))

    if provider:
        stmt = stmt.where(LLMCredential.provider.__eq__(provider))

    return stmt.order_by(LLMCredential.created_at.desc())


class LLMCredentialService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_credential(self, user_id: str, obj_in: LLMCredentialCreate) -> LLMCredential:
        """
        创建凭据，并可选地绑定模型
        """
        new_credential = LLMCredential(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=obj_in.name,
            provider=obj_in.provider,
            api_key=cipher_client.encrypt(obj_in.api_key),  # 建议在此处调用加密工具类，如 cipher.encrypt(obj_in.api_key)
            api_base=obj_in.api_base
        )

        # 处理初始模型绑定
        if obj_in.models:
            model_ids = [model.id for model in obj_in.models]

            stmt = select(LLMModel).where(LLMModel.id.in_(model_ids))
            result = await self.db.execute(stmt)
            models = result.scalars().all()
            new_credential.models = list(models)

        self.db.add(new_credential)
        try:
            await self.db.commit()
            await self.db.refresh(new_credential)
            new_credential.api_key = self.mask_api_key(obj_in.api_key)
            return new_credential
        except Exception as e:
            await self.db.rollback()
            logger.error(f"创建凭据失败: {e}")
            raise CredentialException(status_code=500, message="数据库写入失败")

    async def page_list_credentials(
            self,
            user_id: str,
            name: Optional[str] = None,
            provider: Optional[str] = None,
            page: int = 1,
            page_size: int = 10
    ) -> PageResponse:
        """
        分页查询用户的凭据
        :param user_id:
        :param name:
        :param provider:
        :param page:
        :param page_size:
        :return:
        """
        stmt = await stmt_condition_combine(user_id, name, provider)
        return await paginate(self.db, stmt, page, page_size)

    async def list_credentials(
            self,
            user_id: str,
            name: Optional[str] = None,
            provider: Optional[str] = None,
    ):
        """
        查询用户凭据(不分页)
        :param user_id:
        :param name:
        :param provider:
        :return:
        """
        stmt = await stmt_condition_combine(user_id, name, provider)
        return (await self.db.execute(stmt)).scalars().all()

    async def get_credential_by_id(self, credential_id: str, user_id: str) -> LLMCredential:
        """
        获取凭据详情（带权限校验）
        """
        stmt = (select(LLMCredential)
        .options(selectinload(LLMCredential.models))  # 关键：预加载多对多关系
        .where(
            and_(LLMCredential.id == credential_id, LLMCredential.user_id == user_id)
        ))
        result = await self.db.execute(stmt)
        item = result.scalar_one_or_none()
        if not item:
            raise CredentialException(status_code=404, message="凭据不存在或无权访问")
        # 解密 API Key 并脱敏
        item.api_key = cipher_client.decrypt(item.api_key)
        item.api_key = self.mask_api_key(item.api_key)

        return item

    async def update_credential(
            self,
            user_id: str,
            credential_update: LLMCredentialUpdate
    ) -> LLMCredential:
        """
        更新凭据信息
        """
        credential = await self.get_credential_by_id(credential_update.id, user_id)

        credential.name = credential_update.name
        credential.provider = credential_update.provider
        if not (credential_update.api_key.__contains__("...") or credential_update.api_key.__contains__("***")):
            # 说明要修改apikey
            credential.api_key = cipher_client.encrypt(credential_update.api_key)
        credential.api_base = credential_update.api_base

        # 更新始模型绑定
        if credential_update.models:
            model_ids = [model.id for model in credential_update.models]
            stmt = select(LLMModel).where(LLMModel.id.in_(model_ids))
            result = await self.db.execute(stmt)
            models = result.scalars().all()
            credential.models = list(models)

        try:
            await self.db.commit()
            await self.db.refresh(credential)
            credential.api_key = self.mask_api_key(credential_update.api_key)
            return credential
        except Exception as e:
            await self.db.rollback()
            logger.error(f"更新凭据失败: {e}")
            raise CredentialException(status_code=500, message="数据库更新失败")

    async def delete_credential(self, credential_id: str, user_id: str) -> bool:
        """
        删除凭据
        """
        credential = await self.get_credential_by_id(credential_id, user_id)

        try:
            await self.db.delete(credential)
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"删除凭据失败: {e}")
            raise CredentialException(status_code=500, message="数据库删除失败")

    async def bind_models(self, credential_id: str, user_id: str, model_ids: List[str]):
        """
        手动建立凭据与多个模型的绑定关系
        """
        credential = await self.get_credential_by_id(credential_id, user_id)

        # 查询待绑定的模型
        stmt = select(LLMModel).where(LLMModel.id.in_(model_ids))
        result = await self.db.execute(stmt)
        models = result.scalars().all()

        if not models:
            raise CredentialException(status_code=400, message="未找到有效的模型ID")

        # 更新多对多关系
        credential.models = list(models)

        try:
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"绑定模型失败: {e}")
            raise CredentialException(status_code=500, message="关联更新失败")

    @staticmethod
    def mask_api_key(key: str) -> str:
        """
        简单的密钥脱敏工具
        """
        if len(key) <= 8:
            return "**********"
        return f"{key[:4]}...{key[-4:]}"
