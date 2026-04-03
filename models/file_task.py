import uuid

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func

from core.enum.status import FileRecognizeTaskStatus
from core.infrastructure.database import Base


class FileRecognizeTask(Base):
    __tablename__ = "file_recognize_task"
    __table_args__ = {'comment': '文件识别任务'}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键id")
    file_name = Column(String(255), nullable=False, comment="文件名")
    page = Column(Integer, nullable=True, server_default="0", comment="页数")
    md5 = Column(String(255), nullable=True, comment="文件md5")
    md_location = Column(String(255), nullable=True, comment="解析后最终的md文件的存储位置")
    status = Column(String(64), nullable=False, server_default=FileRecognizeTaskStatus.RESOLVING,
                    comment="任务状态 resolving处理中 finish完成 failed失败")
    progress = Column(String(32), nullable=True, server_default="0%", comment="任务进度")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

class FileRecognizeWorker(Base):
    __tablename__ = "file_recognize_worker"
    __table_args__ = {'comment': '文件识别工作'}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键id")
    ref_task_id = Column(String(36), nullable=False, comment="关联的任务id")
    order = Column(Integer, nullable=False, server_default="0", comment="任务顺序")
    resolve_pdf_path = Column(String(255), nullable=True, comment="待处理的pdf文件的存储位置")
    resolve_md_path = Column(String(255), nullable=True, comment="处理后的md文件的存储位置")
    status = Column(String(64), nullable=False, server_default="waiting",
                    comment="任务状态 waiting待处理 resolving处理中 finish完成 failed失败")
    error_message = Column(Text, nullable=True, comment="错误信息")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")