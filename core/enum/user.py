from enum import StrEnum

class UserStatus(StrEnum):
    ACTIVE = "active"
    BANNED = "banned"
    CLOSED = "closed"

    @classmethod
    def get_desc(cls, status):
        mapping = {
            cls.ACTIVE: "正常",
            cls.BANNED: "禁用",
            cls.CLOSED: "注销"
        }
        return mapping.get(status, "未知状态")
