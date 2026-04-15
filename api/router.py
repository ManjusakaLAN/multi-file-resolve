from fastapi import APIRouter

from api.auth import login_api, permission_api
from api.file import file_api
from api.system import user_api, dict_api, system_router
from api.llm import mcp_api,mcp_router
from api.kb import kb_api, kb_router
api_router = APIRouter()

# 统一挂载路由
api_router.include_router(login_api.login_router)
api_router.include_router(permission_api.permission_router)
api_router.include_router(file_api.file_router)
api_router.include_router(system_router)
api_router.include_router(mcp_router)
api_router.include_router(kb_router)
