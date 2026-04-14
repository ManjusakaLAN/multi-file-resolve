from api.deps import get_file_service
from api.file import file_router
from fastapi import UploadFile, File, Depends, Request

from schemas.file import FileRecordResponse
from schemas.general import Result
from services.file.file_service import FileService


@file_router.post("/upload", response_model=Result[FileRecordResponse])
async def upload_file(
        request: Request,
        file: UploadFile = File(...),
        file_service: FileService = Depends(get_file_service),
):
    return Result.success(message="上传成功", data=await file_service.upload_file(file, request.state.user_id))

@file_router.get("/download")
async def download_file(
        file_key: str,
        file_service: FileService = Depends(get_file_service),
):
    """
    通过 file_key 下载文件
    """
    return await file_service.download_file(file_key)