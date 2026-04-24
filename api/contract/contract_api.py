from typing import List

from fastapi.params import Query
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from starlette.responses import StreamingResponse

from api.deps import get_contract_service, get_contract_agent_service, get_model_service
from api.contract import contract_router
from fastapi import UploadFile, File, Depends, Request, Body

from core.enum.contract import ReviewStatus, RiskLevel
from schemas.contract import ContractReviewTaskResponse, ContractPreReviewInfoResponse, ContractReviewTaskUpdate, \
    RiskResponse, ContractRevisedSuggestionResponse
from schemas.general import Result, PageResponse
from services.contract.contract_service import ContractService
from services.contract.contract_agent_service import ContractAgentService
from services.llm.model_service import LLMModelService


@contract_router.post("/upload", response_model=Result[ContractReviewTaskResponse],
                      description="合同上传并生成审核任务")
async def upload_file(
        request: Request,
        file: UploadFile = File(...),
        contract_service: ContractService = Depends(get_contract_service),
):
    """
    合同上传并生成审核任务
    :param request:
    :param file:
    :param contract_service:
    :return:
    """
    return Result.success(message="上传成功",
                          data=await contract_service.generate_contract_review_task(file, request.state.user_id))


@contract_router.get("/review_task/page_list", response_model=PageResponse[ContractReviewTaskResponse],
                     description="合同审查任务列表")
async def get_review_task_page_list(
        file_name: str = "",
        contract_name: str = "",
        review_status: ReviewStatus | str = "",
        page: int = 1,
        page_size: int = 10,
        contract_service: ContractService = Depends(get_contract_service),
):
    """
    获取合同审查任务列表
    :param file_name:
    :param contract_name:
    :param review_status:
    :param page:
    :param page_size:
    :param contract_service:
    :return:
    """
    return await contract_service.get_review_task_page_list(file_name, contract_name, review_status, page, page_size)


@contract_router.get("/review_task/detail", response_model=Result[ContractReviewTaskResponse],
                     description="合同审查任务详情")
async def get_review_task_detail(
        contract_review_task_id: str = Query(..., description="合同ID"),
        contract_service: ContractService = Depends(get_contract_service),
):
    """
    获取合同审查任务详情
    :param contract_review_task_id:
    :param contract_service:
    :return:
    """
    return Result.success(message="获取合同审查任务详情成功",
                          data=await contract_service.get_review_task_detail(contract_review_task_id))


@contract_router.post("/retry", response_model=Result[ContractPreReviewInfoResponse], description="重试合同审查任务")
async def retry_contract(
        contract_review_task_id: str = Body(..., embed=True),
        contract_service: ContractService = Depends(get_contract_service),
):
    """
    重试任务
    :param contract_review_task_id:
    :param contract_service:
    :return:
    """
    return Result.success(message="任务进入重试队列，请稍等",
                          data=await contract_service.retry(contract_review_task_id))


@contract_router.delete("/delete", response_model=Result[ContractPreReviewInfoResponse], description="合同审查任务删除")
async def delete_contract(
        contract_review_task_id: str = Body(..., embed=True),
        contract_service: ContractService = Depends(get_contract_service),
):
    """
    合同删除
    :param contract_review_task_id:
    :param contract_service:
    :return:
    """
    return Result.success(message="删除成功",
                          data=await contract_service.delete_contract(contract_review_task_id))


@contract_router.post("/review", response_model=Result[ContractReviewTaskResponse])
async def review_contract(
        contract_review_task: ContractReviewTaskUpdate,
        contract_service: ContractService = Depends(get_contract_service),
):
    """
    合同审核
    :param contract_review_task:
    :param contract_service:
    :return:
    """
    return Result.success(message="合同已进入审查队列，请耐心等待...",
                          data=await contract_service.do_contract_review(contract_review_task))


@contract_router.get("/result", response_model=Result[ContractReviewTaskResponse])
async def review_contract(
        contract_review_task_id: str,
        model_service: LLMModelService = Depends(get_model_service),

):
    """
    合同审核
    :param contract_review_task_id:
    :param model_service:
    :return:
    """
    return Result.success(message="审核成功",
                          data=await model_service.get_review_result(contract_review_task_id))


@contract_router.get("/risks", response_model=Result[List[RiskResponse]])
async def get_scan_risks(
        contract_review_task_id: str,
        risk_level: RiskLevel | str = "",
        contract_service: ContractService = Depends(get_contract_service),
):
    """
    获取风险点
    :param risk_level:
    :param contract_review_task_id:
    :param contract_service:
    :return:
    """
    return Result.success(message="获取风险点成功",
                          data=await contract_service.get_scan_risks(contract_review_task_id, risk_level))


@contract_router.get("/revised_suggestion", response_model=Result[List[ContractRevisedSuggestionResponse]])
async def get_revised_suggestion(
        contract_review_task_id: str,
        contract_service: ContractService = Depends(get_contract_service),
):
    """
    获取修正建议
    :param contract_review_task_id:
    :param contract_service:
    :return:
    """
    return Result.success(message="获取修正建议成功",
                          data=[
                              {
                                  "id": "7f2a8934-2e5a-4b92-8f1d-c89e3a123456",
                                  "contract_review_task_id": "TASK-20260424-001",
                                  "review_violation_name": "单方解除权不对等风险",
                                  "original_clause": "只有买方有权随时终止本合同的部分或全部，但应以书面通知卖方，说明终止的内容和有效日期...",
                                  "revised_suggestion": "建议修改为：任何一方欲解除合同，需提前30日书面通知对方，且仅在对方严重违约或发生不可抗力导致合同无法履行时方可行使。",
                                  "revised_description": "原条款赋予买方无条件单方终止权，且未规定卖方的对等权利，显失公平。",
                                  "negotiation_point": "坚持要求增加卖方的解除权或明确买方行使该权利时的经济赔偿标准（含预期利润）。"
                              },
                              {
                                  "id": "a1b2c3d4-e5f6-4a5b-bc6d-e7f8g9h0i1j2",
                                  "contract_review_task_id": "TASK-20260424-001",
                                  "review_violation_name": "支付条件与验收期限风险",
                                  "original_clause": "买方在收到卖方提交的下列单据并经审核无误60日内，向卖方支付合同该批次价格 100 %的结清款。买方最长可延迟检验达6个月。",
                                  "revised_suggestion": "建议修改为：买方应在到货后15日内完成验收。验收合格后30日内支付90%货款，余款10%转为质保金。",
                                  "revised_description": "验收期限过长（6个月）导致卖方回款存在重大不确定性，资金成本高。",
                                  "negotiation_point": "强调行业惯例验收期不超过30天，若买方逾期不验收应视为验收合格。"
                              },
                              {
                                  "id": "3d5f7g9h-1a2b-3c4d-5e6f-7g8h9i0j1k2l",
                                  "contract_review_task_id": "TASK-20260424-001",
                                  "review_violation_name": "赔偿范围不明确风险",
                                  "original_clause": "卖方应向买方支付本合同不合格货物总价款 3%的违约金，并赔偿买方由此产生的全部损失。",
                                  "revised_suggestion": "建议修改为：赔偿范围仅限于买方遭受的直接经济损失，且总赔偿额（含违约金）不超过合同总价的100%。",
                                  "revised_description": "“全部损失”表述模糊，可能包含不可预见的间接损失，卖方风险敞口过大。",
                                  "negotiation_point": "明确排除间接损失（如利润损失、停工损失），并将赔偿总额封顶。"
                              },
                              {
                                  "id": "9a8b7c6d-5e4f-3g2h-1i0j-k9l8m7n6o5p4",
                                  "contract_review_task_id": "TASK-20260424-001",
                                  "review_violation_name": "不可抗力定义缺失风险",
                                  "original_clause": "不可抗力：是指任何一方当事人不能预见、不能避免并不能克服的自然灾害和社会性突发事件...",
                                  "revised_suggestion": "建议在不可抗力定义中明确包含：政府行为、法律法规变更、流行病、网络攻击及电力中断等情形。",
                                  "revised_description": "原定义范围窄，现代商业风险未被完全覆盖，可能导致卖方在特定情况下无法免责。",
                                  "negotiation_point": "要求增加“政府政策调整”和“交通管制”作为免责事宜。"
                              },
                              {
                                  "id": "e1f2g3h4-i5j6-k7l8-m9n0-p1q2r3s4t5u6",
                                  "contract_review_task_id": "TASK-20260424-001",
                                  "review_violation_name": "管辖权地不利风险",
                                  "original_clause": "友好协商解决不成的，向买方所在地人民法院提起诉讼。",
                                  "revised_suggestion": "建议修改为：向被告所在地人民法院提起诉讼；或提交中国国际经济贸易仲裁委员会进行仲裁。",
                                  "revised_description": "买方所在地管辖显著增加卖方的维权差旅及时间成本。",
                                  "negotiation_point": "争取“被告所在地”原则，体现法律公平，减少异地诉讼负担。"
                              }
                          ]
                          )


@contract_router.post("/chat")
async def chat(
        system_prompt: str = Body(..., embed=True),
        user_message: str = Body(..., embed=True),  # 使用 embed=True 以便接收 {"user_message": "..."} 格式
        model_service: LLMModelService = Depends(get_model_service),
):
    model_invoke_info = await model_service.get_model_invoke_info()

    llm = ChatOpenAI(
        model=model_invoke_info.model_id,
        base_url=model_invoke_info.base_url,
        api_key=SecretStr(model_invoke_info.api_key),
        streaming=True  # 显式开启流式模式
    )

    message = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ]

    async def generate():
        async for chunk in llm.astream(message):
            content = chunk.content
            if content:
                # 规范化 SSE 格式：data: 内容\n\n
                # 如果你想传纯文本且前端能识别，至少确保有刷新感
                yield f"data: {content}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
