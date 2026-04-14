from fastapi import APIRouter, Depends

from api.deps import verify_token

system_router = APIRouter(prefix="/system", tags=["用户管理"], dependencies=[Depends(verify_token)])