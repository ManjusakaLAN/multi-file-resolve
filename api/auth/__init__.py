from fastapi import APIRouter, Depends

from api.deps import verify_token

login_router = APIRouter(prefix="/auth", tags=["登录"])
permission_router = APIRouter(prefix="/auth", tags=["权限管理"], dependencies=[Depends(verify_token)])