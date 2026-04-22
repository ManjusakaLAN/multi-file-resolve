from enum import StrEnum

class ReviewStatus(StrEnum):
    WAITING_PRE_REVIEW = "waiting_pre_review"
    PRE_REVIEW = "pre_review"
    PRE_REVIEW_FAILED = "pre_review_failed"
    PRE_REVIEW_FINISH = "pre_review_finish"
    WAITING_REVIEW = "waiting_review"
    RESOLVING = "resolving"
    FINISH = "finish"
    FAILED = "failed"

    @classmethod
    def get_desc(cls, status):
        mapping = {
            cls.WAITING_PRE_REVIEW: "等待预审查",
            cls.PRE_REVIEW: "预审查中",
            cls.PRE_REVIEW_FAILED: "预审查失败",
            cls.PRE_REVIEW_FINISH: "预审查完成",
            cls.WAITING_REVIEW: "待审查",
            cls.RESOLVING: "处理中",
            cls.FINISH: "完成",
            cls.FAILED: "失败"
        }
        return mapping.get(status, "未知状态")

class ReviewRecommendation(StrEnum):
    COMPLIANCE = "compliance"
    NOT_REVIEWED = "not_reviewed"
    SUGGEST_MODIFY = "suggest_modify"

    @classmethod
    def get_desc(cls, recommendation):
        mapping = {
            cls.COMPLIANCE: "合规",
            cls.NOT_REVIEWED: "未审查",
            cls.SUGGEST_MODIFY: "建议修改"
        }
        return mapping.get(recommendation, "未知建议")

class ReviewCriteria(StrEnum):
    STRONG = "strong"
    NEUTRAL = "neutral"
    WEAK = "weak"

    @classmethod
    def get_desc(cls, criteria):
        mapping = {
            cls.STRONG: "强势",
            cls.NEUTRAL: "中立",
            cls.WEAK: "弱势"
        }
        return mapping.get(criteria, "未知标准")

class StandPoint(StrEnum):
    PART_A = "partA"
    PART_B = "partB"

    @classmethod
    def get_desc(cls, point):
        mapping = {
            cls.PART_A: "甲方",
            cls.PART_B: "乙方"
        }
        return mapping.get(point, "未知立场")