import json
import logging
from typing import List, Optional, Sequence
from sqlalchemy import select, delete, and_
from sqlalchemy.orm import selectinload
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from core.exception.middleware_exception import DBException

from models.user import User, Role, Permission, user_role_m2m, role_permission_m2m
from schemas.general import PageResponse
from schemas.user import UserInfo, User as UserSchema, Role as RoleSchema
from util.db_util import paginate

logger = logging.getLogger(__name__)


class PermissionService:
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis
        self.cache_prefix = "user:info:"
        self.expire_time = 3600

    async def get_user_info(self, user_id: str) -> Optional[UserInfo]:
        """获取用户详细信息、角色及权限列表 (带 Redis 缓存)"""
        cache_key = f"{self.cache_prefix}{user_id}"

        # 1. 尝试从缓存读取
        cached_data = await self.redis.get(cache_key)
        if cached_data:
            # 记得处理 bytes 转 str
            data = cached_data.decode('utf-8') if isinstance(cached_data, bytes) else cached_data
            return UserInfo.model_validate(json.loads(data))

        # 2. 数据库查询
        stmt = (
            select(User)
            .where(User.id.__eq__(user_id))
            .options(
                selectinload(User.roles).selectinload(Role.permissions)
            )
        )
        result = await self.db.execute(stmt)
        user_obj = result.scalar_one_or_none()

        if not user_obj:
            return None

        # 3. 提取并去重权限 Code
        # 遍历：用户 -> 多个角色 -> 多个权限
        permission_codes = set()
        for role in user_obj.roles:
            for perm in role.permissions:
                if perm.code:
                    permission_codes.add(perm.code)

        # 4. 组装成 UserInfo 模型
        user_info = UserInfo(
            **UserSchema.model_validate(user_obj).model_dump(),
            roles=[RoleSchema.model_validate(r) for r in user_obj.roles],
            permissions=list(permission_codes)
        )

        # 5. 写入缓存 (过期时间建议与权限列表一致，例如 3600秒)
        await self.redis.setex(
            cache_key,
            self.expire_time,
            user_info.model_dump_json()
        )

        return user_info

    async def clear_user_cache(self, user_id: str):
        """清理特定用户的权限缓存"""
        await self.redis.delete(f"{self.cache_prefix}{user_id}")

    async def create_role(self, name: str, code: str, desc: Optional[str] = None) -> Role:
        """
        新增角色
        :param name: 角色显示名称 例如：管理员
        :param code: 角色代码：例如：admin
        :param desc: 角色描述：例如：管理员角色 拥有所有权限
        :return:
        """
        try:
            role = Role(name=name, code=code, description=desc)
            self.db.add(role)
            await self.db.commit()
            await self.db.refresh(role)
        except Exception as e:
            logger.error(f"新增角色异常: {e}")
            await self.db.rollback()
            raise DBException("新增角色失败,请确认是否已经存在该角色")
        return role

    async def get_roles(self) -> Sequence[Role]:
        result = await self.db.execute(select(Role))
        return result.scalars().all()

    async def delete_role(self, role_id: str):
        """删除角色并级联清理受影响用户的缓存"""
        # 1. 查找受影响的用户 ID
        # 使用 .__eq__ 绕过中间表 Table 对象的类型检查警告
        user_ids_stmt = select(user_role_m2m.c.user_id).where(user_role_m2m.c.ole_id.__eq__(role_id))
        res = await self.db.execute(user_ids_stmt)
        affected_user_ids = res.scalars().all()

        # 2. 删除角色主体
        await self.db.execute(delete(Role).where(Role.id.__eq__(role_id)))
        await self.db.commit()

        # 3. 批量清理缓存
        for uid in affected_user_ids:
            await self.clear_user_cache(str(uid))

    async def update_role(self, role_id: str, name: Optional[str] = None,
                          code: Optional[str] = None, desc: Optional[str] = None) -> Role:
        """
        修改角色信息
        :param role_id: 角色ID
        :param name: 角色显示名称
        :param code: 角色唯一标识
        :param desc: 描述
        """
        try:
            # 1. 获取角色对象
            stmt = select(Role).where(Role.id.__eq__(role_id))
            result = await self.db.execute(stmt)
            role = result.scalar_one_or_none()
            if not role:
                raise DBException("修改失败：目标角色不存在")

            # 2. 动态更新字段
            if name is not None: role.name = name
            if code is not None: role.code = code
            if desc is not None: role.description = desc

            # 3. 提交并刷新
            await self.db.commit()
            await self.db.refresh(role)

            # 4. 关键：清理所有拥有该角色的用户权限缓存
            await self._clear_role_related_users_cache(role_id)

            return role
        except DBException:
            raise
        except Exception as e:
            logger.error(f"修改角色异常: {e}")
            await self.db.rollback()
            raise DBException("修改角色失败，角色名称或代码可能已重复")

    async def create_permission(self, name: str, code: str, res_type: str = "API") -> Permission:
        """
        新增角色权限
        :param name: 权限名称 例如：新增文件
        :param code: 权限代码 例如：file:create
        :param res_type: API/Menu/Button
        :return:
        """
        try:
            perm = Permission(name=name, code=code, resource_type=res_type)
            self.db.add(perm)
            await self.db.commit()
            await self.db.refresh(perm)
        except Exception as e:
            logger.error(f"新增权限异常: {e}")
            raise DBException("新增权限失败,请确认是否已经存在该权限")
        return perm


    async def page_get_permissions(
            self,
            name: Optional[str] = None,
            code: Optional[str] = None,
            page: int = 1,
            page_size: int = 10
    ) -> PageResponse:
        """
        权限分页条件查询 (使用通用分页工具类)
        """
        # 1. 构建基础查询语句
        stmt = select(Permission)

        # 2. 动态添加过滤条件
        filters = []
        if name:
            filters.append(Permission.name.contains(name))
        if code:
            # 也可以直接用 .contains(code)，它会自动帮你加双侧 %
            filters.append(Permission.code.contains(code))

        if filters:
            stmt = stmt.where(and_(*filters))

        # 3. 按创建时间倒序排列
        stmt = stmt.order_by(Permission.created_at.desc())

        # 4. 调用通用分页工具类
        # paginate 内部会自动处理 count 统计和 offset/limit 截断
        return await paginate(self.db, stmt, page, page_size)

    async def assign_roles_to_user(self, user_id: str, role_ids: List[str]):
        """
        用户角色绑定
        一个用户可以有多个角色
        :param user_id:
        :param role_ids:
        :return:
        """
        stmt = select(User).where(User.id.__eq__(user_id)).options(selectinload(User.roles))
        user = (await self.db.execute(stmt)).scalar_one_or_none()
        if not user:
            return

        role_stmt = select(Role).where(Role.id.in_(role_ids))
        roles = (await self.db.execute(role_stmt)).scalars().all()

        user.roles = list(roles)
        await self.db.commit()
        await self.clear_user_cache(user_id)

    async def bind_permissions_to_role(self, role_id: str, perm_ids: List[str]):
        """
        绑定角色 和 权限
        :param role_id:
        :param perm_ids:
        :return:
        """
        stmt = select(Role).where(Role.id.__eq__(role_id)).options(selectinload(Role.permissions))
        role = (await self.db.execute(stmt)).scalar_one_or_none()
        if not role:
            return

        perm_stmt = select(Permission).where(Permission.id.in_(perm_ids))
        perms = (await self.db.execute(perm_stmt)).scalars().all()

        role.permissions = list(perms)
        await self.db.commit()

        # 获取该角色下的所有用户并失效缓存
        u_ids_stmt = select(user_role_m2m.c.user_id).where(user_role_m2m.c.role_id.__eq__(role_id))
        u_ids = (await self.db.execute(u_ids_stmt)).scalars().all()
        for uid in u_ids:
            await self.clear_user_cache(str(uid))

    async def unbind_role_from_user(self, user_id: str, role_id: str):
        """
        解绑 用户 和 角色
        :param user_id: 用户id
        :param role_id: 角色id
        :return:
        """
        # 显式使用 and_ 和 .__eq__ 组合，这是最严谨的写法
        stmt = delete(user_role_m2m).where(
            and_(
                user_role_m2m.c.user_id.__eq__(user_id),
                user_role_m2m.c.role_id.__eq__(role_id)
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()
        await self.clear_user_cache(user_id)

    async def update_permission(self, perm_id: str, name: Optional[str] = None,
                                code: Optional[str] = None, res_type: Optional[str] = None) -> Permission:
        """
        修改权限信息
        :param perm_id:
        :param name:
        :param code:
        :param res_type: API/Menu/Button
        :return:
        """
        # 1. 查询目标是否存在（不涉及事务，放在try外或单独处理）
        stmt = select(Permission).where(Permission.id.__eq__(perm_id))
        result = await self.db.execute(stmt)
        perm = result.scalar_one_or_none()
        if not perm:
            raise DBException("修改失败：目标权限点不存在")

        # 2. 数据库事务操作
        try:
            if name is not None: perm.name = name
            if code is not None: perm.code = code
            if res_type is not None: perm.resource_type = res_type

            await self.db.commit()
            await self.db.refresh(perm)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"数据库更新权限异常: {e}")
            # 这里可以根据 e 的类型进一步判断是否是唯一键冲突（如 Duplicate entry）
            raise DBException("修改权限失败：数据库操作异常，权限代码可能重复")

        # 3. 异步清理缓存（此时数据库事务已成功提交）
        # 即使缓存清理失败，我们通常也不希望给用户报错，因为数据已经改成功了
        try:
            await self._clear_permission_related_users_cache(perm_id)
        except Exception as e:
            # 记录警告日志，但不抛出异常，不阻断返回
            logger.warning(f"权限更新成功，但清理相关用户缓存失败: {e}")

        return perm

    async def delete_permission(self, perm_id: str):
        """删除权限点 (级联清理缓存)"""
        # 1. 验证权限是否存在
        stmt = select(Permission).where(Permission.id.__eq__(perm_id))
        result = await self.db.execute(stmt)
        if not result.scalar_one_or_none():
            raise DBException("删除失败：权限点不存在")

        # 2. 尝试清理受影响用户的缓存
        # 注意：我们将这部分放在 try...except 块内独立处理，不让它影响主事务
        try:
            await self._clear_permission_related_users_cache(perm_id)
        except Exception as e:
            # 缓存清理是“副作用”，报错只记录日志，不抛出异常给用户
            logger.warning(f"删除权限时清理相关用户缓存失败 (perm_id: {perm_id}): {e}")

        # 3. 执行物理删除
        try:
            # 由于你的中间表设置了 ondelete="CASCADE"，数据库会自动清理关联表数据
            await self.db.execute(delete(Permission).where(Permission.id.__eq__(perm_id)))
            await self.db.commit()
        except Exception as e:
            logger.error(f"删除权限数据库操作异常: {e}")
            await self.db.rollback()
            raise DBException("删除权限失败：数据库底层操作错误")

    async def _clear_role_related_users_cache(self, role_id: str):
        """清理所有绑定了指定角色的用户缓存"""
        stmt = select(user_role_m2m.c.user_id).where(user_role_m2m.c.role_id.__eq__(role_id))
        res = await self.db.execute(stmt)
        user_ids = res.scalars().all()
        for uid in user_ids:
            await self.clear_user_cache(str(uid))

    async def _clear_permission_related_users_cache(self, perm_id: str):
        """清理所有绑定了指定权限点（通过角色间接绑定）的用户缓存"""
        try:
            # 1. 确保 select 和 where 中使用 .__eq__() 消除 bool 类型警告
            # 2. join 的第一个参数必须是 Table 对象 (user_role_m2m/role_permission_m2m)
            # 3. join 的第二个参数是显式的关联条件
            stmt = (
                select(user_role_m2m.c.user_id)
                .join(
                    role_permission_m2m,
                    user_role_m2m.c.role_id.__eq__(role_permission_m2m.c.role_id)
                )
                .where(role_permission_m2m.c.permission_id.__eq__(perm_id))
                .distinct()  # 去重，避免一个用户拥有多个角色时重复清理
            )

            res = await self.db.execute(stmt)
            user_ids = res.scalars().all()

            if user_ids:
                for uid in user_ids:
                    # 强制转为 str 确保 Redis Key 类型正确
                    await self.clear_user_cache(str(uid))

        except Exception as e:
            logger.warning(f"清理权限相关用户缓存失败 (perm_id: {perm_id}): {e}")

    async def get_permissions(self, code: Optional[str] = None, name: Optional[str] = None) -> Sequence[Permission]:
        """
        查询所有权限信息 如果传入了code或name 就进行模糊查询
        :param code: 权限编码模糊查询
        :param name: 权限名称模糊查询
        :return: 权限对象列表
        """
        # 1. 构建基础查询
        stmt = select(Permission)

        # 2. 动态构建过滤条件
        filters = []
        if code:
            # 使用 contains 相当于 LIKE '%code%'
            filters.append(Permission.code.contains(code))
        if name:
            filters.append(Permission.name.contains(name))

        # 3. 如果有条件则应用 where
        if filters:
            stmt = stmt.where(and_(*filters))

        # 4. 排序：通常按名称或创建时间排序，方便前端展示
        stmt = stmt.order_by(Permission.name.asc())

        try:
            # 5. 执行查询
            result = await self.db.execute(stmt)
            # scalars().all() 将结果集转换为模型对象列表
            return result.scalars().all()
        except Exception as e:
            logger.error(f"查询权限列表异常: {e}")
            # 这里不需要抛出 DBException，因为查询不到数据返回空列表是正常业务逻辑
            return []

    async def unbind_permission_from_role(self, role_id: str, permission_id: str):
        """
        解绑角色和权限点的关联关系
        :param role_id: 角色ID
        :param permission_id: 权限ID
        """
        try:
            # 1. 执行逻辑删除（中间表记录）
            # 使用 .__eq__() 消除 IDE 的 bool 类型警告
            stmt = delete(role_permission_m2m).where(
                and_(
                    role_permission_m2m.c.role_id.__eq__(role_id),
                    role_permission_m2m.c.permission_id.__eq__(permission_id)
                )
            )
            await self.db.execute(stmt)

            # 2. 提交事务
            await self.db.commit()

            # 3. 关键：清理所有拥有该角色的用户权限缓存
            # 因为角色的权限变少了，必须让相关用户的缓存失效
            await self._clear_role_related_users_cache(role_id)

        except Exception as e:
            logger.error(f"解绑角色权限异常: {e}")
            await self.db.rollback()
            raise DBException("解绑权限失败")

    async def list_role_permission(self, role_id: str) -> List[Permission]:
        """
        传入角色ID 返回角色关联的所有权限信息
        :param role_id: 角色唯一ID
        :return: 权限对象列表
        """
        try:
            # 1. 查询角色并预加载 permissions 关系
            stmt = (
                select(Role)
                .where(Role.id.__eq__(role_id))
                .options(selectinload(Role.permissions))
            )

            result = await self.db.execute(stmt)
            role = result.scalar_one_or_none()

            # 2. 如果角色不存在，返回空列表或抛出异常（根据你的业务需求）
            if not role:
                logger.warning(f"查询角色权限失败：角色ID {role_id} 不存在")
                return []

            # 3. 返回关联的权限列表
            # 这里返回的是 SQLAlchemy 模型对象列表
            return list(role.permissions)

        except Exception as e:
            logger.error(f"获取角色权限列表异常: {e}")
            return []
