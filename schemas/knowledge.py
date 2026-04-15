from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

from core.enum.kb import KBOpenStatus
from schemas.permission import Role


# 1. 共享属性基类
class KnowledgeBaseBase(BaseModel):
    kb_name: str = Field(..., description="知识库名称(用户定义前端显示的名称)", max_length=64)
    kb_type: str = Field(default='personal', description="类型: personal 个人 / system 系统", max_length=12)
    open_status: str = Field(default='closed', description="状态: open 开放 / closed 关闭 (仅系统库可用)", max_length=12)
    collection_name: str = Field(..., description="向量数据库集合名称(英文标识)", max_length=64)
    icon_key: Optional[str] = Field(default='', description="图标key", max_length=256)
    description: Optional[str] = Field(None, description="知识库描述")


# 2. 创建知识库时使用的 Schema (POST)
class KnowledgeBaseCreate(BaseModel):
    """
    创建知识库时的入参。
    """
    kb_name: str = Field(..., description="知识库名称(用户定义前端显示的名称)", max_length=64)
    kb_type: str = Field(default='personal', description="类型: personal 个人 / system 系统", max_length=12)
    icon_key: Optional[str] = Field(default='', description="图标key", max_length=256)
    description: Optional[str] = Field(None, description="知识库描述")
    permit_role_ids: Optional[List[str]] = Field([], description="知识库角色权限 id数组")

# 3. 更新知识库信息时使用的 Schema (PATCH/PUT)
class KnowledgeBaseUpdate(BaseModel):
    """
    更新知识库时的入参。支持局部更新。
    注意：collection_name 通常在创建后不建议修改。
    """
    kb_id: str = Field(..., description="主键ID")
    kb_name: Optional[str] = Field(None, max_length=64)
    open_status: Optional[str | KBOpenStatus] = Field(None, max_length=12)
    icon_key: Optional[str] = Field(None, max_length=256)
    description: Optional[str] = Field(None)
    permit_role_ids: Optional[List[str]] = Field([], description="知识库角色权限 id数组")


# 4. 接口返回/读取详细信息时使用的 Schema (Response)
class KnowledgeBaseResponse(KnowledgeBaseBase):
    """
    返回给前端的知识库详细信息。
    """
    id: str = Field(..., description="主键ID")
    is_deleted: bool = Field(False, description="是否删除")
    deleted_date: Optional[datetime] = Field(None, description="删除时间")
    created_by: Optional[str] = Field(None, description="创建人id")
    created_at: datetime = Field(..., description="创建时间")

    # Pydantic V2 配置：允许从 SQLAlchemy 模型对象直接转换
    model_config = ConfigDict(from_attributes=True)

# 5. 知识库详情 包括权限信息 Role
class KnowledgeBaseDetail(KnowledgeBaseResponse):
    """
    知识库详情 包括权限信息 Role
    """
    permit_roles: Optional[List[Role]] = Field([], description="知识库角色权限 id数组")
