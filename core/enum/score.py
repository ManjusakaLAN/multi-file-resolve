from enum import StrEnum

class SourceEvent(StrEnum):
    LOGIN = "login"
    FILE_READ = "file_read"
    FILE_LIKE = "file_like"
    FILE_DISLIKE = "file_dislike"

    @classmethod
    def get_desc(cls, source_event):
        mapping = {
            cls.LOGIN: "用户登录",
            cls.FILE_READ: "用户阅读文件",
            cls.FILE_LIKE: "用户点赞文件",
            cls.FILE_DISLIKE: "用户取消点赞文件"
        }
        return mapping.get(source_event, "未知事件")