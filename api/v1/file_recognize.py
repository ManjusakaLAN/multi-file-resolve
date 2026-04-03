import logging

from fastapi import APIRouter, Depends, UploadFile
from fastapi.params import Query, Form, File

from api.deps import get_file_service
from schemas.file_recognize_task import FileRecognizeTask
from schemas.general import PageResponse, Result
from services.file_service import FileService

router = APIRouter()


@router.get("/", response_model=PageResponse[FileRecognizeTask])
async def get_file_recognize_task(
        file_name: str = Query(None),
        page: int = Query(1, ge=1),
        size: int = Query(10, ge=1, le=100),
        service: FileService = Depends(get_file_service)
):
    # 获取数据和总数
    items, total = await service.get_tasks_paged(
        file_name=file_name,
        page=page,
        page_size=size
    )
    return PageResponse(
        total=total,
        data=items,
        page=page,
        size=size
    )


@router.put("/task/create", response_model=Result)
async def create_file_recognize_task(
        task_name: str = Form(..., description="任务名称", max_length=50),
        file: UploadFile = File(..., description="要识别的文件"),
        file_service: FileService = Depends(get_file_service)
):
    print(task_name)
    print(file.filename)
    print(file.content_type)
    print(file.size)
    info = await file_service.create_task(file)

    return Result.success(message=info)
