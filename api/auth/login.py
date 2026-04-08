from fastapi import Body, Depends, Response
from redis.asyncio import Redis
from redis.commands.helpers import random_string

from api.auth import login_router
from api.deps import get_login_service, get_remote_ip, get_redis, verify_token
from core.config import settings
from schemas.general import Result
from schemas.user import UserCreate, User
from services.auth.login_service import LoginService
from services.auth.token_service import TokenService
from util.auth_util import generate_captcha_image


@login_router.post("/register", response_model=Result[User])
async def register(
        user_create: UserCreate,
        login_service: LoginService = Depends(get_login_service),
):
    """
    用户注册
    :param user_create:
    :param login_service:
    :return:
    """
    return Result.success(message="注册成功", data=await login_service.register(user_create))


@login_router.post("/login", response_model=Result[dict])
async def login(
        account_name: str = Body(..., description="账号名(用于登录)"),
        password: str = Body(..., description="密码"),
        code: str = Body(None, description="验证码"),
        login_ip: str = Depends(get_remote_ip),
        login_service: LoginService = Depends(get_login_service),
):
    """
    登录接口
    :param login_service:
    :param login_ip: 登录ip
    :param account_name: 账号
    :param password: 密码
    :param code: 验证码
    :return:
    """
    return Result.success(message="登录成功", data=await login_service.login(account_name, password, code, login_ip))


@login_router.get("/captcha")
async def get_captcha(redis: Redis = Depends(get_redis)):
    """
    获取验证码
    :return:
    """
    captcha_text = random_string(settings.CAPTCHA_STR_LEN)
    image_data = generate_captcha_image(captcha_text)
    await redis.setex(captcha_text.strip().lower(), settings.CAPTCHA_TEXT_EXPIRE_TIME,
                      captcha_text)
    return Response(content=image_data, media_type="image/png")


@login_router.post("/logout", response_model=Result[str])
async def logout(
        login_service: LoginService = Depends(get_login_service),
        user_id: str = Depends(verify_token),
):
    """
    登出接口
    :param user_id:
    :param login_service:
    :return:
    """
    await login_service.logout(user_id)
    return Result.success(message="登出成功")


@login_router.post("/refresh_token", response_model=Result[str])
async def token_refresh(
        refresh_token: str = Body(..., description="刷新token", embed=True),
        redis: Redis = Depends(get_redis)
):
    """
    刷新Token
    :param refresh_token:
    :param redis:
    :return:
    """
    return Result.success(message="刷新成功", data=await TokenService.refresh_token(refresh_token, redis))
