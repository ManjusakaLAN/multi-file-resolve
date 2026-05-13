from typing import Optional

from api.audit import audit_router
from api.deps import get_task_service

from fastapi import Depends, Body

from core.enum.kb import AuditStatus, AnalysisStatus
from schemas.file_resolve_task import FileResolveTaskResponse
from schemas.general import Result, PageResponse
from services.kb.task_service import TaskService


@audit_router.get("/task/page_list", response_model=PageResponse[FileResolveTaskResponse])
async def audit_task_page_list(
        audit_status: AuditStatus | str =None,
        analysis_status: AnalysisStatus | str =None,
        file_name: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
        task_service: TaskService = Depends(get_task_service),
):
    return await task_service.task_page_list(file_name, audit_status, analysis_status, page, page_size)


@audit_router.post("/check", response_model=Result[str])
async def check_task(
        task_id: str = Body(..., description="任务ID", embed=True),
        audit_status: AuditStatus = Body(..., description="审核状态", embed=True),
        audit_opinion: str = Body(None, description="审核意见", embed=True),
        task_service: TaskService = Depends(get_task_service),
):
    """
    审核任务
    :param task_id:
    :param audit_status:
    :param audit_opinion:
    :param task_service:
    :return:
    """
    return Result.success(await task_service.check_task(task_id, audit_status, audit_opinion))
