from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, EmailStr

from core.enum.user import UserStatus
from schemas.date import CustomDatetime
from schemas.permission import Role, Permission


# 1. 共享属性基类 (定义公共字段)
class UserBase(BaseModel):
    account_name: str = Field(..., description="账号名(用于登录)", min_length=3, max_length=50)
    user_name: Optional[str] = Field(..., description="展示名称")
    email: Optional[str] = Field(..., description="邮箱地址")
    avatar: Optional[str] = Field(..., description="头像URL")
    status: str = Field(default="active", description="状态: active/banned/closed")

# 2. 创建用户时使用的 Schema (注册/后台添加)
class UserCreate(UserBase):
    password: str = Field(..., description="原始密码", min_length=6)
    confirm_password: str = Field(..., description="确认密码")
    code:  Optional[str] = Field(default="", description="验证码")
    # 创建时通常不需要 salt、ip 等，由后端自动生成

# 3. 更新用户信息时使用的 Schema (PATCH)
class UserUpdate(BaseModel):
    id:  str
    user_name: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    status: Optional[UserStatus | str] = None
    # 注意：修改密码通常建议单独开一个接口，不放在通用的 Profile 更新里

# 4. 登录成功或读取详细信息时返回的 Schema (不包含密码和盐)
class User(UserBase):
    id: str
    last_login_at: Optional[CustomDatetime] = None
    last_login_ip: Optional[str] = None
    created_at: CustomDatetime
    updated_at: CustomDatetime

    # Pydantic V2 配置：允许从 SQLAlchemy 模型对象直接转换
    model_config = ConfigDict(from_attributes=True)

# 5. 内部使用的 Schema (如果某些业务逻辑需要校验密码盐)
class UserInDB(User):
    password: str
    password_salt: str

class UserInfo(User):  # 继承你之前的 User 展示模型
    roles: List[Role] = []
    permissions: List[str] = []