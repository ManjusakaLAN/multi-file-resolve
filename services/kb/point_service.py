from datetime import datetime, date
from typing import Optional
from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.enum.score import SourceEvent
from models.file import FileRecord
from models.score import ScoreHistory
from models.user import User


class PointService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _add_history_and_update_user(
            self,
            user_id: str | None,
            amount: int,
            change_type: str,
            event: SourceEvent,
            source_id: Optional[str] = None,
            remark: str = ""
    ):
        """内部辅助方法：统一处理余额更新和流水记录"""
        # 1. 使用 select for update 锁定用户行，防止并发余额错误
        stmt = select(User).where(User.id == user_id).with_for_update()
        result = await self.db.execute(stmt)
        user = result.scalar_one()

        # 2. 更新对应余额
        if change_type == "points":
            user.total_points += amount
            balance_after = user.total_points
        else:
            user.contribution_value += amount
            balance_after = user.contribution_value

        # 3. 写入流水
        history = ScoreHistory(
            user_id=user_id,
            change_type=change_type,
            change_amount=amount,
            balance_after=balance_after,
            source_event=event,
            source_id=source_id,
            remark=remark
        )
        self.db.add(history)
        return True

    async def user_login_point_add(self, user_id: str, reward_amount: int = 1):
        """
        处理用户登录积分：每天仅限一次
        """
        today_start = datetime.combine(date.today(), datetime.min.time())

        # 检查今日是否已有登录积分记录
        stmt = select(ScoreHistory).where(
            and_(
                ScoreHistory.user_id == user_id,
                ScoreHistory.source_event == SourceEvent.LOGIN.value,
                ScoreHistory.created_at >= today_start
            )
        )
        existing = await self.db.execute(stmt)
        if existing.scalar_one_or_none():
            return False  # 今日已领取

        await self._add_history_and_update_user(
            user_id=user_id,
            amount=reward_amount,
            change_type="points",
            event=SourceEvent.LOGIN,
            remark=SourceEvent.get_desc(SourceEvent.LOGIN)
        )
        await self.db.commit()
        return True

    async def file_read_point_add(self, user_id: str, file_id: str, reward_amount: int = 1):
        """
        处理阅读文件积分：每个文件对同一个用户仅生效一次
        """
        # 检查该用户是否读过该文件并产生过记录
        stmt = select(ScoreHistory).where(
            and_(
                ScoreHistory.user_id == user_id,
                ScoreHistory.source_event == SourceEvent.FILE_READ.value,
                ScoreHistory.source_id == file_id
            )
        )
        existing = await self.db.execute(stmt)
        if existing.scalar_one_or_none():
            return False

        await self._add_history_and_update_user(
            user_id=user_id,
            amount=reward_amount,
            change_type="points",
            event=SourceEvent.FILE_READ,
            source_id=file_id,
            remark=SourceEvent.get_desc(SourceEvent.FILE_READ)
        )
        await self.db.commit()
        return True

    async def file_like_dislike_point_change(self, operator_id: str, file_id: str, is_like: bool):
        """
        处理点赞/点踩：
        1. 每天上限100次（超过则仅记录流水，积分为0）
        2. 操作影响【文件上传者】的积分
        """
        today_start = datetime.combine(date.today(), datetime.min.time())
        event = SourceEvent.FILE_LIKE if is_like else SourceEvent.FILE_DISLIKE
        point_change = 2 if is_like else -2

        # 1. 获取文件信息（找到上传者）
        file_stmt = select(FileRecord).where(FileRecord.id == file_id)
        file_res = await self.db.execute(file_stmt)
        file = file_res.scalar_one_or_none()
        if not file or not file.created_by:
            return False

        # 2. 统计该操作者今日已点赞/点踩次数
        count_stmt = select(func.count(ScoreHistory.id)).where(
            and_(
                ScoreHistory.user_id == operator_id,  # 注意：统计的是操作者的次数
                ScoreHistory.source_event.in_([SourceEvent.FILE_LIKE.value, SourceEvent.FILE_DISLIKE.value]),
                ScoreHistory.created_at >= today_start
            )
        )
        count_res = await self.db.execute(count_stmt)
        today_count = count_res.scalar() or 0

        # 3. 确定最终变动分值
        actual_change = point_change if today_count < 100 else 0

        # 4. 更新流水及用户余额（被影响的人是 file.created_by）
        # 我们这里记录两条流水或在备注说明：谁为谁贡献了积分
        remark = f"{SourceEvent.get_desc(event)} (来自用户:{operator_id})"
        if today_count >= 100:
            remark += " [今日次数已达上限，积分不计入]"

        await self._add_history_and_update_user(
            user_id=str(file.created_by),
            amount=actual_change,
            change_type="points",
            event=event,
            source_id=file_id,
            remark=remark
        )

        # 如果你想记录操作者的流水（即便他不加分），可以再加一条
        await self.db.commit()
        return True