from typing import Optional

from api.deps import get_kb_service, get_task_service
from api.kb import kb_router
from fastapi import Depends, Request, Body

from core.enum.kb import KBType
from schemas.general import Result, PageResponse
from schemas.knowledge import KnowledgeBaseResponse, KnowledgeBaseCreate, KnowledgeBaseUpdate, KnowledgeBaseDetail, \
    KnowledgeBaseStarResponse
from services.kb.kb_service import KBService
from services.kb.task_service import TaskService


@kb_router.post("/create", response_model=Result[KnowledgeBaseResponse], description="创建知识库")
async def create_kb(
        kb_create: KnowledgeBaseCreate,
        request: Request,
        kb_service: KBService = Depends(get_kb_service),
):
    """
    创建知识库
    :param kb_create:
    :param request:
    :param kb_service:
    :return:
    """
    return Result.success(message="创建成功",
                          data=await kb_service.create_kb(**kb_create.model_dump(), user_id=request.state.user_id))


@kb_router.get("/page_list", response_model=Result[PageResponse[KnowledgeBaseResponse]],
               description="分页查询知识库列表")
async def kb_page_list(
        request: Request,
        kb_name: Optional[str] = None,
        kb_type: Optional[str | KBType] = None,
        page: int = 1,
        page_size: int = 10,
        kb_service: KBService = Depends(get_kb_service),
):
    """
    分页查询知识库列表
    :param kb_type:
    :param request:
    :param kb_name:
    :param page:
    :param page_size:
    :param kb_service:
    :return:
    """
    return Result.success(message="查询成功",
                          data=await kb_service.page_list_kb(kb_name=kb_name,kb_type=kb_type, user_id=request.state.user_id, page=page,
                                                             page_size=page_size))


@kb_router.get("/list", response_model=Result[list[KnowledgeBaseResponse]], description="查询知识库列表")
async def kb_list(
        request: Request,
        kb_name: Optional[str] = None,
        kb_service: KBService = Depends(get_kb_service),
):
    """
    查询知识库列表
    :param request:
    :param kb_name:
    :param kb_service:
    :return:
    """
    return Result.success(message="查询成功",
                          data=await kb_service.list_kb(kb_name=kb_name, user_id=request.state.user_id))


@kb_router.put("/update", response_model=Result[KnowledgeBaseResponse], description="更新知识库")
async def update_kb(
        kb_update: KnowledgeBaseUpdate,
        kb_service: KBService = Depends(get_kb_service),
):
    """
    更新知识库
    :param kb_update:
    :param kb_service:
    :return:
    """
    return Result.success(message="更新成功", data=await kb_service.update_kb(**kb_update.model_dump()))


@kb_router.delete("/logic_delete", response_model=Result[bool], description="删除知识库")
async def logic_delete_kb(
        kb_id: str = Body(..., description="知识库ID", embed=True),
        kb_service: KBService = Depends(get_kb_service),
):
    """
    逻辑删除知识库
    :param kb_id:
    :param kb_service:
    :return:
    """
    return Result.success(message="删除成功", data=await kb_service.logic_delete_kb(kb_id))


@kb_router.get("/detail", response_model=Result[KnowledgeBaseDetail], description="获取知识库详情(权限信息等)")
async def get_kb_detail(
        kb_id: str,
        request: Request,
        kb_service: KBService = Depends(get_kb_service),
):
    """
    获取知识库详情(权限信息等)
    :param request:
    :param kb_id:
    :param kb_service:
    :return:
    """
    return Result.success(message="查询成功", data=await kb_service.get_kb_detail(kb_id, request.state.user_id))


@kb_router.get("/created/page_list", response_model=Result[PageResponse[KnowledgeBaseResponse]],
               description="分页查询用户自己创建的知识库列表")
async def created_kb_page_list(
        request: Request,
        kb_name: Optional[str] = None,
        kb_type: Optional[str | KBType] = None,
        page: int = 1,
        page_size: int = 10,
        kb_service: KBService = Depends(get_kb_service),
):
    """
    获取用户自身创建的知识库
    :param kb_type:
    :param request:
    :param kb_name:
    :param page:
    :param page_size:
    :param kb_service:
    :return:
    """
    return Result.success(message="查询成功",
                          data=await kb_service.page_list_created_kb(kb_name=kb_name, kb_type=kb_type,
                                                                     user_id=request.state.user_id,
                                                                     page=page, page_size=page_size))


@kb_router.post("/{kb_id}/join", response_model=Result[bool], description="用户加入知识库")
async def join_knowledge_base(
        kb_id: str,
        request: Request,
        kb_service: KBService = Depends(get_kb_service)
):
    """
    用户主动加入某个知识库
    """
    await kb_service.user_join_kb(user_id=request.state.user_id, kb_id=kb_id)
    return Result.success(message="成功加入知识库")


@kb_router.post("/{kb_id}/exit", response_model=Result[bool], description="用户退出知识库")
async def exit_knowledge_base(
        kb_id: str,
        request: Request,
        kb_service: KBService = Depends(get_kb_service)
):
    """
    用户退出已加入的知识库
    """
    await kb_service.user_exit_kb(user_id=request.state.user_id, kb_id=kb_id)
    return Result.success(message="已成功退出知识库")


@kb_router.post("/{kb_id}/star", response_model=Result[bool], description="收藏/星标知识库")
async def star_knowledge_base(
        kb_id: str,
        request: Request,
        kb_service: KBService = Depends(get_kb_service)
):
    """
    对已加入的知识库进行星标收藏
    """
    await kb_service.user_star_kb(user_id=request.state.user_id, kb_id=kb_id)
    return Result.success(message="收藏成功")


@kb_router.post("/{kb_id}/unstar", response_model=Result[bool], description="取消收藏/星标知识库")
async def unstar_knowledge_base(
        kb_id: str,
        request: Request,
        kb_service: KBService = Depends(get_kb_service)
):
    """
    取消知识库的星标状态
    """
    await kb_service.user_cancel_star_kb(user_id=request.state.user_id, kb_id=kb_id)
    return Result.success(message="取消收藏成功")


@kb_router.get("/join/page_list", response_model=Result[PageResponse[KnowledgeBaseStarResponse]],
               description="分页查询用户加入的知识库列表")
async def kb_join_page_list(
        request: Request,
        kb_name: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
        kb_service: KBService = Depends(get_kb_service),
):
    """
    分页获取加入的知识库
    :param request:
    :param kb_name:
    :param page:
    :param page_size:
    :param kb_service:
    :return:
    """
    return Result.success(message="查询成功",
                          data=await kb_service.get_join_kb(user_id=request.state.user_id, kb_name=kb_name, page=page,
                                                            page_size=page_size))


@kb_router.post("/file/upload", response_model=Result[str], description="文件上传至知识库并解析")
async def kb_file_upload(
        request: Request,
        file_keys=Body(..., description="所有待处理文件的访问key", embed=True),
        kb_id=Body(..., description="知识库ID", embed=True),
        task_type=Body(..., description="任务类型", embed=True),
        folder_id=Body(None, description="上传文件保存的目录ID", embed=True),
        task_service: TaskService = Depends(get_task_service),
):
    """
    文件上传至知识库
    :param folder_id:
    :param task_type:
    :param request:
    :param file_keys:
    :param kb_id:
    :param task_service:
    :return:
    """
    return Result.success(message=await task_service.generate_task(file_keys=file_keys, kb_id=kb_id,
                                                                   user_id=request.state.user_id, task_type=task_type,folder_id=folder_id))

@kb_router.post("/task/retry", response_model=Result[str], description="任务失败重试")
async def kb_task_retry(
        task_id=Body(..., description="任务ID", embed=True),
        task_service: TaskService = Depends(get_task_service),
):
    """
    任务失败重试
    :param task_id:
    :param task_service:
    :return:
    """
    return Result.success(message=await task_service.retry_task(task_id=task_id))