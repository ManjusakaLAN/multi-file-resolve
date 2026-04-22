from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from core.enum.model import ModelConfigType, ModelType, ModelProvider
from schemas.date import CustomDatetime


# ==========================================
# 1. 大模型 (LLMModel) 相关 Schema
# ==========================================

class LLMModelBase(BaseModel):
    model_name: str = Field(..., description="展示名称", examples=["DeepSeek 满血版"])
    model_code: str = Field(..., description="模型标识符", examples=["deepseek-chat"])
    provider: str = Field(..., description="供应商标识", examples=["DeepSeek"])
    default_api_base: Optional[str] = Field(None, description="默认API地址")
    model_type: Optional[ModelType | str] = Field("llm", description="模型类型: llm/embedding/vision")
    config_type: Optional[ModelConfigType | str] = Field("system", description="配置来源: system/custom")
    status: str = Field("active", description="状态: active/banned")


class LLMModelCreate(LLMModelBase):
    """创建模型时的请求体"""
    pass


class LLMModelUpdate(LLMModelBase):
    """更新模型时的请求体"""
    id: str = Field(..., description="模型ID")


class LLMModelResponse(LLMModelBase):
    """模型信息返回（列表/详情）"""
    id: str
    created_by: Optional[str] = None
    created_at: CustomDatetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 2. 凭据 (LLMCredential) 相关 Schema
# ==========================================

class LLMCredentialBase(BaseModel):
    name: str = Field(..., description="凭据别名", examples=["我的DeepSeek Key"])
    provider: str = Field(..., description="对应供应商", examples=["DeepSeek"])
    api_base: Optional[str] = Field(None, description="自定义代理地址")


class LLMCredentialCreate(LLMCredentialBase):
    """用户绑定/创建 Key 时的请求体"""
    api_key: str = Field(..., description="API密钥明文")
    # 可选：创建时直接绑定模型 ID 列表
    models: Optional[List[LLMModelResponse]] = Field(default=[], description="初始绑定的模型ID列表")


class LLMCredentialUpdate(LLMCredentialBase):
    """用户更新 Key 时的请求体"""
    id: str = Field(..., description="凭据ID")
    api_key: Optional[str] = Field(None, description="API密钥明文")
    models: Optional[List[LLMModelResponse]] = Field(default=[], description="初始绑定的模型ID列表")


class LLMCredentialResponse(LLMCredentialBase):
    """凭据信息返回（脱敏处理）"""
    id: str
    user_id: str
    # api_key 不能原样返回，在 service 层处理或在返回前脱敏
    api_key: str = Field(..., description="脱敏后的KEY", examples=["sk-v...39ds"])
    created_at: CustomDatetime
    updated_at: CustomDatetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 3. 关联与详情 (Complex Relationships)
# ==========================================

class LLMCredentialDetail(LLMCredentialResponse):
    """凭据详情，包含它所绑定的模型列表"""
    models: List[LLMModelResponse] = []

class ModelInvokeInfo(BaseModel):
    """模型调用信息"""
    model_id: str = Field(default= "", description="模型ID")
    base_url: str = Field(default= "", description="API调用地址")
    api_key: str = Field(default= "", description="API密钥")
    provider: ModelProvider | str = Field(default= "", description="模型类型")
    model_type: ModelType | str= Field(default= "", description="模型类型")