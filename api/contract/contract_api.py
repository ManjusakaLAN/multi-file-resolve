from typing import List

from fastapi.params import Query

from api.deps import get_contract_service, get_contract_agent_service, get_model_service
from api.contract import contract_router
from fastapi import UploadFile, File, Depends, Request, Body

from core.enum.contract import ReviewStatus
from schemas.contract import ContractReviewTaskResponse, ContractPreReviewInfoResponse, ContractReviewTaskUpdate
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
