import uuid
from sqlalchemy import Column, String, Integer, DateTime, func, Text, ForeignKey, Table, Boolean
from sqlalchemy.orm import relationship

from core.infrastructure.database import Base

# 角色与知识库关联
role_kb_m2m = Table(
    "role_kb_rel",
    Base.metadata,
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("kb_id", String(36), ForeignKey("knowledge_base.id", ondelete="CASCADE"), primary_key=True),
)


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"
    __table_args__ = {'comment': '知识库配置表'}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键id")
    kb_name = Column(String(64), nullable=False, unique=True, comment="知识库名称 用户定义前端显示的名称")
    kb_type = Column(String(12), nullable=False, default='personal', comment="类型: personal 个人/ system 系统")
    open_status = Column(String(12), nullable=False, default='closed',
                         comment="知识库状态 仅提供给system类型的知识库使用,个人的永远是closed状态: open 开放/ closed 关闭")
    collection_name = Column(String(64), nullable=False, unique=True,
                             comment="向量数据库集合名称 在向量数据库中的英文名称")
    icon_key = Column(String(256), nullable=True, default='', comment="图标key")
    description = Column(Text, nullable=True, comment="描述")
    is_deleted = Column(Boolean, default=False, comment="是否删除")
    deleted_date = Column(DateTime, nullable=True, comment="删除时间")

    # 审计字段
    created_by = Column(String(36), nullable=True, comment="创建人id")
    created_at = Column(DateTime, nullable=False, default=func.now(), comment="创建时间")

    # 关系映射：哪些角色可以访问此知识库
    permit_roles = relationship("Role", secondary="role_kb_rel", back_populates="knowledge_bases")
