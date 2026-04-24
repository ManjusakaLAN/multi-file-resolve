import operator
from typing import Optional, List, Annotated

from pydantic import BaseModel, Field

from core.enum.contract import RiskLevel


class ChunkLookupSchema(BaseModel):
    slice_id: int = Field(..., description="合同切片的序号索引")


class Elements(BaseModel):
    """
    合同核心要素提取模型。
    用于从合同文本中结构化地提取关键业务信息。
    """

    # --- 基本信息 ---
    contract_id: str = Field("", description="合同编号")
    contract_name: str = Field("", description="合同名称")
    contract_type: str = Field("", description="合同类型（如：采购、销售、租赁、服务外包）")
    contract_status: str = Field("", description="合同状态（如：履行中、已结项、已终止）")

    # --- 主体信息 ---
    party_a: str = Field("", description="甲方名称（发包方/购买方）")
    party_a_legal_rep: str = Field("", description="甲方法定代表人")
    party_b: str = Field("", description="乙方名称（承包方/供应商）")
    party_b_legal_rep: str = Field("", description="乙方法定代表人")
    party_c: Optional[str] = Field("", description="丙方/第三方名称（如有）")

    # --- 金额与支付 ---
    contract_amount: str = Field("", description="合同总金额（含税）")
    contract_amount_net: str = Field("", description="合同不含税金额")
    tax_rate: str = Field("", description="适用税率")
    currency: str = Field("CNY", description="币种（如：CNY, USD）")
    payment_method: str = Field("", description="支付方式（如：银行转账、电汇、承兑汇票）")

    # --- 履行期限 ---
    contract_period_start: str = Field("", description="合同履行开始日期")
    contract_period_end: str = Field("", description="合同履行结束日期")
    contract_duration: str = Field("", description="合同有效期限（天/月/年）")

    # --- 签署信息 ---
    contract_sign_date: str = Field("", description="合同签署日期")
    contract_sign_place: str = Field("", description="合同签署地点")
    contract_sign_person_a: str = Field("", description="甲方签署人")
    contract_sign_person_b: str = Field("", description="乙方签署人")

    # --- 法律与合规 ---
    effective_conditions: str = Field("", description="合同生效条件")
    governing_law: str = Field("中国法律", description="适用法律/管辖权")
    dispute_resolution: str = Field("", description="争议解决方式（如：仲裁、诉讼）")

    # --- 其他特殊条款 ---
    guarantee_period: str = Field("", description="质保期/保修期")
    performance_bond: str = Field("", description="履约保证金金额")
    intellectual_property: str = Field("", description="知识产权归属说明")
    confidentiality_term: str = Field("", description="保密期限")


class ContractOutline(BaseModel):
    slice_id: int = Field(0, description="合同分片编号")
    outline: str = Field("", description="大纲内容")


# --- 要素提取 和 大纲生成的 State 定义 ---
class State(BaseModel):
    slice_ids: List[int] = Field([], description="待处理的合同分片编号列表")
    # 使用 Annotated 和 operator.add 确保并行节点的结果能合并到一个列表中
    contract_outlines: Annotated[List[ContractOutline], operator.add] = []
    summary: str = Field("", description="合同摘要")
    elements: Elements = Field(default_factory=lambda: Elements(), description="合同要素提取结果")
    logs: Annotated[list[str], operator.add] = []


# 1. 共享属性基类
class RiskScanInfo(BaseModel):
    risk_level: Optional[RiskLevel | str] = Field(..., description="风险等级：high高、medium中、low低")
    associated_clause: str = Field(..., description="关联条款名称/章节号")
    original_excerpt: str = Field(..., description="合同原文摘录")
    risk_description: str = Field(..., description="风险详细说明")
    potential_impact: str = Field(..., description="潜在法律或经济影响")
    modification_suggestion: str = Field(..., description="针对性的修改建议")
    slice_id: Optional[str] = Field(None, description="所属切片ID")


class RiskScanState(BaseModel):
    slice_ids: List[int] = Field([], description="待处理的合同分片编号列表")
    outlines: str = Field("", description="合同大纲信息")
    scan_risks: Annotated[List[RiskScanInfo], operator.add] = Field([], description="风险扫描结果")
    attention: str = Field("", description="注意事项")
    logs: Annotated[list[str], operator.add] = []

# ✅ 必须定义这个包装类
class RiskScanResult(BaseModel):
    """用于接收 {"risks": [...]} 结构的类"""
    risks: List[RiskScanInfo] = Field(default_factory=list, description="发现的风险点列表")