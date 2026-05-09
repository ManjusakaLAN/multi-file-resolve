import logging
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.enum.kb import KBType, KBOpenStatus
from core.enum.mcp import McpType, McpConnectedStatus
from core.enum.model import ModelProvider, ModelConfigType, ModelType
from core.enum.status import UserStatus
from core.infrastructure.vector_db import MilvusVectorDB
from models.llm import ModelConfig
from models.user import User, Role, Permission
from schemas.llm import CredentialCreate, ModelConfigResponse
from schemas.user import Role as RoleSchema
from schemas.dict import DictCreate
from schemas.user import UserCreate
from services.auth.login_service import LoginService  # 假设你的注册逻辑在此
from services.auth.permission_service import PermissionService
from services.kb.kb_service import KBService
from services.llm.credential_service import CredentialService
from services.system.dict_service import DictService

logger = logging.getLogger(__name__)


class InitService:
    def __init__(self, db: AsyncSession, redis, milvus_client: MilvusVectorDB):
        self.db = db
        self.perm_service = PermissionService(db, redis)
        self.login_service = LoginService(db, redis)
        self.dict_service = DictService(db)
        self.kb_service = KBService(db, milvus_client)
        self.credential_service = CredentialService(db)

    async def init_basic_data(self):
        """核心初始化逻辑"""
        try:
            # 1. 基础档案（权限 & 角色）
            # 必须最先执行，因为后面的绑定依赖这些 code 的存在
            await self._init_permissions()
            await self._init_roles()

            # 2. 用户档案
            await self._init_users()

            # 3. 建立关联（角色 <-> 权限）
            await self._init_role_permission_bindings()

            # 4. 建立关联（用户 <-> 角色）
            await self._init_user_role_bindings()

            # 5. 新增系统字典
            await self._init_system_dict()

            # 6. 新增系统知识库
            await self._init_system_knowledge_base()

            # 7. 新增系统模型 和 凭证
            await self._init_system_model_and_credential()

            logger.info("✅ 项目基础数据初始化全量完成")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ 初始化过程中发生崩溃: {e}")
            raise

    async def _get_id_by_code(self, model: Any, code: str) -> Optional[str]:
        """辅助方法：通过 code 获取 ID (已消除类型检查警告)"""
        # 使用 .__eq__() 代替 == 消除 bool 类型误判警告
        # 使用 model.code 获取属性
        stmt = select(model.id).where(model.code.__eq__(code))

        res = await self.db.execute(stmt)
        # scalar_one_or_none 返回第一行第一列的值，即 ID 本身
        result = res.scalar_one_or_none()

        # 确保返回的是字符串类型（如果 ID 是 UUID 对象则转换）
        return str(result) if result else None

    async def _init_permissions(self):
        """初始化权限点"""
        permissions = [
            {"name": "全部权限", "code": "*:*"},
            {"name": "新增权限", "code": "*:add"},
            {"name": "修改权限", "code": "*:edit"},
            {"name": "查询权限", "code": "*:get"},
            {"name": "删除权限", "code": "*:delete"},
        ]
        for p in permissions:
            # 检查 code 是否已存在，防止重复创建
            if not await self._get_id_by_code(Permission, p["code"]):
                await self.perm_service.create_permission(**p)
        logger.info("- 权限点初始化完成")

    async def _init_roles(self):
        """初始化角色"""
        roles = [
            {"name": "超级管理员", "code": "admin", "desc": "最高权限"},
            {"name": "系统管理员", "code": "system_manager", "desc": "管理权限(无删除)"},
            {"name": "普通用户", "code": "user", "desc": "业务权限(新增/查看)"},
        ]
        for r in roles:
            if not await self._get_id_by_code(Role, r["code"]):
                await self.perm_service.create_role(**r)
        logger.info("- 角色档案初始化完成")

    async def _init_users(self):
        """初始化用户"""
        users = [
            {"account_name": "admin", "user_name": "超级管理员", "password": "hxxc!@#1309"},
            {"account_name": "user01", "user_name": "用户01-系统管理员", "password": "hxxc!@#1309"},
            {"account_name": "user02", "user_name": "用户02-普通员工", "password": "hxxc!@#1309"},
        ]
        for u in users:
            # 检查用户是否已存在（使用 .__eq__ 消除警告）
            stmt = select(User).where(User.account_name.__eq__(u["account_name"]))
            existing_user = (await self.db.execute(stmt)).scalar_one_or_none()

            if not existing_user:
                # 显式补全 UserCreate Schema 要求的必填字段，防止 ValidationError
                await self.login_service.register(UserCreate(
                    account_name=u["account_name"],
                    user_name=u["user_name"],
                    password=u["password"],
                    confirm_password=u["password"],
                    email="",  # 修复：补全必填字段
                    avatar="",  # 修复：补全必填字段
                    code="",  # 修复：补全必填字段
                    status="active"
                ))

        # 别忘了在这里 commit，确保用户数据先落库，后续绑定才能查到 ID
        await self.db.commit()
        logger.info("- 用户档案初始化完成")

    async def _init_role_permission_bindings(self):
        """配置角色权限（管理员所有，系统管理员无删除，普通用户仅增查）"""
        # 定义配置映射
        binding_cfg = {
            "admin": ["*:*"],
            "system_manager": ["*:add", "*:edit", "*:get"],
            "user": ["*:add", "*:get"]
        }

        for r_code, p_codes in binding_cfg.items():
            role_id = await self._get_id_by_code(Role, r_code)
            p_ids = []
            for pc in p_codes:
                pid = await self._get_id_by_code(Permission, pc)
                if pid: p_ids.append(pid)

            if role_id and p_ids:
                # 复用 Service 的批量绑定方法
                await self.perm_service.bind_permissions_to_role(role_id, p_ids)
        logger.info("- 角色-权限关联配置完成")

    async def _init_user_role_bindings(self):
        """配置用户角色"""
        user_role_cfg = {
            "admin": ["admin"],
            "user01": ["system_manager"],
            "user02": ["user"]
        }

        for acc_name, r_codes in user_role_cfg.items():
            # 查用户 ID
            u_stmt = select(User.id).where(User.account_name == acc_name)
            uid = (await self.db.execute(u_stmt)).scalar_one_or_none()

            # 查角色 IDs
            r_ids = []
            for rc in r_codes:
                rid = await self._get_id_by_code(Role, rc)
                if rid: r_ids.append(rid)

            if uid and r_ids:
                # 复用 Service 的分配角色方法
                await self.perm_service.assign_roles_to_user(str(uid), r_ids)
        logger.info("- 用户-角色关联配置完成")

    async def _init_system_dict(self):
        """
        初始化系统字典信息
        :return:
        """

        dicts = [
            # 用户状态字典(user_status)
            *[
                DictCreate(
                    dict_code="user_status",
                    label=McpType.get_desc(item),
                    value=item,
                    sort=idx,
                    is_system=1
                ) for idx, item in enumerate(UserStatus)
            ],
            # mcp类型字典(mcp_type)
            *[
                DictCreate(
                    dict_code="mcp_type",
                    label=McpType.get_desc(item),
                    value=item,
                    sort=idx,
                    is_system=1
                ) for idx, item in enumerate(McpType)
            ],
            # mcp连接情况(mcp_connected_status)
            *[
                DictCreate(
                    dict_code="mcp_connected_status",
                    label=McpConnectedStatus.get_desc(item),
                    value=item,
                    sort=idx,
                    is_system=1
                ) for idx, item in enumerate(McpConnectedStatus)
            ],
            # 模型配置类型字典(model_config_type)
            *[
                DictCreate(
                    dict_code="model_config_type",
                    label=ModelConfigType.get_desc(item),
                    value=item,
                    sort=idx,
                    is_system=1
                ) for idx, item in enumerate(ModelConfigType)
            ],
            # 模型供应商字典 (model_provider)
            *[
                DictCreate(
                    dict_code="model_provider",
                    label=ModelProvider.get_desc(item),
                    value=item,
                    sort=idx,
                    is_system=1
                ) for idx, item in enumerate(ModelProvider)
            ],
            # 知识库类型(kb_type)
            *[
                DictCreate(
                    dict_code="kb_type",
                    label=KBType.get_desc(item),
                    value=item,
                    sort=idx,
                    is_system=1
                ) for idx, item in enumerate(KBType)
            ],
            # 知识库开放状态(kb_open_status)
            *[
                DictCreate(
                    dict_code="kb_open_status",
                    label=KBOpenStatus.get_desc(item),
                    value=item,
                    sort=idx,
                    is_system=1
                ) for idx, item in enumerate(KBOpenStatus)
            ],
            # 模型类型 model_type
            *[
                DictCreate(
                    dict_code="model_type",
                    label=ModelType.get_desc(item),
                    value=item,
                    sort=idx,
                    is_system=1
                ) for idx, item in enumerate(ModelType)
            ],
        ]

        for dict_create in dicts:
            await self.dict_service.create_dict(**dict_create.model_dump())

    async def _init_system_knowledge_base(self):

        stmt = select(Role).where(Role.code == "system_manager")
        # 转为字典
        system_manager_role = RoleSchema.model_validate((await self.db.execute(stmt)).scalars().first()).model_dump()
        stmt = select(Role).where(Role.code == "user")
        user_role = RoleSchema.model_validate((await self.db.execute(stmt)).scalars().first()).model_dump()

        # 通过user_name 拿到user_id
        stmt = select(User.id).where(User.user_name == "用户02-普通员工")
        user_id = (await self.db.execute(stmt)).scalar_one_or_none()

        await self.kb_service.create_kb(
            kb_name="知识库1",
            kb_type="system",
            icon_key="",
            description="超级管理员、系统管理员可查看",
            permit_roles=[system_manager_role],
            user_id=user_id
        )

        await self.kb_service.create_kb(
            kb_name="知识库2",
            kb_type="system",
            icon_key="",
            description="所有用户可查看",
            permit_roles=[user_role],
            user_id=user_id
        )

        await self.kb_service.create_kb(
            kb_name="知识库3",
            kb_type="system",
            icon_key="",
            description="超级管理员、普通用户可查看",
            permit_roles=[user_role],
            user_id=user_id
        )

    async def _init_system_model_and_credential(self):
        deepseek_v4_flash_model = ModelConfig(
            model_name="deepseek-v4-flash",
            model_code="deepseek-v4-flash",
            provider=ModelProvider.DEEPSEEK,
            config_type="system",
            status="active",
            default_api_base="https://api.deepseek.com/v1",
            model_type=ModelType.LLM
        )

        self.db.add(deepseek_v4_flash_model)
        await self.db.commit()
        await self.db.refresh(deepseek_v4_flash_model)

        await self.credential_service.create_credential("",
                                                        CredentialCreate(
                                                            name="deepseek凭据",
                                                            provider="deepseek",
                                                            api_key="sk-edbe2c94099b45b2af70516816b7671a",
                                                            api_base="https://api.deepseek.com/v1",
                                                            models=[
                                                                ModelConfigResponse(
                                                                    model_name="Deepseek大模型",
                                                                    model_code="deepseek-v4-flash",
                                                                    model_type=ModelType.LLM,
                                                                    provider=ModelProvider.DEEPSEEK,
                                                                    default_api_base="https://api.deepseek.com/v1",
                                                                    created_by="",
                                                                    status="active",
                                                                    id=deepseek_v4_flash_model.id,
                                                                    created_at=datetime.now(),
                                                                    config_type=ModelConfigType.SYSTEM,
                                                                )]))
