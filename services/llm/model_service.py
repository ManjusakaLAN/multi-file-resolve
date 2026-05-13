import logging
import uuid
from typing import Optional

from openai import OpenAI
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import  status
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool

from core.enum.model import ModelType
from core.exception.llm_exception import ModelException
from models.llm import ModelConfig
from schemas.general import PageResponse
from schemas.llm import ModelConfigCreate, ModelConfigUpdate, ModelInvokeInfo
from util.db_util import paginate
from util.secret_util import cipher_client

logger = logging.getLogger(__name__)


class ModelService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_model_invoke_info(self, model_id: str = None,
                                    model_type: ModelType | str = ModelType.LLM) -> ModelInvokeInfo:
        """
        通过 relationship 和 selectinload 获取模型调用信息
        """
        # 1. 构造查询，并明确指定预加载 credentials 关系
        stmt = select(ModelConfig).options(
            selectinload(ModelConfig.credentials)
        )

        if model_id:
            stmt = stmt.where(ModelConfig.id == model_id)
        else:
            # 注意：这里确保 ModelConfig.model_type 是字符串或兼容枚举
            stmt = stmt.where(ModelConfig.model_type == model_type)

        result = await self.db.execute(stmt)
        model_config = result.scalars().first()

        if not model_config:
            raise ModelException("模型不存在", status.HTTP_404_NOT_FOUND, )

        # 2. 检查是否有绑定的凭据 (此时 credentials 已被加载到内存)
        if not model_config.credentials:
            raise ModelException("该模型未绑定任何凭据", status.HTTP_404_NOT_FOUND, )

        # 3. 遍历预加载好的凭据进行测试
        for credential in model_config.credentials:
            model_invoke_info = ModelInvokeInfo(
                base_url=credential.api_base,
                model_id=model_config.model_code,
                model_type=model_config.model_type,
                provider=model_config.provider
            )

            # 解密 API Key
            try:
                model_invoke_info.api_key = cipher_client.decrypt(credential.api_key)
            except Exception as e:
                logger.error(f"凭据 {credential.id} 解密失败: {e}")
                continue

            # 4. 定义同步测试函数，防止阻塞异步事件循环
            def test_connection():
                test_client = OpenAI(
                    api_key=model_invoke_info.api_key,
                    base_url=model_invoke_info.base_url
                )
                # 简单的测试调用
                return test_client.models.list()

            try:
                # 使用 FastAPI 提供的线程池运行同步 I/O 任务
                available_models = await run_in_threadpool(test_connection)
                logger.info(
                    f"成功通过凭据 {credential.id} 连接到模型 {model_config.model_code} 目前可用模型：{available_models}")
                return model_invoke_info
            except Exception as e:
                logger.warning(f"凭据 {credential.id} 连接测试失败: {e}")
                continue

        raise ModelException("所有绑定凭据均无法通过连接测试", status.HTTP_404_NOT_FOUND)

    async def create_model(self, create_model: ModelConfigCreate, user_id: Optional[str] = None) -> ModelConfig:
        """
                创建模型定义
                逻辑：
                1. 如果是系统模型(system)：全局 model_code 必须唯一。
                2. 如果是自定义模型(custom)：该 user_id 下的 model_code 必须唯一。
                """
        # 1. 动态构建唯一性校验条件
        if create_model.config_type.__eq__("system"):
            # 系统模型：全局查找是否有相同的 model_code
            stmt = select(ModelConfig).where(ModelConfig.model_code.__eq__(create_model.model_code))
        else:
            # 自定义模型：只查找该用户下是否有相同的 model_code
            # 注意：即便系统里有同名的 code，用户也可以创建自己的同名配置（实现覆盖或私有化）
            stmt = select(ModelConfig).where(
                and_(
                    ModelConfig.model_code.__eq__(create_model.model_code),
                    ModelConfig.created_by.__eq__(user_id)
                )
            )
        existing = await self.db.execute(stmt)

        if existing.scalar_one_or_none():
            raise ModelException(
                code=status.HTTP_400_BAD_REQUEST,
                message=f"模型标识符 '{create_model.model_code}' 已存在"
            )

        # 2. 创建实例
        new_model = ModelConfig(
            id=str(uuid.uuid4()),
            model_name=create_model.model_name,
            model_code=create_model.model_code,
            default_api_base=create_model.default_api_base,
            provider=create_model.provider,
            config_type=create_model.config_type,
            status=create_model.status,
            created_by=user_id,
            model_type=create_model.model_type
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
            model_type: Optional[str] = None,
            page: int = 1,
            page_size: int = 10
    ) -> PageResponse:
        """
        分页查询模型列表：系统模型 + 用户自建模型
        """
        stmt = select(ModelConfig)

        # 基础可见性过滤
        visibility_filters = [ModelConfig.config_type.__eq__("system")]
        if user_id:
            visibility_filters.append(ModelConfig.created_by.__eq__(user_id))

        stmt = stmt.where(or_(*visibility_filters))

        # 动态条件过滤
        if model_type:
            stmt = stmt.where(ModelConfig.model_type.__eq__(model_type))
        if model_name:
            stmt = stmt.where(ModelConfig.model_name.contains(model_name))
        if model_code:
            stmt = stmt.where(ModelConfig.model_code.contains(model_code))
        if provider:
            stmt = stmt.where(ModelConfig.provider.__eq__(provider))
        if config_type:
            stmt = stmt.where(ModelConfig.config_type.__eq__(config_type))

        stmt = stmt.order_by(ModelConfig.provider.asc(), ModelConfig.created_at.desc())
        return await paginate(self.db, stmt, page, page_size)

    async def list_models(
            self,
            model_name: Optional[str] = None,
            model_code: Optional[str] = None,
            provider: Optional[str] = None,
            user_id: Optional[str] = None,
            model_type: Optional[str] = None
    ):
        """
        分页查询模型列表：系统模型 + 用户自建模型
        """
        stmt = select(ModelConfig)

        # 基础可见性过滤
        visibility_filters = [ModelConfig.config_type.__eq__("system")]
        if user_id:
            visibility_filters.append(ModelConfig.created_by.__eq__(user_id))
        stmt = stmt.where(or_(*visibility_filters))

        # 动态条件过滤
        if model_type:
            stmt = stmt.where(ModelConfig.model_type.__eq__(model_type))
        if model_name:
            stmt = stmt.where(ModelConfig.model_name.contains(model_name))
        if model_code:
            stmt = stmt.where(ModelConfig.model_code.contains(model_code))
        if provider:
            stmt = stmt.where(ModelConfig.provider.__eq__(provider))

        stmt = stmt.order_by(ModelConfig.provider.asc(), ModelConfig.created_at.desc())
        return (await self.db.execute(stmt)).scalars().all()

    async def get_model_by_id(self, model_id: str) -> ModelConfig:
        """
        根据ID获取模型
        """
        stmt = select(ModelConfig).where(ModelConfig.id.__eq__(model_id))
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise ModelException(status_code=404, message="模型定义不存在")
        return model

    async def update_model(
            self,
            model_update: ModelConfigUpdate,
    ) -> ModelConfig:
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
        model.model_type = model_update.model_type

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