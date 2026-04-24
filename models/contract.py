import uuid

from sqlalchemy import Column, String, Integer, DateTime, func, Text, JSON
from core.infrastructure.database import Base


class ContractReviewTask(Base):
    __tablename__ = "contract_review_task"
    __table_args__ = {'comment': '合同审查任务'}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键id")
    file_name = Column(String(256), comment="文件名称")
    contract_name = Column(String(256), comment="合同名称")
    review_status = Column(String(100), default="waiting_pre_review",
                           comment="审查状态:waiting_pre_review 等待预审查中 pre_review 预审查中 pre_review_failed 预审查失败 pre_review_finish 预审查完成 waiting_review 待审查 resolving 处理中 finish 完成 failed 失败")
    review_stage = Column(String(100), default="file_analysis",
                          comment="审查阶段:文档解析 file_analysis 要素提取 elements_extract 风险扫描 risk_scan 摘要生成 summarization_generate 修订建议 revised_suggestion")
    high_risk = Column(Integer, default=0, comment="高风险数量")
    medium_risk = Column(Integer, default=0, comment="中风险数量")
    low_risk = Column(Integer, default=0, comment="低风险数量")
    review_recommendation = Column(String(32), default="not_reviewed",
                                   comment="审查建议：compliance合规  not_reviewed未审查 suggest_modify建议修改")
    summary = Column(Text, comment="合同摘要")
    attention = Column(Text, comment="注意事项")
    stand_point = Column(String(64), default="", comment="立场选择 partA甲方 partB乙方 ")
    review_criteria = Column(String(64), default="", comment="审查标准：strong强势, neutral中立, weak弱势")
    outlines = Column(JSON, comment="合同大纲")
    elements = Column(JSON, comment="合同要素")
    contract_type = Column(String(64), comment="合同类型")
    part_a_name = Column(String(256), comment="甲方名称")
    part_b_name = Column(String(256), comment="乙方名称")
    md_file_key = Column(String(256), comment="md文件key")
    source_file_key = Column(String(256), comment="源文件key")
    md_file_path = Column(String(256), comment="md文件路径")
    is_contract = Column(Integer, default=2, comment="是否合同 0 否 1 是 2 未知")
    contract_overview = Column(String(1024), comment="合同概要")
    error_message = Column(String(1024), comment="错误信息")
    created_by = Column(String(36), comment="创建人")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")


class ContractSliceContent(Base):
    __tablename__ = "contract_slice_content"
    __table_args__ = {'comment': '合同切分内容'}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键id")
    contract_review_task_id = Column(String(36), comment="合同审查任务id")
    slice_id = Column(String(36), comment="切分id")
    slice_content = Column(Text, comment="切分内容")
    len = Column(Integer, comment="切分内容长度")
    created_by = Column(String(36), comment="创建人")
    is_risk_scanned = Column(Integer, default=0, comment="是否风险扫描 0 否 1 是")


class ContractRisk(Base):
    __tablename__ = "contract_risk"
    __table_args__ = {'comment': '合同风险'}
    #  包括 关联条款 原文摘录 风险说明 潜在影响 修改建议 所属切片id
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键id")
    contract_review_task_id = Column(String(36), comment="合同审查任务id")
    slice_id = Column(String(36), comment="切片id")
    risk_level = Column(String(36), comment="风险等级 低中高")
    # 关联条款
    associated_clause = Column(Text, comment="关联条款")
    # 原文摘录
    original_excerpt = Column(Text, comment="原文摘录")
    # 风险说明
    risk_description = Column(Text, comment="风险说明")
    # 潜在影响
    potential_impact = Column(Text, comment="潜在影响")
    # 修改建议
    modification_suggestion = Column(Text, comment="修改建议")
    created_time = Column(DateTime, default=func.now(), comment="创建时间")


class ContractRevisedSuggestion(Base):
    __tablename__ = "contract_revised_suggestion"
    __table_args__ = {'comment': '合同修订建议'}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键id")
    contract_review_task_id = Column(String(36), comment="合同审查任务id")
    # 审查违规名称
    review_violation_name = Column(String(36), comment="审查违规名称")
    # 原始条款
    original_clause = Column(Text, comment="原始条款")
    # 修订建议
    revised_suggestion = Column(Text, comment="修订建议")
    # 修订说明
    revised_description = Column(Text, comment="修订说明")
    # 谈判要点
    negotiation_point = Column(Text, comment="谈判要点")
