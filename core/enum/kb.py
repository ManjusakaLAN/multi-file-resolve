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


class AuditStatus(StrEnum):
    """审核状态枚举"""
    UNREVIEWED = "unreviewed"
    PASS = "pass"
    REVIEW_FAILED = "review_failed"
    NO_NEED_REVIEWED = "no_need_reviewed"

    @classmethod
    def get_desc(cls, status):
        mapping = {
            cls.UNREVIEWED: "未审核",
            cls.PASS: "审核通过",
            cls.REVIEW_FAILED: "审核失败",
            cls.NO_NEED_REVIEWED: "不需要审核"
        }
        return mapping.get(status, "未知状态")


class AnalysisStatus(StrEnum):
    """解析状态枚举"""
    WAITING = "waiting"
    CONVERT = "convert"
    OCR_RESOLVE = "ocr_resolve"
    FILE_CHUNK = "file_chunk"
    DATA_CLEAN = "data_clean"
    EMBEDDING = "embedding"
    FINISH = "finish"
    FAILED = "failed"

    @classmethod
    def get_desc(cls, status):
        mapping = {
            cls.WAITING: "等待解析中",
            cls.CONVERT: "文件转换中",
            cls.OCR_RESOLVE: "OCR解析中",
            cls.FILE_CHUNK: "文件切片中",
            cls.DATA_CLEAN: "数据清洗中",
            cls.EMBEDDING: "嵌入中",
            cls.FINISH: "完成",
            cls.FAILED: "失败"
        }
        return mapping.get(status, "未知状态")

class TaskType(StrEnum):
    """任务类型枚举"""
    AUDIT_TASK = "audit_task"
    REWARD_TASK = "reward_task"

    @staticmethod
    def get_desc(task_type):
        mapping = {
            TaskType.AUDIT_TASK: "审核任务",
            TaskType.REWARD_TASK: "悬赏任务"
        }
        return mapping.get(task_type, "未知任务类型")