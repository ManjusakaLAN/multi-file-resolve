import logging
import uuid
from typing import Optional
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import  status

from core.exception.llm_exception import ModelException
from models.llm import LLMModel
from schemas.general import PageResponse
from schemas.llm import LLMModelCreate, LLMModelUpdate
from util.db_util import paginate

logger = logging.getLogger(__name__)


class LLMModelService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_model(self, obj_in: LLMModelCreate, user_id: Optional[str] = None) -> LLMModel:
        """
                创建模型定义
                逻辑：
                1. 如果是系统模型(system)：全局 model_code 必须唯一。
                2. 如果是自定义模型(custom)：该 user_id 下的 model_code 必须唯一。
                """
        # 1. 动态构建唯一性校验条件
        if obj_in.config_type.__eq__("system"):
            # 系统模型：全局查找是否有相同的 model_code
            stmt = select(LLMModel).where(LLMModel.model_code.__eq__(obj_in.model_code))
        else:
            # 自定义模型：只查找该用户下是否有相同的 model_code
            # 注意：即便系统里有同名的 code，用户也可以创建自己的同名配置（实现覆盖或私有化）
            stmt = select(LLMModel).where(
                and_(
                    LLMModel.model_code.__eq__(obj_in.model_code),
                    LLMModel.created_by.__eq__(user_id)
                )
            )
        existing = await self.db.execute(stmt)

        if existing.scalar_one_or_none():
            raise ModelException(
                code=status.HTTP_400_BAD_REQUEST,
                message=f"模型标识符 '{obj_in.model_code}' 已存在"
            )

        # 2. 创建实例
        new_model = LLMModel(
            id=str(uuid.uuid4()),
            model_name=obj_in.model_name,
            model_code=obj_in.model_code,
            default_api_base=obj_in.default_api_base,
            provider=obj_in.provider,
            config_type=obj_in.config_type,
            status=obj_in.status,
            created_by=user_id
        )

        self.db.add(new_model)
        try:
            await self.db.commit()
            await self.db.refresh(new_model)
            return new_model
        except Exception as e:
            await self.db.rollback()
            logger.error(f"创建模型失败: {e}")
            raise ModelException(status_code=500, message="数据库写入失败")

    async def page_list_models(
            self,
            model_name: Optional[str] = None,
            model_code: Optional[str] = None,
            provider: Optional[str] = None,
            config_type: Optional[str] = None,
            user_id: Optional[str] = None,
            page: int = 1,
            page_size: int = 10
    ) -> PageResponse:
        """
        分页查询模型列表：系统模型 + 用户自建模型
        """
        stmt = select(LLMModel)

        # 基础可见性过滤
        visibility_filters = [LLMModel.config_type.__eq__("system")]
        if user_id:
            visibility_filters.append(LLMModel.created_by.__eq__(user_id))

        stmt = stmt.where(or_(*visibility_filters))

        # 动态条件过滤
        if model_name:
            stmt = stmt.where(LLMModel.model_name.contains(model_name))
        if model_code:
            stmt = stmt.where(LLMModel.model_code.contains(model_code))
        if provider:
            stmt = stmt.where(LLMModel.provider.__eq__(provider))
        if config_type:
            stmt = stmt.where(LLMModel.config_type.__eq__(config_type))

        stmt = stmt.order_by(LLMModel.provider.asc(), LLMModel.created_at.desc())
        return await paginate(self.db, stmt, page, page_size)

    async def list_models(
            self,
            model_name: Optional[str] = None,
            model_code: Optional[str] = None,
            provider: Optional[str] = None,
            user_id: Optional[str] = None,
    ):
        """
        分页查询模型列表：系统模型 + 用户自建模型
        """
        stmt = select(LLMModel)

        # 基础可见性过滤
        visibility_filters = [LLMModel.config_type.__eq__("system")]
        if user_id:
            visibility_filters.append(LLMModel.created_by.__eq__(user_id))
        stmt = stmt.where(or_(*visibility_filters))

        # 动态条件过滤
        if model_name:
            stmt = stmt.where(LLMModel.model_name.contains(model_name))
        if model_code:
            stmt = stmt.where(LLMModel.model_code.contains(model_code))
        if provider:
            stmt = stmt.where(LLMModel.provider.__eq__(provider))

        stmt = stmt.order_by(LLMModel.provider.asc(), LLMModel.created_at.desc())
        return (await self.db.execute(stmt)).scalars().all()

    async def get_model_by_id(self, model_id: str) -> LLMModel:
        """
        根据ID获取模型
        """
        stmt = select(LLMModel).where(LLMModel.id.__eq__(model_id))
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise ModelException(status_code=404, message="模型定义不存在")
        return model

    async def update_model(
            self,
            model_update: LLMModelUpdate,
    ) -> LLMModel:
        """
        更新模型信息
        """
        model = await self.get_model_by_id(model_update.id)

        model.model_name = model_update.model_name
        model.model_code = model_update.model_code
        model.status = model_update.status
        model.provider = model_update.provider
        model.config_type = model_update.config_type
        model.default_api_base = model_update.default_api_base

        try:
            await self.db.commit()
            await self.db.refresh(model)
            return model
        except Exception as e:
            await self.db.rollback()
            logger.error(f"更新模型失败: {e}")
            raise ModelException(status_code=500, message="数据库更新失败")

    async def delete_model(self, model_id: str) -> bool:
        """
        删除模型
        """
        model = await self.get_model_by_id(model_id)

        try:
            await self.db.delete(model)
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"删除模型失败: {e}")
            raise ModelException(status_code=500, message="数据库删除失败")
