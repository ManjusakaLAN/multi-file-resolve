from sqlalchemy.ext.asyncio import AsyncSession


class PointService:
    def __init__(self, db: AsyncSession):
        self.db = db



    def user_login_point_add(self):
        """
        处理用户登录时积分的增加 每天仅一次
        处理时需要判断今日是不是以及有记录了
        :return:
        """
        pass

    def file_read_point_add(self):
        """
        处理用户阅读文件时积分的增加
        每个文件对同一个用户仅生效一次
        :return:
        """
        pass

    def file_like_dislike_point_change(self):
        """
        处理用户点赞或取消点赞时积分的增加或减少
        每天同一个用户最多有100次 点赞和点踩操作 超过了这个次数积分变化为0 仅做记录
        这些操作会影响文件上传用户的积分值
        :return:
        """