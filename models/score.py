import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, ForeignKey, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from core.infrastructure.database import Base


class ScoreHistory(Base):
    __tablename__ = "score_history"
    __table_args__ = {'comment': '分值(积分/贡献值)变更流水表'}

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键id"
    )

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, comment="用户id"
    )

    # 变动类型标识
    change_type: Mapped[str] = mapped_column(
        String(20), comment="变动类型: points (积分) / contribution (贡献值)"
    )

    # 变动数值
    change_amount: Mapped[int] = mapped_column(
        Integer, comment="变动数额: 正数为加, 负数为减"
    )

    # 变动后余额 (重要：用于快速对账和排查数据问题)
    balance_after: Mapped[int] = mapped_column(
        Integer, comment="变动后的实时余额"
    )

    # 业务来源信息
    source_event: Mapped[str] = mapped_column(
        String(64), comment="触发事件: sign_in(签到), upload_file(上传), qa_bonus(问答奖励)等"
    )

    source_id: Mapped[Optional[str]] = mapped_column(
        String(36), comment="关联业务ID: 如关联的文件ID、任务ID等"
    )

    remark: Mapped[Optional[str]] = mapped_column(
        String(255), comment="备注/详情说明"
    )

    # 审计时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="记录时间"
    )
