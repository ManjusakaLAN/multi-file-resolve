from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from schemas.date import CustomDatetime

# 1. 权限基类
class PermissionBase(BaseModel):
    name: str = Field(..., description="权限名称", max_length=64)
    code: str = Field(..., description="权限唯一标识(如: task:delete)", max_length=64)
    resource_type: Optional[str] = Field(default="API", description="资源类型: API/Menu/Button")

# 2. 创建权限
class PermissionCreate(PermissionBase):
    pass

# 3. 更新权限
class PermissionUpdate(BaseModel):
    id: str
    name: Optional[str] = None
    code: Optional[str] = None
    resource_type: Optional[str] = None

# 4. 返回权限信息
class Permission(PermissionBase):
    id: str
    created_at: CustomDatetime

    model_config = ConfigDict(from_attributes=True)

# 1. 角色基类
class RoleBase(BaseModel):
    name: str = Field(..., description="角色名称", max_length=64)
    code: str = Field(..., description="角色编码", max_length=64)
    description: Optional[str] = Field(None, description="角色描述", max_length=255)

# 2. 创建角色
class RoleCreate(RoleBase):
    pass

# 3. 更新角色
class RoleUpdate(BaseModel):
    id:  str
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None

# 4. 返回角色信息 (基础版)
class Role(RoleBase):
    id: str
    created_at: CustomDatetime

    model_config = ConfigDict(from_attributes=True)

# 5. 返回角色详细信息 (包含该角色拥有的权限列表)
class RoleWithPermissions(Role):
    permissions: List[str] = []



