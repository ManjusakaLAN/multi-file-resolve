from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

# ==========================================
# 1. 大模型 (LLMModel) 相关 Schema
# ==========================================

class LLMModelBase(BaseModel):
    model_name: str = Field(..., description="展示名称", examples=["DeepSeek 满血版"])
    model_code: str = Field(..., description="模型标识符", examples=["deepseek-chat"])
    provider: str = Field(..., description="供应商标识", examples=["DeepSeek"])
    config_type: str = Field("system", description="配置来源: system/custom")
    status: str = Field("active", description="状态: active/banned")
    api_base: Optional[str] = Field(None, description="默认API地址")

class LLMModelCreate(LLMModelBase):
    """创建模型时的请求体"""
    pass

class LLMModelResponse(LLMModelBase):
    """模型信息返回（列表/详情）"""
    id: str
    created_by: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# 2. 凭据 (LLMCredential) 相关 Schema
# ==========================================

class LLMCredentialBase(BaseModel):
    name: str = Field(..., description="凭据别名", examples=["我的DeepSeek Key"])
    provider: str = Field(..., description="对应供应商", examples=["DeepSeek"])
    api_base: Optional[str] = Field(None, description="自定义代理地址")
    is_default: bool = Field(False, description="是否为默认凭据")

class LLMCredentialCreate(LLMCredentialBase):
    """用户绑定/创建 Key 时的请求体"""
    api_key: str = Field(..., description="API密钥明文")
    # 可选：创建时直接绑定模型 ID 列表
    model_ids: Optional[List[str]] = Field(default=[], description="初始绑定的模型ID列表")

class LLMCredentialResponse(LLMCredentialBase):
    """凭据信息返回（脱敏处理）"""
    id: str
    user_id: str
    # api_key 绝不能原样返回，建议在 service 层处理或在返回前脱敏
    api_key: str = Field(..., description="脱敏后的KEY", examples=["sk-v...39ds"])
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# 3. 关联与详情 (Complex Relationships)
# ==========================================

class LLMCredentialDetail(LLMCredentialResponse):
    """凭据详情，包含它所绑定的模型列表"""
    models: List[LLMModelResponse] = []

class LLMModelDetail(LLMModelResponse):
    """模型详情，包含关联的凭据（通常用于后台管理查看）"""
    # 注意：面向普通用户时，通常不返回此字段，或仅返回当前用户的关联凭据
    credentials: List[LLMCredentialResponse] = []

class ModelBindCredentialRequest(BaseModel):
    """手动绑定模型与凭据的请求体"""
    model_id: str
    credential_id: str