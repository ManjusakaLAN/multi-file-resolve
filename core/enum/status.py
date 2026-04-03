from enum import StrEnum


class FileRecognizeTaskStatus(StrEnum):
    RESOLVING = "resolving"
    FINISH = "finish"
    FAILED = "failed"

    @classmethod
    def get_desc(cls, status):
        mapping = {
            cls.RESOLVING: "解析中",
            cls.FINISH: "已完成",
            cls.FAILED: "任务失败"
        }
        return mapping.get(status, "未知状态")