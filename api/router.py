from fastapi import APIRouter

from api.auth import login, permission
from api.file import file
from api.system import user, dict, system_router

api_router = APIRouter()

# 统一挂载路由
api_router.include_router(login.login_router)
api_router.include_router(permission.permission_router)
api_router.include_router(file.file_router)
api_router.include_router(system_router)
