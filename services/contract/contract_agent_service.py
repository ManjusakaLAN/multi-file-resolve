import json
import logging
import uuid

from langchain.chat_models import init_chat_model
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.enum.contract import ReviewStatus, ReviewStage
from models.contract import ContractSliceContent, ContractReviewTask, ContractRisk
from schemas.agent_tool import ChunkLookupSchema, ContractOutline, RiskScanState
from schemas.contract import ContractPreReviewInfoResponse, ContractReviewTaskUpdate
from schemas.llm import ModelInvokeInfo
from langchain.messages import HumanMessage, SystemMessage

from services.contract.agent_workflow.oe_agent_workflow import parallel_workflow, State
from services.contract.agent_workflow.risk_scan_agent_workflow import risk_scan_workflow

logger = logging.getLogger(__name__)


class ContractAgentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_contract_slice_contents(self, contract_review_task_id: str):
        """
        获取合同切片内容
        :param contract_review_task_id:
        :return:
        """
        stmt_contract_slice = select(ContractSliceContent).where(
            ContractSliceContent.contract_review_task_id == contract_review_task_id).order_by(
            ContractSliceContent.slice_id)
        contract_slice_contents = (await self.db.execute(stmt_contract_slice)).scalars().all()

        if not contract_slice_contents:
            raise Exception("contract_id not found")
        return contract_slice_contents

    async def contract_judge_agent(self, model_invoke_info: ModelInvokeInfo,
                                   contract_review_task_id: str) -> ContractPreReviewInfoResponse:
        """
        合同预审查 Agent
        :param model_invoke_info:
        :param contract_review_task_id:
        :return:
        """
        # 拿到合同切片内容
        contract_slice_contents = await self.get_contract_slice_contents(contract_review_task_id)
        # 取出第一条和最后一条数据
        first_slice = contract_slice_contents[0]
        last_slice = contract_slice_contents[-1]

        model = init_chat_model(
            model=model_invoke_info.model_id,
            base_url=model_invoke_info.base_url,
            api_key=model_invoke_info.api_key,
            temperature=0.7,
            timeout=30,
            max_tokens=8192,
            max_retries=6,  # Default; increase for unreliable networks
        )

        res_schema = {
            "is_contract": "是否是一个合同文件，请返回 'True' 或 'False'",
            "contract_name": "合同名称",
            "part_a": "甲方名称",
            "part_b": "乙方名称",
        }

        model.with_structured_output(ContractPreReviewInfoResponse)
        prompt_msg = f"""
            你是一个合同审查专家，现在我将给你一个文件的首位部分内容，你需要帮我完成两件事情：
            1. 通过这些内容告知我，这是否是一个合同文件，只要几率足够大就请认可这个文件是合同文件
            2. 通过这些内容，从文件中提取核心要素，包括合同名称，甲乙方名称，如果没有这些内容请填充空字符串即可
            返回的格式参照 {res_schema}
            返回的内容必须要严格按照这个json格式进行返回，请勿返回其他内容
            输出限制：
            1. 直接输出 JSON 字符串本身。
            2. 禁止使用 ```json 等 Markdown 格式。
            3. 不要输出任何多余的文字。
        """

        conversation = [
            SystemMessage(prompt_msg),
            HumanMessage(f"合同文件的开头部分内容：{first_slice.slice_content}，"
                         f"合同文件的结尾部分内容：{last_slice.slice_content}"),
        ]

        response = await model.ainvoke(conversation)
        preview_info = json.loads(response.content)

        contract_name = preview_info.get("contract_name")
        part_a = preview_info.get("part_a")
        part_b = preview_info.get("part_b")
        is_contract = preview_info.get("is_contract")

        contract_review_task_stmt = select(ContractReviewTask).where(
            ContractReviewTask.id == contract_review_task_id
        )
        contract_review_task = (await self.db.execute(contract_review_task_stmt)).scalars().first()
        if not contract_review_task:
            raise Exception("找不到合同审查任务")

        contract_review_task.contract_name = contract_name
        contract_review_task.part_a_name = part_a
        contract_review_task.part_b_name = part_b
        if is_contract:
            contract_review_task.is_contract = 1
        else:
            contract_review_task.is_contract = 0
        # 更新状态为预审查完成
        contract_review_task.review_status = ReviewStatus.PRE_REVIEW_FINISH
        contract_review_task.review_stage = ReviewStage.ELEMENTS_EXTRACT
        await self.db.commit()
        return json.loads(response.content)

    def get_slice_tool(self, task_id: str):
        """创建一个动态工具，闭包捕获当前的 db 和 task_id"""

        async def lookup_slice_content(slice_id: int) -> str:
            """当大纲显示某章节在特定切片中时，调用此工具获取原文内容。"""
            stmt = select(ContractSliceContent).where(
                ContractSliceContent.contract_review_task_id == task_id,
                ContractSliceContent.slice_id == slice_id
            )
            result = await self.db.execute(stmt)
            obj = result.scalars().first()
            return obj.slice_content if obj else "未找到该切片内容"

        return StructuredTool.from_function(
            coroutine=lookup_slice_content,
            name="lookup_contract_slice",
            description="根据切片 ID 获取合同原文内容,目前可选id为 0-5",
            args_schema=ChunkLookupSchema
        )

    async def contract_core_content_compression_and_element_pick_up(self, model_invoke_info: ModelInvokeInfo,
                                                                    contract_review_task_id: str) -> State:
        """
        合同要素提取和大纲生成
        :param model_invoke_info:
        :param contract_review_task_id:
        :return:
        """

        llm = ChatOpenAI(
            model=model_invoke_info.model_id,
            base_url=model_invoke_info.base_url,
            api_key=SecretStr(model_invoke_info.api_key)
        )

        tools = [self.get_slice_tool(contract_review_task_id)]

        config = {
            "configurable": {
                "thread_id": uuid.uuid4(),
                "llm": llm,  # 注入模型实例
                "tools": tools  # 注入工具实例
            }
        }

        stmt = (
            select(func.count())
            .select_from(ContractSliceContent)
            .where(ContractSliceContent.contract_review_task_id == contract_review_task_id)
        )

        # 执行并获取结果
        result = await self.db.execute(stmt)
        count = result.scalar()  # 获取查询到的整数数量
        slice_ids = list(range(count))
        state = State(slice_ids=slice_ids, summary="")
        state = await parallel_workflow.ainvoke(state, config=config)

        stmt = select(ContractReviewTask).where(
            ContractReviewTask.id == contract_review_task_id
        )
        contract_review_task = (await self.db.execute(stmt)).scalars().first()

        # 转为对象
        state = State(**state)
        # 记录大纲
        outlines = []
        sorted_outlines = sorted(state.contract_outlines, key=lambda x: x.slice_id)
        for outline in sorted_outlines:
            outline_info = ContractOutline(slice_id=outline.slice_id, outline=outline.outline)
            outlines.append(outline_info)
        outlines_json_str = json.dumps([o.model_dump() for o in outlines], ensure_ascii=False)
        contract_review_task.outlines = outlines_json_str
        elements_dict = state.elements.model_dump()
        # 记录核心要素
        contract_review_task.elements = json.dumps(elements_dict)
        # 记录合同摘要
        contract_review_task.summary = state.summary

        contract_review_task.review_stage = ReviewStage.RISK_SCAN
        await self.db.commit()
        print(state)
        return state

    async def contract_risk_scan(self, model_invoke_info: ModelInvokeInfo, contract_review_task_id: str, outlines: str) -> RiskScanState:
        """
        合同风险扫描
        :param outlines:
        :param model_invoke_info:
        :param contract_review_task_id:
        :return:
        """
        llm = ChatOpenAI(
            model=model_invoke_info.model_id,
            base_url=model_invoke_info.base_url,
            api_key=SecretStr(model_invoke_info.api_key)
        )

        tools = [self.get_slice_tool(contract_review_task_id)]

        config = {
            "configurable": {
                "thread_id": uuid.uuid4(),
                "llm": llm,  # 注入模型实例
                "tools": tools  # 注入工具实例
            }
        }

        stmt = (
            select(func.count())
            .select_from(ContractSliceContent)
            .where(ContractSliceContent.contract_review_task_id == contract_review_task_id)
        )

        # 执行并获取结果
        result = await self.db.execute(stmt)
        count = result.scalar()  # 获取查询到的整数数量
        slice_ids = list(range(count))
        risk_state = RiskScanState(slice_ids=slice_ids, outlines=outlines, scan_risks=[], logs=[])
        risk_state = await risk_scan_workflow.ainvoke(risk_state, config=config)

        risk_state = RiskScanState(**risk_state)
        logger.info(f"风险扫描结果:{risk_state}")
        scan_risks = risk_state.scan_risks
        contract_risks = []
        for scan_risk in scan_risks:
            contract_risk = ContractRisk(
                contract_review_task_id=contract_review_task_id,
                slice_id=scan_risk.slice_id,
                risk_level=scan_risk.risk_level,
                associated_clause=scan_risk.associated_clause,
                original_excerpt=scan_risk.original_excerpt,
                risk_description=scan_risk.risk_description,
                potential_impact=scan_risk.potential_impact,
                modification_suggestion=scan_risk.modification_suggestion
            )
            contract_risks.append(contract_risk)
        self.db.add_all(contract_risks)
        logger.info(f"风险点扫描记录完成: {contract_risks}")
        await self.db.commit()

        return risk_state