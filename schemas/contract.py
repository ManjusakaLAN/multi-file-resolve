from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

from core.enum.contract import ReviewRecommendation, ReviewStatus, StandPoint, ReviewCriteria, RiskLevel, ReviewStage
from schemas.agent_tool import Elements, ContractOutline


class ContractReviewTaskBase(BaseModel):
    file_name: Optional[str] = Field(None, max_length=256, description="文件名称")
    contract_name: Optional[str] = Field(None, max_length=256, description="合同名称")

    # 1. 类型改为 Optional
    # 2. 默认值设为 None 或 枚举值
    review_status: Optional[ReviewStatus | str] = Field("", description="审查状态")
    review_stage: Optional[ReviewStage | str] = Field("", description="审查阶段")
    review_recommendation: Optional[ReviewRecommendation | str] = Field("", description="审查建议")
    stand_point: Optional[StandPoint | str] = Field("", description="立场选择")
    review_criteria: Optional[ReviewCriteria | str] = Field("", description="审查标准")
    summary: Optional[str] = Field("", description="合同摘要")
    attention: Optional[str] = Field("", description="注意事项")
    high_risk: int = Field(0)
    medium_risk: int = Field(0)
    low_risk: int = Field(0)
    contract_type: Optional[str] = None
    part_a_name: Optional[str] = None
    part_b_name: Optional[str] = None
    is_contract: int = 0
    contract_overview: Optional[str] = None
    error_message: Optional[str] = None
    outlines: Optional[str | List[ContractOutline]] = None
    elements: Optional[str | Elements] = None


# --- 创建请求 Schema ---
class ContractReviewTaskCreate(ContractReviewTaskBase):
    source_file_key: str = Field(..., description="源文件key")


# --- 更新请求 Schema ---
class ContractReviewTaskUpdate(BaseModel):
    # 全部设为 Optional，且包含空值拦截逻辑
    id: str = Field(..., description="主键ID")
    file_name: Optional[str] = None
    contract_name: Optional[str] = None
    review_status: Optional[ReviewStatus | str] = None
    high_risk: Optional[int] = None
    medium_risk: Optional[int] = None
    low_risk: Optional[int] = None
    review_recommendation: Optional[ReviewRecommendation | str] = None
    stand_point: Optional[StandPoint | str] = None
    review_criteria: Optional[ReviewCriteria | str] = None
    contract_type: Optional[str] = None
    part_a_name: Optional[str] = None
    part_b_name: Optional[str] = None
    md_file_key: Optional[str] = None
    md_file_path: Optional[str] = None
    is_contract: Optional[int] = None
    contract_overview: Optional[str] = None
    error_message: Optional[str] = None


# --- 返回响应 Schema ---
class ContractReviewTaskResponse(ContractReviewTaskBase):
    id: str
    md_file_key: Optional[str] = None
    source_file_key: Optional[str] = None
    md_file_path: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime

    @property
    def review_status_desc(self) -> str:
        # 增加 None 值判断
        if not self.review_status:
            return "未知状态"
        return ReviewStatus.get_desc(self.review_status)


# 合同 预审查 schema
class ContractPreReviewInfoResponse(BaseModel):
    """
    合同预审查结果
    """
    is_contract: bool = Field(..., description="是否是一个合同文件")
    contract_name: Optional[str] = Field(None, description="合同名称")
    part_a: Optional[str] = Field(None, description="甲方名称")
    part_b: Optional[str] = Field(None, description="乙方名称")


# 1. 共享属性基类
class RiskBase(BaseModel):
    risk_level: Optional[RiskLevel | str] = Field(..., description="风险等级：high高、medium中、low低")
    associated_clause: str = Field(..., description="关联条款名称/章节号")
    original_excerpt: str = Field(..., description="合同原文摘录")
    risk_description: str = Field(..., description="风险详细说明")
    potential_impact: str = Field(..., description="潜在法律或经济影响")
    modification_suggestion: Optional[str] = Field("", description="针对性的修改建议")
    slice_id: Optional[str] = Field(None, description="所属切片ID")


# 2. 供 LangGraph 结构化提取使用的 Schema
# 注意：提取时不需要 ID 和 TaskID，由后端逻辑自动补充
class RiskCreate(RiskBase):
    """
    创建风险项时的入参。
    LLM 提取出这些字段后，后端会关联 contract_review_task_id 并存入数据库。
    """
    pass


# 4. 更新风险信息时使用的 Schema (PATCH)
class RiskUpdate(BaseModel):
    """
    手动修正风险项时的入参。
    """
    risk_level: Optional[RiskLevel | str] = Field(None, description="风险等级")
    associated_clause: Optional[str] = Field(None, description="关联条款")
    risk_description: Optional[str] = Field(None, description="风险说明")
    modification_suggestion: Optional[str] = Field(None, description="修改建议")


# 5. 接口返回详细信息时使用的 Schema (Response)
class RiskResponse(RiskBase):
    """
    返回给前端的完整风险详情。
    """
    id: str = Field(..., description="风险记录唯一ID")
    contract_review_task_id: str = Field(..., description="关联的审查任务ID")
    created_time: datetime = Field(..., description="识别时间")


# --- 1. 基础模型 (定义通用业务字段) ---
class ContractRevisedSuggestionBase(BaseModel):
    contract_review_task_id: Optional[str] = Field(None, description="合同审查任务id")
    review_violation_name: Optional[str] = Field(None, description="审查违规名称")
    original_clause: Optional[str] = Field(None, description="原始条款")
    revised_suggestion: Optional[str] = Field(None, description="修订建议")
    revised_description: Optional[str] = Field(None, description="修订说明")
    negotiation_point: Optional[str] = Field(None, description="谈判要点")


# --- 2. 响应模型 (用于接口返回数据) ---
class ContractRevisedSuggestionResponse(ContractRevisedSuggestionBase):
    id: str = Field(..., description="主键ID")


# --- 3. 列表查询模型 (用于分页查询过滤) ---
class ContractRevisedSuggestionQuery(BaseModel):
    contract_review_task_id: Optional[str] = Field(None, description="按审查任务ID精确过滤")
    review_violation_name: Optional[str] = Field(None, description="按违规名称模糊搜索")
    # 通常分页查询还需要包含如下字段
    # page: int = Field(1, ge=1, description="页码")
    # size: int = Field(10, ge=1, le=100, description="每页数量")


# --- 4. 创建/更新模型 (用于接口请求参数) ---
class ContractRevisedSuggestionCreate(ContractRevisedSuggestionBase):
    # 必填项可以在这里重写，例如任务ID在创建时通常是必须的
    contract_review_task_id: str = Field(..., description="合同审查任务id")


class ContractRevisedSuggestionUpdate(BaseModel):
    # 更新模型所有字段均为可选，防止覆盖未传的字段
    review_violation_name: Optional[str] = None
    original_clause: Optional[str] = None
    revised_suggestion: Optional[str] = None
    revised_description: Optional[str] = None
    negotiation_point: Optional[str] = None
