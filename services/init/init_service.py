import logging
from typing import Optional, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User, Role, Permission
from schemas.user import UserCreate
from services.auth.login_service import LoginService  # 假设你的注册逻辑在此
from services.auth.permission_service import PermissionService

logger = logging.getLogger(__name__)


class InitService:
    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        # 实例化业务 Service，复用其逻辑
        self.perm_service = PermissionService(db, redis)
        # 注意：LoginService 如果需要 Redis，请传入
        self.login_service = LoginService(db, redis)

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