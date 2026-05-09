from typing import Optional, List

from api.deps import get_credential_service
from api.llm import credential_router
from fastapi import Depends, Request, Query, Body

from schemas.general import Result, PageResponse
from schemas.llm import CredentialResponse, CredentialDetail, CredentialCreate, CredentialUpdate
from services.llm.credential_service import CredentialService


@credential_router.get("/page_list", response_model=PageResponse[CredentialResponse],
                       description="分页获取凭据")
async def get_credential_page_list(
        request: Request,
        name: Optional[str] = Query(None, description="凭据名称"),
        provider: Optional[str] = Query(None, description="供应商"),
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1),
        credential_service: CredentialService = Depends(get_credential_service)
):
    """
    凭据分页查询
    :param request:
    :param name:
    :param provider:
    :param page:
    :param page_size:
    :param credential_service:
    :return:
    """
    return await credential_service.page_list_credentials(request.state.user_id, name, provider, page, page_size)

@credential_router.get("/list", response_model=Result[List[CredentialResponse]],
                       description="获取凭据(不分页)")
async def get_credential_page_list(
        request: Request,
        name: Optional[str] = Query(None, description="凭据名称"),
        provider: Optional[str] = Query(None, description="供应商"),
        credential_service: CredentialService = Depends(get_credential_service)
):
    """
    凭据分页查询
    :param request:
    :param name:
    :param provider:
    :param credential_service:
    :return:
    """
    return Result.success(message="获取成功",data=await credential_service.list_credentials(request.state.user_id, name, provider))

@credential_router.get("/detail", response_model=Result[CredentialDetail], description="获取凭据详情")
async def get_credential_detail(
        request: Request,
        credential_id: str,
        credential_service: CredentialService = Depends(get_credential_service)
):
    """
    获取凭据详情
    :param request:
    :param credential_id:
    :param credential_service:
    :return:
    """
    return Result.success(message="获取成功",
                          data=await credential_service.get_credential_by_id(credential_id, request.state.user_id))


@credential_router.post("/create", response_model=Result[CredentialResponse], description="创建凭据")
async def create_credential(
        request: Request,
        obj_in: CredentialCreate,
        credential_service: CredentialService = Depends(get_credential_service)
):
    """
    创建凭据
    :param request:
    :param obj_in:
    :param credential_service:
    :return:
    """
    return Result.success(message="创建成功",
                          data=await credential_service.create_credential(request.state.user_id, obj_in))


@credential_router.put("/update", response_model=Result[CredentialResponse], description="更新凭据")
async def update_credential(
        request: Request,
        credential_update: CredentialUpdate,
        credential_service: CredentialService = Depends(get_credential_service)
):
    """
    更新凭据
    :param credential_update:
    :param request:
    :param credential_service:
    :return:
    """
    return Result.success(message="更新成功",
                          data=await credential_service.update_credential(request.state.user_id, credential_update))


@credential_router.delete("/delete", response_model=Result[bool], description="删除凭据")
async def delete_credential(
        request: Request,
        credential_id: str = Body(..., description="凭据ID", embed= True),
        credential_service: CredentialService = Depends(get_credential_service)
):
    """
    删除凭据
    :param request:
    :param credential_id:
    :param credential_service:
    :return:
    """
    return Result.success(message="删除成功",
                          data=await credential_service.delete_credential(credential_id, request.state.user_id))
