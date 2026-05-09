import logging
import uuid
from typing import List, Optional
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.exception.llm_exception import CredentialException
from models.llm import Credential, ModelConfig
from schemas.general import PageResponse
from schemas.llm import (
    CredentialCreate,
    CredentialResponse, CredentialUpdate,
)
from util.db_util import paginate
from util.secret_util import cipher_client

logger = logging.getLogger(__name__)


async def stmt_condition_combine(user_id: str, name: str, provider: str):
    stmt = select(Credential).where(Credential.user_id.__eq__(user_id))

    if name:
        stmt = stmt.where(Credential.name.contains(name))

    if provider:
        stmt = stmt.where(Credential.provider.__eq__(provider))

    return stmt.order_by(Credential.created_at.desc())


class CredentialService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_credential(self, user_id: str, obj_in: CredentialCreate) -> CredentialResponse:
        """
        创建凭据，并可选地绑定模型
        """
        new_credential = Credential(
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

            stmt = select(ModelConfig).where(ModelConfig.id.in_(model_ids))
            result = await self.db.execute(stmt)
            models = result.scalars().all()
            new_credential.models = list(models)

        self.db.add(new_credential)
        try:
            await self.db.commit()
            await self.db.refresh(new_credential)

            credential_response = CredentialResponse.model_validate(new_credential)
            credential_response.api_key = self.mask_api_key(obj_in.api_key)
            return credential_response
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

    async def get_credential_by_id(self, credential_id: str, user_id: str) -> Credential:
        """
        获取凭据详情（带权限校验）
        """
        stmt = (select(Credential)
        .options(selectinload(Credential.models))  # 关键：预加载多对多关系
        .where(
            and_(Credential.id == credential_id, Credential.user_id == user_id)
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
            credential_update: CredentialUpdate
    ) -> CredentialResponse:
        """
        更新凭据信息
        """
        # 1. 预加载 models 关系，避免后续赋值时的 Lazy Loading 报错
        # 同时在查询阶段就加入 user_id 校验，防止越权
        stmt = (
            select(Credential)
            .where(
                and_(
                    Credential.id == credential_update.id
                )
            )
            .options(selectinload(Credential.models))
        )

        result = await self.db.execute(stmt)
        credential = result.scalar_one_or_none()

        if not credential:
            raise CredentialException(status_code=404, message="凭据不存在或无权访问")

        # 2. 更新基础字段
        credential.name = credential_update.name
        credential.provider = credential_update.provider
        credential.api_base = credential_update.api_base

        # 3. 严谨的 API Key 更新逻辑
        # 只有当传入了新 key，且新 key 不是脱敏占位符时才执行加密
        new_raw_key = credential_update.api_key
        if new_raw_key and not any(mask in new_raw_key for mask in ["...", "***"]):
            logger.info(f"检测到 API Key 变更，执行加密存储")
            credential.api_key = cipher_client.encrypt(new_raw_key)

        # 4. 更新模型绑定 (因为上面用了 selectinload，这里赋值不会报错)
        if credential_update.models is not None:
            model_ids = [model.id for model in credential_update.models]
            if model_ids:
                m_stmt = select(ModelConfig).where(ModelConfig.id.in_(model_ids))
                m_result = await self.db.execute(m_stmt)
                credential.models = list(m_result.scalars().all())
            else:
                credential.models = []

        try:
            await self.db.commit()
            # 刷新以获取数据库最新的状态（如 updated_at 等）
            await self.db.refresh(credential)

            credential_response = CredentialResponse.model_validate(credential)
            credential_response.api_key = self.mask_api_key(new_raw_key)

            return credential_response

        except Exception as e:
            await self.db.rollback()
            logger.error(f"更新凭据失败，ID: {credential_update.id}, Error: {e}")
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
        stmt = select(ModelConfig).where(ModelConfig.id.in_(model_ids))
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
