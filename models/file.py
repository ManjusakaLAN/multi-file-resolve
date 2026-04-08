import uuid
from typing import Any
from sqlalchemy import Column, String, Integer, DateTime, func
from core.infrastructure.database import Base


class FileRecord(Base):
    __tablename__ = "file_record"
    __table_args__ = {'comment': '文件上传信息记录'}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键id")
    file_key = Column(String(255), nullable=False, comment="上传文件的访问唯一标识,如:common/api.png")
    name = Column(String(255), nullable=False, comment="上传文件的名称")
    size = Column(Integer, nullable=False, comment="上传文件的大小,单位:字节")
    extension = Column(String(255), nullable=False, comment="上传文件的扩展名,例如: pdf,txt")
    mime_type = Column(String(255), nullable=True, comment="上传文件的MIME类型,例如: text/plain")
    md5 = Column(String(255), nullable=True, comment="上传文件的MD5值")
    # 审计字段
    created_by = Column(String(36), nullable=True, comment="创建人id")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")

    def __init__(self, **kw: Any):
        super().__init__(**kw)
