import uuid

from sqlalchemy import Column, String, DateTime, func, Table, ForeignKey
from sqlalchemy.orm import relationship

from core.infrastructure.database import Base

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
    __table_args__ = {'comment': '文件识别任务'}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键id")
    account_name = Column(String(255), unique=True, nullable=False, comment="账号名(用于登录)")
    user_name = Column(String(255), nullable=True, comment="用户名(用户账号展示的名称)")
    email = Column(String(255), nullable=True, comment="邮箱")
    password = Column(String(255), nullable=True, comment="密码")
    password_salt = Column(String(255), nullable=True, comment="密码盐")
    avatar = Column(String(255), nullable=True, comment="头像")
    last_login_at = Column(DateTime, nullable=True, comment="最后登录时间")
    last_login_ip = Column(String(255), nullable=True, comment="最后登录IP")
    status = Column(String(16), nullable=False, server_default="active",
                    comment="用户状态 active激活 / banned 禁用 / closed 注销")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), comment="更新时间")

    # 新增关系映射
    roles = relationship("Role", secondary=user_role_m2m, back_populates="users")


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = {'comment': '角色表'}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="角色ID")
    name = Column(String(64), unique=True, nullable=False, comment="角色名称(如: 管理员)")
    code = Column(String(64), unique=True, nullable=False, comment="角色编码(如: admin)")
    description = Column(String(255), nullable=True, comment="角色描述")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")

    # 关系映射
    users = relationship("User", secondary=user_role_m2m, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permission_m2m, back_populates="roles")


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = {'comment': '权限资源表'}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="权限ID")
    name = Column(String(64), nullable=False, comment="权限名称(如: 任务删除)")
    code = Column(String(64), unique=True, nullable=False, comment="权限唯一标识(如: task:delete)")
    resource_type = Column(String(32), nullable=True, comment="资源类型(API/Menu/Button)")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")

    # 关系映射
    roles = relationship("Role", secondary=role_permission_m2m, back_populates="permissions")
