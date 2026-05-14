from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

from schemas.date import CustomDatetime


# --- 1. 基础模型 (定义通用字段) ---
class FileRecordBase(BaseModel):
    name: str = Field(..., description="上传文件的名称")
    size: int = Field(..., description="文件大小(字节)")
    extension: str = Field(..., description="扩展名")
    mime_type: Optional[str] = Field(None, description="MIME类型")
    md5: Optional[str] = Field(None, description="文件MD5值")
    file_points: float = Field(0, description="当前总积分")


# --- 2. 响应模型 (用于接口返回数据) ---
class FileRecordResponse(FileRecordBase):
    id: str = Field(..., description="主键ID")
    file_key: str = Field(..., description="访问唯一标识")
    created_by: Optional[str] = Field(None, description="创建人ID")
    created_at: CustomDatetime = Field(..., description="创建时间")

    # Pydantic V2 配置：允许从 SQLAlchemy 模型对象转换
    model_config = ConfigDict(from_attributes=True)


# --- 3. 列表查询模型 (用于分页查询过滤) ---
class FileRecordQuery(BaseModel):
    name: Optional[str] = Field(None, description="按文件名模糊搜索")
    extension: Optional[str] = Field(None, description="按扩展名过滤")
    created_by: Optional[str] = Field(None, description="按创建人过滤")
