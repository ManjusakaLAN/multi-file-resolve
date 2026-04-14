import uuid

from sqlalchemy import Column, String, Integer, DateTime, func
from core.infrastructure.database import Base


class Dict(Base):
    __tablename__ = "sys_dict"
    __table_args__ = {'comment': '字典信息记录'}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键id")
    dict_code = Column(String(50), nullable=False, index=True, comment="字典编码 例如: user_status")
    label = Column(String(100), comment="字典名称/标签 例如: 激活/禁用")
    value = Column(String(100), comment="字典键值 例如: active/banner")
    sort = Column(Integer, default=0, comment="排序")
    is_system = Column(Integer, default=1, comment="是否系统内置 0 否 1 是")
