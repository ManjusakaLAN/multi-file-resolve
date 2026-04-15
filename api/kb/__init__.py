from fastapi import APIRouter, Depends

from api.deps import verify_token

kb_router = APIRouter(prefix="/kb", tags=["知识库"], dependencies=[Depends(verify_token)])