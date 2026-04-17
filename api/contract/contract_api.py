from api.deps import get_file_service
from api.contract import contract_router
from fastapi import UploadFile, File, Depends, Request

from schemas.file import FileRecordResponse
from schemas.general import Result
from services.file.file_service import FileService


@contract_router.post("/preview", response_model=Result[str])
async def upload_file(
        request: Request,
        file: UploadFile = File(...),
        file_service: FileService = Depends(get_file_service),
):

    await file_service.file_upload_and_convert(file, request.state.user_id)

    return Result.success(message="上传成功", data=await file_service.upload_file(file, request.state.user_id))