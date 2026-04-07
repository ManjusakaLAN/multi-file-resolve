from fastapi import APIRouter

from api.auth import login

api_router = APIRouter()

# 统一挂载路由
api_router.include_router(login.router)
