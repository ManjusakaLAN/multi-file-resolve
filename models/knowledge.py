import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, DateTime, func, Text, ForeignKey, Table, Boolean, Column, Integer
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

    members: Mapped[List["User"]] = relationship(
        "User",
        secondary="user_kb_rel",
        back_populates="joined_knowledge_bases"
    )


# models/knowledge.py (或单独的文件)

class UserKnowledgeBase(Base):
    __tablename__ = "user_kb_rel"
    __table_args__ = {'comment': '用户与知识库加入关联表'}

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    kb_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_base.id", ondelete="CASCADE"), primary_key=True
    )

    # 扩展字段
    join_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="加入时间")
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否收藏/星标")


# 知识库 文件解析任务
class FileResolveTask(Base):
    __tablename__ = "file_resolve_task"
    __table_args__ = {'comment': '知识库 文件解析任务'}

    # 主键
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键id"
    )

    # 知识库id
    kb_id: Mapped[str] = mapped_column(
        String(36),
        comment="知识库id"
    )

    # 审核状态
    audit_status: Mapped[str] = mapped_column(
        String(32), default='pending', comment="审核状态: 未审核 unreviewed 审核通过 pass 审核失败 review_failed"
    )

    # 解析状态
    analysis_status: Mapped[str] = mapped_column(
        String(32), default='pending',
        comment="解析状态:waiting 等待解析中 convert 文件转换中 ocr_resolve ocr解析中 file_chunk 文件切片中 data_clean 数据清洗中 embedding 嵌入中 finish 完成 failed 失败"
    )

    # 审核意见
    audit_opinion: Mapped[str] = mapped_column(
        Text, comment="审核意见 包括通过的和不通过的"
    )

    # 文件访问key
    file_key: Mapped[str] = mapped_column(
        String(256), comment="文件访问key"
    )

    # 审计字段
    created_by: Mapped[Optional[str]] = mapped_column(
        String(36), comment="创建人id"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )

    # md文件key
    md_file_key: Mapped[str] = mapped_column(
        String(256), comment="md文件key"
    )

    # md 文件本地路径
    md_file_path: Mapped[str] = mapped_column(
        String(256), comment="md 文件本地路径"
    )


class FileSliceRecord(Base):
    __tablename__ = "file_slice_record"
    __table_args__ = {'comment': '知识库 文件切片记录'}
    # 主键
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键id"
    )

    # 文件id
    file_id: Mapped[str] = mapped_column(
        String(36), comment="文件id"
    )

    # 切片id
    slice_id: Mapped[str] = mapped_column(
        String(36), comment="切片id"
    )

    # 切片内容
    slice_content: Mapped[str] = mapped_column(
        Text, comment="切片内容"
    )

    # 切片长度
    slice_length: Mapped[int] = mapped_column(
        Integer, comment="切片长度"
    )

    # 是否已经完成嵌入
    is_embedded: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否已经完成嵌入"
    )

    # 是否已经完成清洗
    is_cleaned: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否已经完成清洗"
    )

