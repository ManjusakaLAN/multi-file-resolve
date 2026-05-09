import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, func, Table, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.infrastructure.database import Base

# 模型与凭据的中间表 (多对多关联表)
# SQLAlchemy 2.0 依然推荐使用 Table 来定义纯粹的关联表(没有额外业务字段时)
model_credential_m2m = Table(
    "model_config_credential_rel",
    Base.metadata,
    Column("model_config_id", String(36), ForeignKey("model_config.id", ondelete="CASCADE"), primary_key=True,
           comment="模型ID"),
    Column("credential_id", String(36), ForeignKey("credential.id", ondelete="CASCADE"), primary_key=True,
           comment="凭据ID"),
    comment="模型与凭据精确绑定表。例如：用户A指定使用'凭据1'来调用'DeepSeek-V3'模型"
)


class ModelConfig(Base):
    __tablename__ = "model_config"
    __table_args__ = {'comment': '大模型基础配置表。定义系统支持哪些模型，如 GPT-4, DeepSeek-V3'}

    # 主键
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键ID"
    )

    # 必填项 (Mapped[str] 自动等价于 nullable=False)
    model_name: Mapped[str] = mapped_column(
        String(64), comment="展示名称。例如：DeepSeek 满血版, GPT-4o 预览版"
    )
    model_code: Mapped[str] = mapped_column(
        String(64), comment="模型标识符。例如：deepseek-chat, gpt-4o, claude-3-5-sonnet"
    )
    provider: Mapped[str] = mapped_column(
        String(32), index=True, comment="供应商标识。例如：DeepSeek, OpenAI, AliCloud, Anthropic"
    )
    model_type: Mapped[str] = mapped_column(
        String(32), default='llm', comment="模型类型。llm 大语言模型 embedding 嵌入模型 vision 视觉模型"
    )
    config_type: Mapped[str] = mapped_column(
        String(12), default='system', comment="配置来源。system:系统内置(如官方GPT4); custom:用户私有(如接入本地Ollama)"
    )
    status: Mapped[str] = mapped_column(
        String(12), default='active', comment="可用状态。active:激活; banned:禁用"
    )

    # 可选项 (Mapped[str | None] 自动等价于 nullable=True)
    default_api_base: Mapped[str | None] = mapped_column(
        String(255), comment="默认API地址。例如：https://api.deepseek.com"
    )
    created_by: Mapped[str | None] = mapped_column(
        String(36), index=True, comment="创建人ID。系统内置模型此字段为空; 用户自建模型存用户UUID"
    )

    # 时间与审计字段
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )

    # 关系映射 (2.0 风格：明确指定这是一个 Credential 列表)
    credentials: Mapped[list["Credential"]] = relationship(
        secondary=model_credential_m2m,
        back_populates="models",
    )


class Credential(Base):
    __tablename__ = "credential"
    __table_args__ = {'comment': '用户API密钥凭据池。存储用户个人的 API Key，如个人的 DeepSeek Key'}

    # 主键
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键ID"
    )

    # 必填项
    user_id: Mapped[str] = mapped_column(
        String(36), index=True, comment="用户ID。标识该密钥属于哪个用户"
    )
    name: Mapped[str] = mapped_column(
        String(64), comment="凭据别名。由用户起名，例如：我的DeepSeek测试Key, 公司OpenAI正式账户"
    )
    provider: Mapped[str] = mapped_column(
        String(32), comment="对应供应商。一般需与模型表的provider匹配，例如：DeepSeek, OpenAI"
    )
    api_key: Mapped[str] = mapped_column(
        String(512), comment="API密钥。用户填写的 sk-xxxx..."
    )

    # 可选项
    api_base: Mapped[str | None] = mapped_column(
        String(255), comment="代理地址或模型地址。例如：https://api.deepseek.com 或用户的中转URL"
    )

    # 时间与审计字段
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    # 关系映射 (反向绑定)
    models: Mapped[list["ModelConfig"]] = relationship(
        secondary=model_credential_m2m,
        back_populates="credentials",
    )