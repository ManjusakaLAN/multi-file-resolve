import logging

from fastapi import APIRouter, Depends
from fastapi.params import Query

from api.deps import get_file_service
from schemas.file_recognize_task import FileRecognizeTask
from schemas.page import PageResponse
from services.file_service import FileService

router = APIRouter(dependencies=[])
logger = logging.getLogger(__name__)

@router.get("/", response_model=PageResponse[FileRecognizeTask])
async def read_items(
        file_name: str = Query(None),
        page: int = Query(1, ge=1),
        size: int = Query(10, ge=1, le=100),
        service: FileService = Depends(get_file_service)
):
    logger.info(f"正在查询文件列表，关键字: {file_name}")
    logger.error("这是一个错误日志")
    logger.debug("这是一个调试日志")
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

