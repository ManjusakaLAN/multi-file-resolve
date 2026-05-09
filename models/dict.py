import uuid
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from core.infrastructure.database import Base


class Dict(Base):
    __tablename__ = "sys_dict"
    __table_args__ = {'comment': '字典信息记录'}

    # 主键 ID
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="主键id"
    )

    # 必填项 (Mapped[str] 会自动推导出 nullable=False)
    dict_code: Mapped[str] = mapped_column(
        String(50),
        index=True,
        comment="字典编码 例如: user_status"
    )

    # 可选项 (Mapped[str | None] 会自动推导出 nullable=True)
    label: Mapped[str | None] = mapped_column(
        String(100),
        comment="字典名称/标签 例如: 激活/禁用"
    )

    value: Mapped[str | None] = mapped_column(
        String(100),
        comment="字典键值 例如: active/banner"
    )

    # 整数类型及默认值
    sort: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="排序"
    )

    is_system: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="是否系统内置 0 否 1 是"
    )
