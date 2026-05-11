import logging
from datetime import datetime
from typing import Optional, Sequence
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.config import settings
from core.enum.kb import KBType, KBOpenStatus
from core.exception.llm_exception import KBException
from core.infrastructure.vector_db import MilvusVectorDB
from models.knowledge import KnowledgeBase, role_kb_m2m, UserKnowledgeBase
from models.user import Role, user_role_m2m
from schemas.permission import Role as RoleSchema
from util.convert_util import convert_cn_to_pinyin
from util.random_util import string_random
from schemas.general import PageResponse
from util.db_util import paginate

logger = logging.getLogger(__name__)


class KBService:
    def __init__(self, db: AsyncSession, milvus_client: MilvusVectorDB):
        self.db = db
        self.milvus_client = milvus_client

    async def create_kb(self, kb_name: str, kb_type: KBType | str, icon_key: str, description: str,
                        permit_roles: list[RoleSchema], user_id: str) -> KnowledgeBase:
        # 1. 检查同名
        stmt = select(KnowledgeBase).where(and_(KnowledgeBase.kb_name == kb_name, KnowledgeBase.is_deleted == False))
        if (await self.db.execute(stmt)).scalar_one_or_none():
            raise KBException(message="知识库名称已存在")

        # 2. 创建 Milvus 集合
        collection_name = convert_cn_to_pinyin(kb_name) + "_" + string_random(8)
        self.milvus_client.create_hybrid_collection(
            collection_name=collection_name,
            dim=settings.MILVUS_VECTOR_DIM
        )

        try:
            kb = KnowledgeBase(
                kb_name=kb_name,
                kb_type=kb_type,
                open_status=KBOpenStatus.CLOSED,
                collection_name=collection_name,
                icon_key=icon_key,
                description=description,
                created_by=user_id
            )

            # 3. 系统库权限绑定
            if kb_type == KBType.SYSTEM and permit_roles:
                permit_role_ids = [role['id'] for role in permit_roles]
                role_stmt = select(Role).where(Role.id.in_(permit_role_ids))
                roles = (await self.db.execute(role_stmt)).scalars().all()
                kb.permit_roles = roles

            self.db.add(kb)
            await self.db.commit()
            await self.db.refresh(kb)
            return kb
        except Exception as e:
            await self.db.rollback()
            # 容错：数据库失败时尝试删除已创建的 Milvus 集合
            self.milvus_client.drop_collection(collection_name)
            logger.error(f"创建知识库失败: {e}")
            raise e

    async def permission_query_stmt_combine(self, kb_name: str, user_id: str):
        # 1. 获取当前用户的所有角色编码
        role_stmt = select(Role.code).join(
            user_role_m2m,
            Role.id.__eq__(user_role_m2m.c.role_id)
        ).where(user_role_m2m.c.user_id.__eq__(user_id))

        user_roles = (await self.db.execute(role_stmt)).scalars().all()
        is_admin = "admin" in user_roles

        # 2. 构建基础查询 (过滤已删除)
        stmt = select(KnowledgeBase).where(KnowledgeBase.is_deleted.__eq__(False))

        # 3. 权限过滤逻辑
        if not is_admin:
            # 3.1 获取用户角色关联的所有 KB ID
            kb_ids_stmt = select(role_kb_m2m.c.kb_id).join(
                user_role_m2m,
                user_role_m2m.c.role_id.__eq__(role_kb_m2m.c.role_id)
            ).where(user_role_m2m.c.user_id.__eq__(user_id))

            permitted_kb_ids = (await self.db.execute(kb_ids_stmt)).scalars().all()

            # 3.2 核心权限过滤逻辑拆解：
            # A: 我自己创建的 (拥有最高权限，无视 open_status)
            owner_cond = KnowledgeBase.created_by.__eq__(user_id)

            # B: 系统库且处于 open 状态下的访问策略：
            #    (角色被授权) OR (未绑定任何角色的公开库)
            system_open_cond = and_(
                KnowledgeBase.kb_type.__eq__(KBType.SYSTEM),
                KnowledgeBase.open_status.__eq__(KBOpenStatus.OPEN),
                or_(
                    KnowledgeBase.id.in_(permitted_kb_ids),
                    ~KnowledgeBase.permit_roles.any()
                )
            )

            # C: 个人库 (personal) 的访问策略：
            #    通常个人库只允许创建者看，但如果业务允许角色共享，可以加在此处
            #    目前逻辑：个人库仅限创建者(已在 owner_cond 处理)

            # 最终合并：(我是所有者) OR (是开放状态的系统库且我有权限/库公开)
            stmt = stmt.where(or_(owner_cond, system_open_cond))

        # 4. 业务条件过滤
        if kb_name:
            stmt = stmt.where(KnowledgeBase.kb_name.contains(kb_name))

        # 5. 排序与分页
        stmt = stmt.order_by(KnowledgeBase.created_at.desc())
        return stmt

    async def page_list_kb(self, kb_name: Optional[str],
                           user_id: str, page: int = 1, page_size: int = 10) -> PageResponse:
        """
        分页条件查询知识库 (含复杂权限过滤)
        逻辑补充：系统库如果是 closed 状态，非管理员/创建者不可见
        """
        stmt = await self.permission_query_stmt_combine(kb_name, user_id)
        return await paginate(self.db, stmt, page, page_size)

    async def list_kb(self, kb_name: str, user_id: str) -> Sequence[KnowledgeBase]:
        """
        不分页列表（带权限过滤，符合 SQLAlchemy 2.0 规范格式）
        逻辑：Admin/创建者看全部；普通人仅看 open 状态的系统库（需角色授权或库公开）
        """
        stmt = await self.permission_query_stmt_combine(kb_name, user_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_kb(self, kb_id: str, kb_name: str, open_status: KBOpenStatus | str,
                        icon_key: str, description: str, permit_roles: Optional[list[RoleSchema]]) -> KnowledgeBase:
        """
        更新知识库及其权限
        """
        # 1. 获取原记录 (包含已关联的角色信息)
        stmt = select(KnowledgeBase).options(
            selectinload(KnowledgeBase.permit_roles)  # 关键：提前把关系数据加载到内存
        ).where(
            and_(KnowledgeBase.id.__eq__(kb_id), KnowledgeBase.is_deleted.__eq__(False))
        )
        result = await self.db.execute(stmt)
        kb = result.scalar_one_or_none()

        if not kb:
            raise KBException(message="知识库不存在或已删除")

        # 2. 检查重名 (排除自己且过滤已删除)
        name_stmt = select(KnowledgeBase).where(
            and_(
                KnowledgeBase.kb_name.__eq__(kb_name),
                KnowledgeBase.id.__ne__(kb_id),
                KnowledgeBase.is_deleted.__eq__(False)
            )
        )
        if (await self.db.execute(name_stmt)).scalar_one_or_none():
            raise KBException(message="知识库名称已存在")

        # 3. 更新基础字段
        kb.kb_name = kb_name
        kb.icon_key = icon_key
        kb.description = description

        # 4. 【核心修复】更新权限部分
        # 只有系统库需要处理 permit_role_ids 的角色绑定 和 开放状态
        if kb.kb_type.__eq__(KBType.SYSTEM):

            kb.open_status = open_status

            if permit_roles is not None:
                # 如果传了空列表 []，则代表清空所有角色，变更为公开库
                if len(permit_roles) > 0:
                    permit_role_ids = [role['id'] for role in permit_roles]
                    role_stmt = select(Role).where(Role.id.in_(permit_role_ids))
                    roles = (await self.db.execute(role_stmt)).scalars().all()
                    # 直接赋值，SQLAlchemy 会自动计算 Diff 并更新中间表 role_kb_rel
                    kb.roles = roles
                else:
                    # 传入空列表，清空关联
                    kb.roles = []

        try:
            await self.db.commit()
            await self.db.refresh(kb)
            return kb
        except Exception as e:
            await self.db.rollback()
            logger.error(f"更新知识库失败: {e}")
            raise KBException(message="更新数据库记录失败")

    async def logic_delete_kb(self, kb_id: str):
        """
        软删除知识库
        """
        kb = await self.get_kb_by_id(kb_id)

        try:
            #  数据库软删除
            kb.is_deleted = True

            # 名称携带-delete 后缀 外加随机字符串
            kb.kb_name = f"{kb.kb_name}-delete-{string_random(8)}"
            kb.deleted_date = datetime.now(settings.tz_info)

            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"删除知识库失败: {e}")
            raise KBException(message="删除知识库失败")

    async def get_kb_by_id(self, kb_id: str) -> KnowledgeBase:
        stmt = select(KnowledgeBase).where(and_(KnowledgeBase.id == kb_id, KnowledgeBase.is_deleted == False))
        result = await self.db.execute(stmt)
        kb = result.scalar_one_or_none()
        if not kb:
            raise KBException(message="知识库不存在或已删除")
        return kb

    async def get_kb_detail(self, kb_id: str) -> KnowledgeBase:
        """
        获取知识库详情 包括角色信息Role
        :param kb_id: 知识库ID
        :return: KnowledgeBase 实例 (由 FastAPI 自动转化为 KnowledgeBaseDetail Schema)
        """
        # 1. 构造查询语句，预加载 roles 关系
        stmt = (
            select(KnowledgeBase)
            .options(selectinload(KnowledgeBase.permit_roles))  # 关键：预加载
            .where(
                and_(
                    KnowledgeBase.id.__eq__(kb_id),
                    KnowledgeBase.is_deleted.__eq__(False)
                )
            )
        )

        # 2. 执行查询
        result = await self.db.execute(stmt)
        kb = result.scalar_one_or_none()

        # 3. 校验是否存在
        if not kb:
            raise KBException(message="知识库不存在或已删除")

        return kb

    async def page_list_created_kb(self, kb_name: str, user_id: str, page: int = 1,
                                   page_size: int = 10) -> PageResponse:
        """
        查询用户自身创建的知识库
        :param kb_name:
        :param user_id:
        :param page:
        :param page_size:
        :return:
        """
        stmt = select(KnowledgeBase).where(
            KnowledgeBase.created_by == user_id
        )
        if kb_name:
            stmt = stmt.where(KnowledgeBase.kb_name.contains(kb_name))

        stmt = stmt.order_by(KnowledgeBase.created_at.desc())
        return await paginate(self.db, stmt, page, page_size)

    async def user_join_kb(self, user_id: str, kb_id: str):
        """
        用户加入知识库
        逻辑：校验KB存在性 -> 校验是否已加入 -> 写入关联记录
        """
        # 1. 校验知识库是否存在且未删除
        await self.get_kb_by_id(kb_id)

        # 2. 检查是否已经加入过，防止重复插入
        check_stmt = select(UserKnowledgeBase).where(
            and_(
                UserKnowledgeBase.user_id == user_id,
                UserKnowledgeBase.kb_id == kb_id
            )
        )
        existing = (await self.db.execute(check_stmt)).scalar_one_or_none()
        if existing:
            raise KBException(message="您已在成员列表中，无需重复加入")

        try:
            # 3. 创建加入记录
            user_kb = UserKnowledgeBase(
                user_id=user_id,
                kb_id=kb_id,
                join_at=datetime.now(settings.tz_info),
                is_favorite=False
            )
            self.db.add(user_kb)
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"User {user_id} join KB {kb_id} failed: {e}")
            raise KBException(message="加入知识库失败，请稍后重试")

    async def user_exit_kb(self, user_id: str, kb_id: str):
        """
        用户退出知识库
        逻辑：校验非创建者身份 -> 删除关联记录
        """
        # 1. 获取关联记录
        stmt = select(UserKnowledgeBase).where(
            and_(
                UserKnowledgeBase.user_id == user_id,
                UserKnowledgeBase.kb_id == kb_id
            )
        )
        user_kb = (await self.db.execute(stmt)).scalar_one_or_none()
        if not user_kb:
            raise KBException(message="未找到加入记录")

        # 2. 业务约束：创建者不允许退出，只能走逻辑删除流程
        kb = await self.get_kb_by_id(kb_id)
        if kb.created_by == user_id:
            raise KBException(message="创建者不能退出知识库，请通过删除知识库解散")

        try:
            await self.db.delete(user_kb)
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"User {user_id} exit KB {kb_id} failed: {e}")
            raise KBException(message="退出知识库失败")

    async def user_star_kb(self, user_id: str, kb_id: str):
        """
        用户收藏/星标加入的知识库
        逻辑：必须先加入才能收藏（或者根据业务需求，点击收藏自动触发加入）
        """
        stmt = select(UserKnowledgeBase).where(
            and_(
                UserKnowledgeBase.user_id == user_id,
                UserKnowledgeBase.kb_id == kb_id
            )
        )
        user_kb = (await self.db.execute(stmt)).scalar_one_or_none()

        if not user_kb:
            # 也可以改为自动调用 user_join_kb，这里采用严谨模式：必须先加入
            raise KBException(message="请先加入知识库后再进行收藏")

        try:
            user_kb.is_favorite = True
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Star KB failed: {e}")
            raise KBException(message="操作失败")

    async def user_cancel_star_kb(self, user_id: str, kb_id: str):
        """
        用户取消收藏/星标
        """
        stmt = select(UserKnowledgeBase).where(
            and_(
                UserKnowledgeBase.user_id == user_id,
                UserKnowledgeBase.kb_id == kb_id
            )
        )
        user_kb = (await self.db.execute(stmt)).scalar_one_or_none()

        if user_kb and user_kb.is_favorite:
            try:
                user_kb.is_favorite = False
                await self.db.commit()
            except Exception as e:
                await self.db.rollback()
                logger.error(f"Cancel star KB failed: {e}")
                raise KBException(message="取消收藏失败")

        return True

    async def get_join_kb(self, kb_name: str, user_id: str, page: int = 1,
                          page_size: int = 10) -> PageResponse:
        """
        获取用户加入的知识库列表（包含 is_favorite 字段）
        """
        # 1. 构建查询：显式添加 UserKnowledgeBase.is_favorite 列
        stmt = (
            select(
                KnowledgeBase,
                UserKnowledgeBase.is_favorite.label("is_favorite")  # 显式加 label
            )
            .join(
                UserKnowledgeBase,
                and_(
                    UserKnowledgeBase.kb_id == KnowledgeBase.id,
                    UserKnowledgeBase.user_id == user_id
                )
            )
            .where(KnowledgeBase.is_deleted.__eq__(False))
        )

        # 2. 搜索过滤
        if kb_name:
            stmt = stmt.where(KnowledgeBase.kb_name.contains(kb_name))

        # 3. 排序逻辑
        stmt = stmt.order_by(
            UserKnowledgeBase.is_favorite.desc(),
            KnowledgeBase.created_at.desc()
        )

        # 4. 分页处理
        # 注意：因为 select 了多列，paginate 返回的 items 会是 Tuple 格式: (KnowledgeBase, bool)
        return await paginate(self.db, stmt, page, page_size)