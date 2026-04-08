from typing import List, Optional

from fastapi import Depends, Body, Request

from api.auth import permission_router
from api.deps import get_permission_service, PermissionChecker
from schemas.general import Result, PageResponse
from schemas.permission import RoleCreate, Role, RoleUpdate, PermissionCreate, PermissionUpdate, Permission
from schemas.user import UserInfo
from services.auth.permission_service import PermissionService


@permission_router.post("/role/add", response_model=Result[Role])
async def add_role(
        role_create: RoleCreate,
        permission_service: PermissionService = Depends(get_permission_service),
):
    """
    创建角色
    :param role_create:
    :param permission_service:
    :return:
    """
    return Result.success(message="创建角色成功",
                          data=await permission_service.create_role(role_create.name, role_create.code,
                                                                    role_create.description))


@permission_router.put("/role/edit", response_model=Result[Role])
async def edit_role(
        role_create: RoleUpdate,
        permission_service: PermissionService = Depends(get_permission_service),
):
    """
    修改角色
    :param role_create:
    :param permission_service:
    :return:
    """
    return Result.success(message="修改角色成功",
                          data=await permission_service.update_role(role_create.id, role_create.name, role_create.code,
                                                                    role_create.description))


@permission_router.get("/role/list",
                       response_model=Result[List[Role]])
async def list_role(
        permission_service: PermissionService = Depends(get_permission_service)
):
    """
    获取角色列表
    :param permission_service:
    :return:
    """
    return Result.success(message="获取角色列表成功",
                          data=await permission_service.get_roles())


@permission_router.delete("/role/delete", response_model=Result[str])
async def delete_role(
        role_ids: List[str] = Body(..., embed=True),
        permission_service: PermissionService = Depends(get_permission_service),
):
    """
    删除角色
    :param role_ids:
    :param permission_service:
    :return:
    """
    for role_id in role_ids:
        await permission_service.delete_role(role_id)

    return Result.success(message="删除角色成功")


@permission_router.post("/role/user_bind", response_model=Result[str])
async def user_bind_role(
        user_id: str = Body(...),
        role_ids: List[str] = Body(..., embed=True),
        permission_service: PermissionService = Depends(get_permission_service),
):
    """
    绑定角色
    :param user_id:
    :param role_ids:
    :param permission_service:
    :return:
    """
    await permission_service.assign_roles_to_user(user_id, role_ids)
    return Result.success(message="绑定角色成功")


@permission_router.delete("/role/user_unbind", response_model=Result[str])
async def user_unbind_role(
        user_id: str = Body(...),
        role_id: str = Body(...),
        permission_service: PermissionService = Depends(get_permission_service),
):
    """
    解绑角色
    :param user_id:
    :param role_id:
    :param permission_service:
    :return:
    """
    await permission_service.unbind_role_from_user(user_id, role_id)
    return Result.success(message="解绑角色成功")


@permission_router.post("/permission/add")
async def add_permission(
        permission_create: PermissionCreate,
        permission_service: PermissionService = Depends(get_permission_service),
):
    """
    添加权限
    :param permission_create:
    :param permission_service:
    :return:
    """
    await permission_service.create_permission(permission_create.name, permission_create.code)
    return Result.success(message="添加权限成功")


@permission_router.put("/permission/edit")
async def edit_permission(
        permission_update: PermissionUpdate,
        permission_service: PermissionService = Depends(get_permission_service),
):
    """
    修改权限
    :param permission_update:
    :param permission_service:
    :return:
    """
    await permission_service.update_permission(permission_update.id, permission_update.name, permission_update.code,
                                               permission_update.resource_type)
    return Result.success(message="修改权限成功")


@permission_router.get("/permission/page_list", response_model=PageResponse[Permission])
async def page_list_permission(
        name: str = "",
        code: str = "",
        page: Optional[int] = 1,
        page_size: Optional[int] = 10,
        permission_service: PermissionService = Depends(get_permission_service),
):
    """
    分页获取权限列表
    :param page_size:
    :param code:
    :param name:
    :param page:
    :param permission_service:
    :return:
    """
    return await permission_service.page_get_permissions(name, code, page, page_size)


@permission_router.get("/permission/list", response_model=Result[List[Permission]])
async def list_permission(
        name: str = "",
        code: str = "",
        permission_service: PermissionService = Depends(get_permission_service),
):
    """
    获取权限列表
    :param code:
    :param name:
    :param permission_service:
    :return:
    """
    return Result.success(message="获取权限列表成功",
                          data=await permission_service.get_permissions(code, name))


@permission_router.delete("/permission/delete", response_model=Result[str])
async def delete_permission(
        permission_ids: List[str] = Body(..., embed=True),
        permission_service: PermissionService = Depends(get_permission_service),
):
    """
    删除权限
    :param permission_ids:
    :param permission_service:
    :return:
    """
    for permission_id in permission_ids:
        await permission_service.delete_permission(permission_id)

    return Result.success(message="删除权限成功")


@permission_router.post("/permission/role_bind", response_model=Result[str])
async def role_bind_permission(
        role_id: str = Body(...),
        permission_ids: List[str] = Body(..., embed=True),
        permission_service: PermissionService = Depends(get_permission_service),
):
    """
    绑定权限
    :param role_id:
    :param permission_ids:
    :param permission_service:
    :return:
    """
    await permission_service.bind_permissions_to_role(role_id, permission_ids)
    return Result.success(message="绑定权限成功")


@permission_router.delete("/permission/role_unbind", response_model=Result[str])
async def role_unbind_permission(
        role_id: str = Body(...),
        permission_id: str = Body(...),
        permission_service: PermissionService = Depends(get_permission_service),
):
    """
    解绑权限
    :param role_id:
    :param permission_id:
    :param permission_service:
    :return:
    """
    await permission_service.unbind_permission_from_role(role_id, permission_id)
    return Result.success(message="解绑权限成功")


@permission_router.get("/user/info", response_model=Result[UserInfo])
async def get_user_info(
        request: Request,
        permission_service: PermissionService = Depends(get_permission_service),
):
    """
    获取用户信息
    :param request:
    :param permission_service:
    :return:
    """
    return Result.success(message="获取用户信息成功",
                          data=await permission_service.get_user_info(request.state.user_id))


@permission_router.get("/role/permission/list", response_model=Result[List[Permission]])
async def list_role_permission(
        role_id: str = "",
        permission_service: PermissionService = Depends(get_permission_service),
):
    """
    获取角色权限列表
    :param role_id:
    :param permission_service:
    :return:
    """
    return Result.success(message="获取角色权限列表成功",
                          data=await permission_service.list_role_permission(role_id))
