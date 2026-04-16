from typing import Optional, List

from api.deps import get_credential_service, get_model_service
from api.llm import model_router
from fastapi import Depends, Request, Query, Body

from core.enum.model import ModelConfigType
from schemas.general import Result, PageResponse
from schemas.llm import LLMModelResponse, LLMModelCreate, LLMModelUpdate
from services.llm.model_service import LLMModelService


@model_router.get("/page_list", response_model=PageResponse[LLMModelResponse],
                  description="分页获取模型")
async def page_list_model(
        request: Request,
        model_name: Optional[str] = Query(None, description="模型名称"),
        model_code: Optional[str] = Query(None, description="模型标识"),
        provider: Optional[str] = Query(None, description="供应商"),
        config_type: Optional[ModelConfigType | str] = Query(None, description="配置类型"),
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1),
        model_service: LLMModelService = Depends(get_model_service)
):
    """
    模型分页查询
    :param request:
    :param model_name:
    :param model_code:
    :param provider:
    :param config_type:
    :param page:
    :param page_size:
    :param model_service:
    :return:
    """
    return await model_service.page_list_models(model_name, model_code, provider, config_type, request.state.user_id,
                                                page, page_size)

@model_router.get("/list", response_model=Result[List[LLMModelResponse]],
                  description="分页获取模型")
async def list_model(
        request: Request,
        model_name: Optional[str] = Query(None, description="模型名称"),
        model_code: Optional[str] = Query(None, description="模型标识"),
        provider: Optional[str] = Query(None, description="供应商"),
        model_service: LLMModelService = Depends(get_model_service)
):
    """
    模型查询(不分页)
    :param request:
    :param model_name:
    :param model_code:
    :param provider:
    :param model_service:
    :return:
    """
    return Result.success(message="查询成功", data= await model_service.list_models(model_name, model_code, provider))

@model_router.post("/create", response_model=Result[LLMModelResponse], description="创建模型")
async def create_model(
        request: Request,
        model_create: LLMModelCreate,
        model_service: LLMModelService = Depends(get_model_service)
):
    """
    创建模型
    :param request:
    :param model_create:
    :param model_service:
    :return:
    """
    return Result.success(message="创建成功",
                          data=await model_service.create_model(model_create, request.state.user_id))


@model_router.put("/update", response_model=Result[LLMModelResponse], description="更新模型")
async def update_model(
        model_update: LLMModelUpdate,
        model_service: LLMModelService = Depends(get_model_service)
):
    """
    更新模型
    :param model_update:
    :param model_service:
    :return:
    """
    return Result.success(message="更新成功", data=await model_service.update_model(model_update))

@model_router.delete("/delete", response_model=Result[bool], description="删除模型")
async def delete_model(
        model_id: str = Body(..., description="模型ID", embed= True),
        model_service: LLMModelService = Depends(get_model_service)
):
    """
    删除模型
    :param model_id:
    :param model_service:
    :return:
    """
    return Result.success(message="删除成功", data=await model_service.delete_model(model_id))