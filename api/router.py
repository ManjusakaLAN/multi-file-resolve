from fastapi import APIRouter

from api.auth import login,permission

api_router = APIRouter()

# 统一挂载路由
api_router.include_router(login.login_router)
api_router.include_router(permission.permission_router)
