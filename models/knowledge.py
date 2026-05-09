import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, DateTime, func, Text, ForeignKey, Table, Boolean, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.infrastructure.database import Base
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from models.user import Role

# 1. 角色与知识库关联 (多对多中间表)
# 对于简单的中间表，2.0 依然推荐使用 Table 定义，或者使用新版的声明式映射
role_kb_m2m = Table(
    "role_kb_rel",
    Base.metadata,
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("kb_id", String(36), ForeignKey("knowledge_base.id", ondelete="CASCADE"), primary_key=True),
)


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"
    __table_args__ = {'comment': '知识库配置表'}

    # 主键
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键id"
    )

    # 必填字段 (Mapped[str] 自动识别为 nullable=False)
    kb_name: Mapped[str] = mapped_column(
        String(64), unique=True, comment="知识库名称 用户定义前端显示的名称"
    )
    kb_type: Mapped[str] = mapped_column(
        String(12), default='personal', comment="类型: personal 个人/ system 系统"
    )
    open_status: Mapped[str] = mapped_column(
        String(12), default='closed',
        comment="知识库状态 仅提供给system类型的知识库使用,个人的永远是closed状态: open 开放/ closed 关闭"
    )
    collection_name: Mapped[str] = mapped_column(
        String(64), unique=True, comment="向量数据库集合名称 在向量数据库中的英文名称"
    )

    # 可选字段 (Mapped[Optional[str]] 自动识别为 nullable=True)
    icon_key: Mapped[Optional[str]] = mapped_column(
        String(256), default='', comment="图标key"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, comment="描述"
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否删除"
    )
    deleted_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime, comment="删除时间"
    )

    # 审计字段
    created_by: Mapped[Optional[str]] = mapped_column(
        String(36), comment="创建人id"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )

    # 2.0 关系映射：显式声明 Mapped[List["Role"]]
    # 注意：如果 Role 类在其他文件，记得处理循环导入或使用字符串引用
    permit_roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary=role_kb_m2m,
        back_populates="knowledge_bases"
    )