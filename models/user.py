import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, DateTime, func, Table, ForeignKey, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.infrastructure.database import Base
from models.knowledge import role_kb_m2m
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.knowledge import KnowledgeBase
# --- 多对多关联表保持使用 Table 定义 ---

# 用户与角色关联
user_role_m2m = Table(
    "user_role_rel",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

# 角色与权限关联
role_permission_m2m = Table(
    "role_permission_rel",
    Base.metadata,
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", String(36), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"
    __table_args__ = {'comment': '用户信息表'}

    # 主键
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键id"
    )

    # 必填项 (Mapped[str] 自动推导为 nullable=False)
    account_name: Mapped[str] = mapped_column(
        String(255), unique=True, comment="账号名(用于登录)"
    )
    status: Mapped[str] = mapped_column(
        String(16), server_default="active", comment="用户状态 active激活 / banned 禁用 / closed 注销"
    )

    # 可选项 (Mapped[Optional[str]] 自动推导为 nullable=True)
    user_name: Mapped[Optional[str]] = mapped_column(String(255), comment="用户名")
    email: Mapped[Optional[str]] = mapped_column(String(255), comment="邮箱")
    password: Mapped[Optional[str]] = mapped_column(String(255), comment="密码")
    password_salt: Mapped[Optional[str]] = mapped_column(String(255), comment="密码盐")
    avatar: Mapped[Optional[str]] = mapped_column(String(255), comment="头像")
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="最后登录时间")
    last_login_ip: Mapped[Optional[str]] = mapped_column(String(255), comment="最后登录IP")

    # 审计时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    # 关系映射：Mapped[List["Role"]] 让 IDE 完美识别
    roles: Mapped[List["Role"]] = relationship(
        secondary=user_role_m2m,
        back_populates="users"
    )

    joined_knowledge_bases: Mapped[List["KnowledgeBase"]] = relationship(
        "KnowledgeBase",
        secondary="user_kb_rel",
        back_populates="members"
    )

class Role(Base):
    __tablename__ = "roles"
    __table_args__ = {'comment': '角色表'}

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="角色ID"
    )
    name: Mapped[str] = mapped_column(String(64), unique=True, comment="角色名称")
    code: Mapped[str] = mapped_column(String(64), unique=True, comment="角色编码")
    description: Mapped[Optional[str]] = mapped_column(String(255), comment="角色描述")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系映射
    users: Mapped[List["User"]] = relationship(
        secondary=user_role_m2m,
        back_populates="roles"
    )
    permissions: Mapped[List["Permission"]] = relationship(
        secondary=role_permission_m2m,
        back_populates="roles"
    )
    knowledge_bases: Mapped[List["KnowledgeBase"]] = relationship(
        secondary=role_kb_m2m,
        back_populates="permit_roles"
    )


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = {'comment': '权限资源表'}

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="权限ID"
    )
    name: Mapped[str] = mapped_column(String(64), comment="权限名称")
    code: Mapped[str] = mapped_column(String(64), unique=True, comment="权限唯一标识")
    resource_type: Mapped[Optional[str]] = mapped_column(String(32), comment="资源类型")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系映射
    roles: Mapped[List["Role"]] = relationship(
        secondary=role_permission_m2m,
        back_populates="permissions"
    )
