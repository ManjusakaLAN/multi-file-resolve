from api.deps import get_contract_service
from api.contract import contract_router
from fastapi import UploadFile, File, Depends, Request

from schemas.contract import ContractReviewTaskResponse
from schemas.general import Result
from services.contract.contract_service import ContractService


@contract_router.post("/upload", response_model=Result[ContractReviewTaskResponse])
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
