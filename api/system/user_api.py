from typing import Optional

from api.deps import get_user_service, PermissionChecker
from api.system import system_router
from fastapi import Depends, Query, Body

from core.enum.status import UserStatus
from schemas.general import Result, PageResponse
from schemas.user import User, UserCreate, UserUpdate
from services.user.user_service import UserService


@system_router.get("/user/page_list", response_model=PageResponse[User], description="分页查询用户信息")
async def user_page_list(
        account_name: str = Query("", description="账号名"),
        user_name: str = Query("", description="用户名"),
        status: Optional[UserStatus | str] = Query(None, description="状态"),
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=1000),
        user_service: UserService = Depends(get_user_service),
):
    """
    分页查询用户信息
    :param account_name:
    :param user_name:
    :param status:
    :param page:
    :param page_size:
    :param user_service:
    :return:
    """
    return await user_service.page_list_user(
        account_name=account_name,
        user_name=user_name,
        user_status=status,
        page=page,
        page_size=page_size
    )


@system_router.get("/user/get", response_model=Result[User], description="获取用户信息")
async def user_get(
        user_id: str,
        user_service: UserService = Depends(get_user_service),
):
    """
    获取用户信息
    :param user_id:
    :param user_service:
    :return:
    """
    return Result.success(await user_service.get_user_by_id(user_id))


@system_router.post("/user/create", response_model=Result[User], description="创建用户")
async def user_create(
        user: UserCreate,
        user_service: UserService = Depends(get_user_service),
):
    """
    创建用户
    :param user:
    :param user_service:
    :return:
    """
    return Result.success(await user_service.create_user(user))


@system_router.put("/user/update", response_model=Result[User], description="更新用户信息")
async def user_update(
        user: UserUpdate,
        user_service: UserService = Depends(get_user_service),
):
    """
    更新用户信息
    :param user:
    :param user_service:
    :return:
    """
    return Result.success(await user_service.update_user(
        user_id=user.id,
        user_name=user.user_name,
        email=user.email,
        avatar=user.avatar,
        status=user.status
    ))


@system_router.delete("/user/delete", response_model=Result[bool], description="删除用户")
async def user_delete(
        user_id: str = Body(..., description="用户ID", embed=True),
        user_service: UserService = Depends(get_user_service),
):
    """
    删除用户
    :param user_id:
    :param user_service:
    :return:
    """
    return Result.success(await user_service.delete_user(user_id))


@system_router.put("/user/change_password", response_model=Result[User], description="修改用户密码")
async def user_change_password(
        user_id: str = Body(..., description="用户ID", embed=True),
        old_password: str = Body(..., description="旧密码", embed=True),
        new_password: str = Body(..., description="新密码", embed=True),
        confirm_password: str = Body(..., description="确认密码", embed=True),
        user_service: UserService = Depends(get_user_service),
):
    """
    修改用户密码
    :param confirm_password:
    :param user_id:
    :param old_password:
    :param new_password:
    :param user_service:
    :return
    """
    return Result.success(await user_service.change_password(user_id, old_password, new_password, confirm_password))


@system_router.post("/user/reset_password", response_model=Result[User], description="重置用户密码",
                    dependencies=[Depends(PermissionChecker(required_roles=['admin']))])
async def user_reset_password(
        user_id: str = Body(..., description="用户ID", embed=True),
        password: str = Body(..., description="新密码", embed=True),
        user_service: UserService = Depends(get_user_service),
):
    """
    管理员重置用户密码
    :param user_id:
    :param password:
    :param user_service:
    :return:
    """
    return Result.success(message="修改用户密码成功", data=await user_service.reset_password(user_id, password))
