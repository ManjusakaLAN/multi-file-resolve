from fastapi import APIRouter, Depends

from api.deps import verify_token

mcp_router = APIRouter(prefix="/mcp", tags=["MCP 模型上下文协议"], dependencies=[Depends(verify_token)])

model_router = APIRouter(prefix="/model", tags=["模型管理"], dependencies=[Depends(verify_token)])

credential_router = APIRouter(prefix="/credential", tags=["凭据管理"], dependencies=[Depends(verify_token)])