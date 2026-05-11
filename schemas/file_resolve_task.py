from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

from core.enum.kb import AuditStatus, AnalysisStatus


# 1. 共享属性基类
class FileResolveTaskBase(BaseModel):
    kb_id: str = Field(..., description="知识库ID")
    file_key: str = Field(..., description="文件访问key/路径", max_length=256)
    audit_status: AuditStatus = Field(
        default=AuditStatus.UNREVIEWED,
        description="审核状态: unreviewed 未审核, pass 通过, review_failed 失败"
    )
    analysis_status: AnalysisStatus = Field(
        default=AnalysisStatus.WAITING,
        description="解析状态: waiting, convert, ocr_resolve, file_chunk, data_clean, embedding, finish, failed"
    )
    audit_opinion: Optional[str] = Field(None, description="审核意见")
    md_file_key: Optional[str] = Field(None, description="md文件key")
    md_file_path: Optional[str] = Field(None, description="md 文件本地路径")


# 2. 创建任务时使用的 Schema
class FileResolveTaskCreate(BaseModel):
    """
    提交文件解析任务时的入参
    """
    kb_id: str = Field(..., description="知识库ID")
    file_key: str = Field(..., description="上传后的文件key")
    # 创建时通常不需要传入状态，由后台逻辑默认设为 pending/waiting


# 3. 更新任务时使用的 Schema
class FileResolveTaskUpdate(BaseModel):
    """
    更新任务状态或审核信息（通常供后台或审核流程使用）
    """
    id: str = Field(..., description="任务主键ID")
    audit_status: Optional[AuditStatus] = Field(None, description="审核状态")
    analysis_status: Optional[AnalysisStatus] = Field(None, description="解析状态")
    audit_opinion: Optional[str] = Field(None, description="审核意见")


# 4. 响应时使用的 Schema
class FileResolveTaskResponse(FileResolveTaskBase):
    """
    返回给前端的解析任务详细信息
    """
    id: str = Field(..., description="主键ID")
    created_by: Optional[str] = Field(None, description="创建人id")
    created_at: datetime = Field(..., description="创建时间")

    # 配置从 SQLAlchemy 模型对象转换
    model_config = ConfigDict(from_attributes=True)