from idlelib.query import Query
from typing import Optional

from api.deps import get_kb_service
from api.kb import kb_router
from fastapi import Depends, Request, Body
from schemas.general import Result, PageResponse
from schemas.knowledge import KnowledgeBaseResponse, KnowledgeBaseCreate, KnowledgeBaseUpdate, KnowledgeBaseDetail
from services.kb.kb_service import KBService


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
        page: int = 1,
        page_size: int = 10,
        kb_service: KBService = Depends(get_kb_service),
):
    """
    分页查询知识库列表
    :param request:
    :param kb_name:
    :param kb_type:
    :param page:
    :param page_size:
    :param kb_service:
    :return:
    """
    return Result.success(message="查询成功",
                          data=await kb_service.page_list_kb(kb_name=kb_name, user_id=request.state.user_id, page=page,
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
        kb_id: str ,
        kb_service: KBService = Depends(get_kb_service),
):
    """
    获取知识库详情(权限信息等)
    :param kb_id:
    :param kb_service:
    :return:
    """
    return Result.success(message="查询成功", data=await kb_service.get_kb_detail(kb_id))

