import uuid
from sqlalchemy import Column, String, DateTime, func, Table, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from core.infrastructure.database import Base

# 模型与凭据的中间表
model_credential_m2m = Table(
    "llm_model_credential_rel",
    Base.metadata,
    Column("model_id", String(36), ForeignKey("llm_model.id", ondelete="CASCADE"), primary_key=True, comment="模型ID"),
    Column("credential_id", String(36), ForeignKey("llm_credential.id", ondelete="CASCADE"), primary_key=True, comment="凭据ID"),
    comment="模型与凭据精确绑定表。例如：用户A指定使用'凭据1'来调用'DeepSeek-V3'模型"
)

class LLMModel(Base):
    __tablename__ = "llm_model"
    __table_args__ = {'comment': '大模型基础配置表。定义系统支持哪些模型，如 GPT-4, DeepSeek-V3'}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键ID")
    model_name = Column(String(64), nullable=False, comment="展示名称。例如：DeepSeek 满血版, GPT-4o 预览版")
    model_code = Column(String(64), nullable=False, comment="模型标识符。例如：deepseek-chat, gpt-4o, claude-3-5-sonnet")
    provider = Column(String(32), nullable=False, index=True, comment="供应商标识。例如：DeepSeek, OpenAI, AliCloud, Anthropic")
    model_type = Column(String(32), default='llm',nullable=False, comment="模型类型。llm 大语言模型 embedding 嵌入模型 vision 视觉模型")
    default_api_base = Column(String(255), nullable=True, comment="默认API地址。例如：https://api.deepseek.com")
    # 配置类型
    config_type = Column(String(12), default='system', comment="配置来源。system:系统内置(如官方GPT4); custom:用户私有(如接入本地Ollama)")
    # 状态
    status = Column(String(12), default='active', comment="可用状态。active:激活; banned:禁用")

    # 自动化映射
    credentials = relationship(
        "LLMCredential",
        secondary=model_credential_m2m,
        back_populates="models",
    )

    created_by = Column(String(36), index=True, comment="创建人ID。系统内置模型此字段为空; 用户自建模型存用户UUID")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")


class LLMCredential(Base):
    __tablename__ = "llm_credential"
    __table_args__ = {'comment': '用户API密钥凭据池。存储用户个人的 API Key，如个人的 DeepSeek Key'}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键ID")
    user_id = Column(String(36), nullable=False, index=True, comment="用户ID。标识该密钥属于哪个用户")
    name = Column(String(64), nullable=False, comment="凭据别名。由用户起名，例如：我的DeepSeek测试Key, 公司OpenAI正式账户")

    provider = Column(String(32), nullable=False, comment="对应供应商。一般需与模型表的provider匹配，例如：DeepSeek, OpenAI")
    api_key = Column(String(512), nullable=False, comment="API密钥。用户填写的 sk-xxxx...")
    api_base = Column(String(255), nullable=True, comment="代理地址或模型地址。例如：https://api.deepseek.com 或用户的中转URL")

    # 自动化映射
    models = relationship(
        "LLMModel",
        secondary=model_credential_m2m,
        back_populates="credentials",
    )

    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")