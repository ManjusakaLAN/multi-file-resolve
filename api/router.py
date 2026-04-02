from fastapi import APIRouter
from api.v1 import items  # 导入各模块路由
from config.config import settings

api_router = APIRouter()

# 统一挂载 v1 版本的路由
api_router.include_router(items.router, prefix="/items", tags=["商品管理"])

# 如果以后有 v2 版本，可以继续在这里扩展
# api_router.include_router(v2_router, prefix="/v2")