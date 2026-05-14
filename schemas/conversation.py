from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any
from datetime import datetime
from schemas.date import CustomDatetime


# --- 1. 基础模型 ---
class ChatSessionBase(BaseModel):
    session_type: str = Field("single", description="会话类型: single(库内), global(主页)")
    kb_id: str = Field("", description="关联的知识库ID")
    topic: Optional[str] = Field(None, description="会话主题/标题")


# --- 2. 响应模型 (用于会话列表或详情返回) ---
class ChatSessionResponse(ChatSessionBase):
    id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="所属用户ID")
    create_time: CustomDatetime = Field(..., description="创建时间")

    model_config = ConfigDict(from_attributes=True)


# --- 3. 创建与更新模型 ---
class ChatSessionUpdate(BaseModel):
    topic: str = Field(..., description="修改会话标题")


class ChatSessionQuery(BaseModel):
    session_type: Optional[str] = Field(None, description="按会话类型过滤")
    kb_id: Optional[str] = Field(None, description="按知识库ID过滤")