from pydantic import BaseModel, ConfigDict, field_serializer
from datetime import datetime
from typing import Optional

from core.config import settings
from core.enum.status import FileRecognizeTaskStatus
from schemas.date import CustomDatetime


# 1. 共享属性基类
class FileRecognizeTaskBase(BaseModel):
    file_name: str
    page: Optional[int] = 0
    md5: Optional[str] = None
    md_location: Optional[str] = None
    status: FileRecognizeTaskStatus = FileRecognizeTaskStatus.RESOLVING
    progress: Optional[str] = "0%"

# 2. 创建任务时使用的 Schema (POST)
class FileRecognizeTaskCreate(FileRecognizeTaskBase):
    # 如果创建时只需要文件名，可以把其他字段设为可选
    pass

# 3. 更新任务状态/进度时使用的 Schema (PATCH/PUT)
class FileRecognizeTaskUpdate(BaseModel):
    page: Optional[int] = None
    md_location: Optional[str] = None
    status: Optional[str] = None # 如: finish, failed
    progress: Optional[str] = None

# 4. 响应/读取数据时使用的 Schema (GET/Response)
class FileRecognizeTask(FileRecognizeTaskBase):
    id: str
    created_at: CustomDatetime

    # Pydantic V2 的写法，替代了原来的 class Config: from_attributes = True
    model_config = ConfigDict(from_attributes=True)