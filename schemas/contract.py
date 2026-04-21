from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Any

from core.enum.contract import ReviewRecommendation, ReviewStatus, StandPoint, ReviewCriteria


class ContractReviewTaskBase(BaseModel):
    file_name: Optional[str] = Field(None, max_length=256, description="文件名称")
    contract_name: Optional[str] = Field(None, max_length=256, description="合同名称")

    # 1. 类型改为 Optional
    # 2. 默认值设为 None 或 枚举值
    review_status: Optional[ReviewStatus | str] = Field("", description="审查状态")
    review_recommendation: Optional[ReviewRecommendation | str] = Field("", description="审查建议")
    stand_point: Optional[StandPoint | str] = Field("", description="立场选择")
    review_criteria: Optional[ReviewCriteria | str] = Field("", description="审查标准")

    high_risk: int = Field(0)
    medium_risk: int = Field(0)
    low_risk: int = Field(0)
    contract_type: Optional[str] = None
    part_a_name: Optional[str] = None
    part_b_name: Optional[str] = None
    is_contract: int = 0
    contract_overview: Optional[str] = None
    error_message: Optional[str] = None


# --- 创建请求 Schema ---
class ContractReviewTaskCreate(ContractReviewTaskBase):
    source_file_key: str = Field(..., description="源文件key")


# --- 更新请求 Schema ---
class ContractReviewTaskUpdate(BaseModel):
    # 全部设为 Optional，且包含空值拦截逻辑
    file_name: Optional[str] = None
    contract_name: Optional[str] = None
    review_status: Optional[ReviewStatus] = None
    high_risk: Optional[int] = None
    medium_risk: Optional[int] = None
    low_risk: Optional[int] = None
    review_recommendation: Optional[ReviewRecommendation] = None
    stand_point: Optional[StandPoint] = None
    review_criteria: Optional[ReviewCriteria] = None
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

    class Config:
        from_attributes = True
