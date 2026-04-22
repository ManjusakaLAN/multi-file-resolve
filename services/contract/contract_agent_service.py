import json
import logging
from langchain.chat_models import init_chat_model
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.enum.contract import ReviewStatus
from models.contract import ContractSliceContent, ContractReviewTask
from schemas.contract import ContractPreReviewInfoResponse
from schemas.llm import ModelInvokeInfo
from langchain.messages import HumanMessage, SystemMessage

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
        await self.db.commit()
        return json.loads(response.content)

    async def contract_core_content_compression_and_element_pick_up(self, model_invoke_info: ModelInvokeInfo,
                                                                    contract_review_task_id: str):
        """
        合同审查任务
        :param model_invoke_info:
        :param contract_review_task_id:
        :return:
        """
        # 拿到合同切片内容  contract_slice_content.slice_content 可以拿到合同内容
        contract_slice_contents = await self.get_contract_slice_contents(contract_review_task_id)

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
            "compress_content": "核心内容提取返回存放在此位置",
            "core_elements": {
                "contract_id": "合同编号",
                "contract_name": "合同名称",
                "contract_type": "合同类型（如：采购、销售、租赁、服务外包）",
                "contract_status": "合同状态（如：履行中、已结项、已终止）",

                "party_a": "甲方名称（发包方/购买方）",
                "party_a_legal_rep": "甲方法定代表人",
                "party_b": "乙方名称（承包方/供应商）",
                "party_b_legal_rep": "乙方法定代表人",
                "party_c": "丙方/第三方名称（如有）",

                "contract_amount": "合同总金额（含税）",
                "contract_amount_net": "合同不含税金额",
                "tax_rate": "适用税率",
                "currency": "币种（如：CNY, USD）",
                "payment_method": "支付方式（如：银行转账、电汇、承兑汇票）",

                "contract_period_start": "合同履行开始日期",
                "contract_period_end": "合同履行结束日期",
                "contract_duration": "合同有效期限（天/月/年）",

                "contract_sign_date": "合同签署日期",
                "contract_sign_place": "合同签署地点",
                "contract_sign_person_a": "甲方签署人",
                "contract_sign_person_b": "乙方签署人",

                "effective_conditions": "合同生效条件",
                "governing_law": "适用法律/管辖权",
                "dispute_resolution": "争议解决方式（如：仲裁、诉讼）",

                "guarantee_period": "质保期/保修期",
                "performance_bond": "履约保证金金额",
                "intellectual_property": "知识产权归属说明",
                "confidentiality_term": "保密期限"
            }
        }

        prompt_msg = f"""
        你是一个合同审查专家，现在我将依次按顺序给你一个合同文件的全部切片内容，你需要对每个切片完成两项工作:
        其一：对切片内容进行总结提炼,并且在之后的切片，我会将之前你对前面切片的总结一并传递给你，你需要基于前面的总结来对当前切片的内容进行总结，总结时不要求绝对简练，关键是要尽可能不要丢失关键信息
        其二，提取切片中的要素信息
        你必须关注的要素信息是：合同的名称，甲方和乙方，其余要素按照要求提取即可，提取不到的返回空字符串即可，在不断分析切片的过程中逐渐完善要素相关提取即可
        返回的格式参照 {res_schema}
        返回的内容必须要严格按照这个json格式进行返回，请勿返回其他内容
        """

        conversation = [
            SystemMessage(prompt_msg)
        ]

        for contract_slice_content in contract_slice_contents:
            conversation.append(HumanMessage(contract_slice_content.slice_content))
            response = model.invoke(conversation)
            print(response)
            print(json.dumps(response.content))
            break
