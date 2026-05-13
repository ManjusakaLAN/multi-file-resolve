import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, func, ForeignKey, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.infrastructure.database import Base


class FileRecord(Base):
    __tablename__ = "file_record"
    __table_args__ = {'comment': '文件上传信息记录'}

    # 主键 ID：使用 Mapped[str]
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="主键id"
    )

    # 必填字段：Mapped[str] 或 Mapped[int] 自动推导为 nullable=False
    file_key: Mapped[str] = mapped_column(
        String(255),
        comment="上传文件的访问唯一标识,如:common/api.png"
    )

    name: Mapped[str] = mapped_column(
        String(255),
        comment="上传文件的名称"
    )

    size: Mapped[int] = mapped_column(
        Integer,
        comment="上传文件的大小,单位:字节"
    )

    extension: Mapped[str] = mapped_column(
        String(255),
        comment="上传文件的扩展名,例如: pdf,txt"
    )

    # 可选字段：使用 Mapped[type | None] 自动推导为 nullable=True
    mime_type: Mapped[str | None] = mapped_column(
        String(255),
        comment="上传文件的MIME类型,例如: text/plain"
    )

    md5: Mapped[str | None] = mapped_column(
        String(255),
        comment="上传文件的MD5值"
    )

    # 审计字段
    created_by: Mapped[str | None] = mapped_column(
        String(36),
        comment="创建人id"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        comment="创建时间"
    )

    # 知识库id
    kb_id: Mapped[str] = mapped_column(
        String(36),nullable=True ,comment="知识库id"
    )

    file_points: Mapped[int] = mapped_column(
        Float, server_default="0", comment="当前总积分"
    )

    # 新增外键关联到 Folder
    folder_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("folder.id"), nullable=True, comment="所属文件夹id, 为空表示在根目录"
    )

    # 是否解析完成
    is_resolved: Mapped[bool] = mapped_column(
        Boolean, server_default="0", comment="是否解析完成"
    )

    # 关系映射
    folder: Mapped[Optional["Folder"]] = relationship("Folder", back_populates="files")
