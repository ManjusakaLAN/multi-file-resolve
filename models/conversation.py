from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Integer
from datetime import datetime
import uuid

from core.infrastructure.database import Base


class ChatSession(Base):
    __tablename__ = "chat_session"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(64), index=True, nullable=False)
    session_type = Column(String(20), default="single", comment="知识库内single 主页global")  # SINGLE, GLOBAL
    topic = Column(String(255), comment="会话主题,同时也作为标题显示")
    is_deleted = Column(Integer, default=0)
    create_time = Column(DateTime, default=datetime.now)


class ChatMessage(Base):
    __tablename__ = "chat_message"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("chat_session.id"), index=True)
    role = Column(String(20), nullable=True, comment="角色")  # user, assistant, system
    content = Column(Text)
    # 存储召回文件的聚类快照：[{file_id, file_name, is_like, chunks: [...]}]
    source_context = Column(JSON, nullable=True)
    create_time = Column(DateTime, default=datetime.now)
