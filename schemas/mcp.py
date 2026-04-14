from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

from core.enum.mcp import McpConnectedStatus


# 1. 共享属性基类
class McpServerBase(BaseModel):
    name: str = Field(..., description="mcp服务名称", max_length=64)
    mcp_type: str = Field(..., description="mcp服务类型 (sse / streamable_http)", max_length=32)
    mcp_url: str = Field(..., description="mcp服务地址", max_length=512)
    connected_status: McpConnectedStatus = Field(default=McpConnectedStatus.NOT_CONNECTED, description="mcp服务状态 (0:未连接, 1:已连接)")
    description: Optional[str] = Field(None, description="mcp服务描述")


# 2. 创建时使用的 Schema
class McpServerCreate(McpServerBase):
    """
    创建 MCP 服务配置时的入参
    """
    # 如果创建时需要显式传入 created_by，可以取消下面注释
    # created_by: str = Field(..., description="创建人id")
    pass


# 3. 更新时使用的 Schema
class McpServerUpdate(BaseModel):
    """
    更新 MCP 服务配置时的入参，所有字段设为可选
    """
    id: str = Field(..., description="主键ID")
    name: Optional[str] = Field(None, max_length=64)
    mcp_type: Optional[str] = Field(None, max_length=32)
    mcp_url: Optional[str] = Field(None, max_length=512)
    connected_status: Optional[McpConnectedStatus] = Field(None)
    description: Optional[str] = Field(None)


# 4. 响应时使用的 Schema
class McpServerResponse(McpServerBase):
    """
    返回给前端的详细信息
    """
    id: str = Field(..., description="主键ID")
    created_by: str = Field(..., description="创建人id")
    created_at: datetime = Field(..., description="创建时间")

    # Pydantic V2 配置：允许从 SQLAlchemy 模型对象转换
    model_config = ConfigDict(from_attributes=True)