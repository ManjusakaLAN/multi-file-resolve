import logging
from typing import AsyncGenerator, List, Optional

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exception.security_exception import TokenException
from core.infrastructure.database import AsyncSessionLocal
from core.infrastructure.cache import redis_manager
from core.infrastructure.storage import MinioClient, minio_client
from core.infrastructure.vector_db import MilvusVectorDB
from services.auth.login_service import LoginService
from services.auth.permission_service import PermissionService
from services.auth.token_service import TokenService
from fastapi import Request, Depends, HTTPException

from services.contract.contract_service import ContractService
from services.file.file_service import FileService
from services.kb.kb_service import KBService
from services.contract.contract_agent_service import ContractAgentService
from services.llm.credential_service import LLMCredentialService
from services.llm.model_service import LLMModelService
from services.mcp.mcp_manager import MCPManager
from services.mcp.mcp_service import McpService
from services.system.dict_service import DictService
from services.user.user_service import UserService

logger = logging.getLogger(__name__)


########################### 中间件部分 ###########################
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据源对象
    :return:
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_redis() -> Redis:
    """
    获取Redis 异步客户端单例
    :return:
    """
    return redis_manager.client


async def get_storage() -> MinioClient:
    """
    获取存储对象
    :return:
    """
    return minio_client


async def get_milvus() -> MilvusVectorDB:
    """
    获取 Milvus 对象
    :return:
    """
    return MilvusVectorDB()


########################### 业务层部分 ###########################
async def get_login_service(
        db: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis)
) -> LoginService:
    """
    获取登录服务层对象
    :param db:
    :param redis:
    :return:
    """
    return LoginService(db, redis)


async def get_permission_service(
        db: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis)
) -> PermissionService:
    """
    获取权限服务层对象
    :param db:
    :param redis:
    :return:
    """
    return PermissionService(db, redis)


async def get_file_service(
        db: AsyncSession = Depends(get_db),
        minio_client: MinioClient = Depends(get_storage),
) -> FileService:
    """
    获取文件服务层对象
    :param minio_client:
    :param db:
    :return:
    """
    return FileService(db, minio_client)


async def get_user_service(
        db: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis),
        login_service: LoginService = Depends(get_login_service),
) -> UserService:
    """
    获取用户服务层对象
    :param login_service:
    :param redis:
    :param db:
    :return:
    """
    return UserService(db, redis, login_service)


async def get_dict_service(
        db: AsyncSession = Depends(get_db),
) -> DictService:
    """
    获取字典服务层对象
    :param db:
    :return:
    """
    return DictService(db)


async def get_mcp_manager() -> MCPManager:
    """
    获取 MCP 管理对象
    """
    return MCPManager()


async def get_mcp_service(
        db: AsyncSession = Depends(get_db),
        mcp_manager: MCPManager = Depends(get_mcp_manager),
) -> McpService:
    """
    获取mcp服务
    :param db:
    :param mcp_manager:
    :return:
    """
    return McpService(db, mcp_manager)


async def get_kb_service(
        db: AsyncSession = Depends(get_db),
        milvus_client=Depends(get_milvus),
):
    """
    获取知识库服务
    :param db:
    :param milvus_client:
    :return:
    """
    return KBService(db, milvus_client)


async def get_model_service(
        db: AsyncSession = Depends(get_db),
):
    """
    获取模型服务
    :param db:
    :return:
    """
    return LLMModelService(db)


async def get_credential_service(
        db: AsyncSession = Depends(get_db),
):
    """
    获取凭据服务
    :param db:
    :return:
    """
    return LLMCredentialService(db)


async def get_contract_agent_service(
        db: AsyncSession = Depends(get_db),
):
    """
    获取模型服务
    :param db:
    :return:
    """
    return ContractAgentService(db)


async def get_contract_service(
        db: AsyncSession = Depends(get_db),
        file_service: FileService = Depends(get_file_service),
        minio_client: MinioClient = Depends(get_storage),
        contract_agent_service: ContractAgentService = Depends(get_contract_agent_service),
        model_service: LLMModelService = Depends(get_model_service),
):
    """
    获取合同服务
    :param model_service:
    :param contract_agent_service:
    :param db:
    :param file_service:
    :param minio_client:
    :return:
    """
    return ContractService(db, file_service, contract_agent_service, model_service, minio_client)


########################### web 安全部分 ###########################
async def get_remote_ip(request: Request) -> str:
    """
    通用 IP 获取依赖
    """
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    return request.client.host if request.client else "127.0.0.1"


async def verify_token(request: Request,
                       redis: Redis = Depends(get_redis)) -> str:
    """
    Token 校验依赖项 (拦截器)
    """
    try:
        # 不开启鉴权 返回空
        if not settings.LOGIN_ENABLED:
            return ""

        # 从 Header 获取 token (例如: Authorization: Bearer xxxx)
        auth_header = request.headers.get("Authorization")
        # 调用 Service 验证 Token
        user_id = await TokenService.verify(auth_header, redis)
    except TokenException as e:
        logger.error(f"获取token失败: {e}")
        raise e
    # 将解析出的用户信息存入 request.state 方便后续调用
    request.state.user_id = user_id
    return user_id


class PermissionChecker:
    def __init__(
            self,
            required_permissions: Optional[List[str]] = None,
            required_roles: Optional[List[str]] = None,
            require_all: bool = False
    ):
        """
        :param required_permissions: 需要的权限代码列表
        :param required_roles: 需要的角色代码列表
        :param require_all: True 表示必须同时满足角色和权限要求，False 表示满足其一即可
        """
        self.required_permissions = required_permissions or []
        self.required_roles = required_roles or []
        self.require_all = require_all

    async def __call__(
            self,
            request: Request,
            perm_service: PermissionService = Depends(get_permission_service)
    ):
        # 1. 获取用户 ID
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            raise HTTPException(status_code=401, detail="认证失败，无法获取用户信息")

        # 2. 获取用户完整信息（含角色对象和权限字符串列表）
        user_info = await perm_service.get_user_info(user_id)
        if not user_info:
            raise HTTPException(status_code=401, detail="用户信息不存在或已失效")

        # 3. 超级管理员：拥有最高优先级，直接放行
        user_role_codes = [r.code for r in user_info.roles]
        if "admin" in user_role_codes:
            request.state.user = user_info
            return True

        # 4. 判定角色是否匹配
        role_matched = False
        if self.required_roles:
            # 取交集判断是否拥有指定角色之一
            if set(self.required_roles).intersection(set(user_role_codes)):
                role_matched = True

        # 5. 判定权限是否匹配
        perm_matched = False
        if self.required_permissions:
            # 取交集判断是否拥有指定权限之一
            if set(self.required_permissions).intersection(set(user_info.permissions)):
                perm_matched = True

        # 6. 综合逻辑判定
        # 如果设置了 require_all=True，则必须角色和权限都通过
        # 否则（默认），只要满足角色或权限之一即可
        is_authorized = False
        if self.require_all:
            is_authorized = role_matched and perm_matched
        else:
            # 如果没指定角色要求，则只看权限；如果没指定权限要求，则只看角色
            is_authorized = role_matched or perm_matched

        if not is_authorized:
            detail = []
            if self.required_roles: detail.append(f"角色: {self.required_roles}")
            if self.required_permissions: detail.append(f"权限: {self.required_permissions}")

            raise HTTPException(
                status_code=403,
                detail=f"权限不足。需要满足 {' 且 '.join(detail) if self.require_all else ' 或 '.join(detail)}"
            )

        # 7. 挂载用户信息供后续路由使用
        request.state.user = user_info
        return True
