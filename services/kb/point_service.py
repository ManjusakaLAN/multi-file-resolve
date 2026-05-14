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

    async def file_like_dislike_point_change(self, operator_id: str, file_id: str, is_like: Optional[bool],
                                             reward_amount: int):
        """
        处理点赞/点踩/取消操作：
        is_like: True(赞), False(踩), None(取消)
        reward_amount: 变动的积分值 (可能是 +1, -1, +2, -2)
        """
        today_start = datetime.combine(date.today(), datetime.min.time())

        # --- 1. 自动判定事件类型 ---
        if is_like is True:
            event = SourceEvent.FILE_LIKE
        elif is_like is False:
            event = SourceEvent.FILE_DISLIKE
        else:
            # 如果 is_like 为 None，说明是取消操作
            # 根据 reward_amount 正负判定是从什么状态取消的
            # 原本点赞(+1)，取消则 -1；原本点踩(-1)，取消则 +1
            event = SourceEvent.FILE_CANCEL_LIKE if reward_amount < 0 else SourceEvent.FILE_CANCEL_DISLIKE

        # 2. 获取文件信息（找到上传者）
        file_stmt = select(FileRecord).where(FileRecord.id == file_id)
        file_res = await self.db.execute(file_stmt)
        file = file_res.scalar_one_or_none()
        if not file or not file.created_by:
            return False

        # 3. 统计该操作者今日【新增评价】的次数（取消操作通常不计入上限限制，或者根据业务需求调整）
        # 这里统计 FILE_LIKE 和 FILE_DISLIKE 两种“主动评价”行为
        count_stmt = select(func.count(ScoreHistory.id)).where(
            and_(
                ScoreHistory.user_id == operator_id,
                ScoreHistory.source_event.in_([SourceEvent.FILE_LIKE.value, SourceEvent.FILE_DISLIKE.value]),
                ScoreHistory.created_at >= today_start
            )
        )
        count_res = await self.db.execute(count_stmt)
        today_count = count_res.scalar() or 0

        # 4. 确定最终变动分值
        # 规则：如果是取消操作(CANCEL)，通常不受100次上限限制（要把分退回）；
        # 如果是新增操作(LIKE/DISLIKE)，受上限限制。
        actual_change = reward_amount
        is_over_limit = False

        if event in [SourceEvent.FILE_LIKE, SourceEvent.FILE_DISLIKE]:
            if today_count >= 100:
                actual_change = 0
                is_over_limit = True

        # 5. 更新流水及用户余额
        remark = f"{SourceEvent.get_desc(event)} (操作人ID:{operator_id})"
        if is_over_limit:
            remark += " [今日次数已达上限，积分不计入]"

        await self._add_history_and_update_user(
            user_id=str(file.created_by),
            amount=actual_change,
            change_type="points",
            event=event,
            source_id=file_id,
            remark=remark
        )

        # 6. 同步更新文件表的总积分字段
        file.file_points = (file.file_points or 0) + actual_change

        await self.db.commit()
        return True

    async def get_user_score(self, user_id):

        stmt = select(User).where(User.id == user_id)
        user = await self.db.execute(stmt)
        user = user.scalar_one_or_none()
        return {
            "total_points": user.total_points,
            "contribution_value": user.contribution_value
        }

    async def get_file_points_rank(self, limit: int = 10):
        """
        获取系统文件积分排名 只需要前10个
        :param limit:
        :return:
        """
        stmt_limit = select(FileRecord).where(FileRecord.is_resolved == True).order_by(FileRecord.file_points.desc()).limit(limit)
        return (await self.db.execute(stmt_limit)).scalars().all()