from enum import StrEnum


class KBType(StrEnum):
    PERSONAL = "personal"
    SYSTEM = "system"

    @classmethod
    def get_desc(cls, kb_type):
        mapping = {
            cls.PERSONAL: "个人知识库",
            cls.SYSTEM: "系统知识库"
        }
        return mapping.get(kb_type, "未知类型")


class KBOpenStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"

    @classmethod
    def get_desc(cls, status):
        mapping = {
            cls.OPEN: "开放",
            cls.CLOSED: "关闭"
        }
        return mapping.get(status, "未知状态")
