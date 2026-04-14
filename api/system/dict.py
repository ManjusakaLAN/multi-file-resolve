from typing import Optional

from api.deps import get_dict_service
from api.system import system_router
from fastapi import Depends, Query, Body
from schemas.dict import DictCreate, DictResponse, DictUpdate
from schemas.general import Result, PageResponse
from services.system.dict_service import DictService


@system_router.get("/dict/page_list", response_model=PageResponse[DictResponse], description="分页查询字典信息")
async def dict_page_list(
        dict_code: str = Query("", description="字典编码"),
        label: str = Query("", description="字典标签"),
        value: str = Query("", description="字典键值"),
        is_system: Optional[int | str] = Query(None, description="是否系统内置"),
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=1000),
        dict_service: DictService = Depends(get_dict_service),
):
    return await dict_service.page_list_dict(dict_code, label, value, is_system, page, page_size)

@system_router.get("/dict/list", response_model=Result[list[DictResponse]], description="查询字典信息")
async def dict_list(
        dict_code: str = Query("", description="字典编码"),
        label: str = Query("", description="字典标签"),
        value: str = Query("", description="字典键值"),
        is_system: Optional[int | str] = Query(None, description="是否系统内置"),
        dict_service: DictService = Depends(get_dict_service),
):
    return Result.success(message="查询成功", data=await dict_service.list_dict(dict_code, label, value, is_system))

@system_router.post("/dict/create", response_model=Result[DictResponse], description="创建字典信息")
async def dict_create(
        create_dict: DictCreate,
        dict_service: DictService = Depends(get_dict_service),
):
    return Result.success(message="创建成功", data=await dict_service.create_dict(**create_dict.model_dump()))


@system_router.put("/dict/update", response_model=Result[DictResponse], description="更新字典信息")
async def dict_update(
        update_dict: DictUpdate,
        dict_service: DictService = Depends(get_dict_service),
):
    return Result.success(message="更新成功", data=await dict_service.update_dict(**update_dict.model_dump()))


@system_router.delete("/dict/delete", response_model=Result[bool], description="删除字典信息")
async def dict_delete(
        dict_id: str = Body(..., description="字典ID", embed=True),
        dict_service: DictService = Depends(get_dict_service),
):
    return Result.success(message="删除成功", data=await dict_service.delete_dict(dict_id))
