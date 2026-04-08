from fastapi import APIRouter, Depends

from api.deps import verify_token

file_router = APIRouter(prefix="/file", tags=["文件"], dependencies=[Depends(verify_token)])