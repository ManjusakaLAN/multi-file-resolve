import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import String, Integer, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from core.infrastructure.database import Base


class ChatSession(Base):
    __tablename__ = "chat_session"
    __table_args__ = {'comment': '知识库对话会话表'}

    # 主键 ID
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="主键id"
    )

    # 用户隔离
    user_id: Mapped[str] = mapped_column(
        String(64),
        index=True,
        comment="用户id"
    )

    # 会话类型
    session_type: Mapped[str] = mapped_column(
        String(20),
        default="single",
        comment="知识库内single 主页global"
    )

    # 关联知识库 (如果是全局对话，该值可能为空字符串或特定标识)
    kb_id: Mapped[str] = mapped_column(
        String(36),
        default="",
        comment="知识库id"
    )

    # 会话标题
    topic: Mapped[str | None] = mapped_column(
        String(255),
        comment="会话主题,同时也作为标题显示"
    )

    # 状态与时间
    is_deleted: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="是否逻辑删除 0 否 1 是"
    )

    create_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        comment="创建时间"
    )


class ChatMessage(Base):
    __tablename__ = "chat_message"
    __table_args__ = {'comment': '知识库对话消息记录表'}

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="消息记录id"
    )

    # 外键关联
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_session.id"),
        index=True,
        comment="所属会话id"
    )

    # 角色 (user, assistant, system)
    role: Mapped[str | None] = mapped_column(
        String(20),
        comment="角色"
    )

    # 消息正文
    content: Mapped[str | None] = mapped_column(
        Text,
        comment="消息正文内容"
    )

    # 检索溯源上下文 (JSON 存储)
    # 存储召回文件的聚类快照：[{file_id, file_name, is_like, chunks: [...]}]
    source_context: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="存储召回文件的聚类快照"
    )

    create_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        comment="消息生成时间"
    )