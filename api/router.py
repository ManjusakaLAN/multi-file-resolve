from fastapi import APIRouter
from api.v1 import file_recognize
api_router = APIRouter()

# 统一挂载 v1 版本的路由
api_router.include_router(file_recognize.router, prefix="/file_recognize", tags=["文件识别任务"])

# 如果以后有 v2 版本，可以继续在这里扩展
# api_router.include_router(v2_router, prefix="/v2")