import uuid

from sqlalchemy import Column, String, DateTime, func

from core.infrastructure.database import Base


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
