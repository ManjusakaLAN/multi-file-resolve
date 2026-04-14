from fastapi import APIRouter, Depends

from api.deps import verify_token

mcp_router = APIRouter(prefix="/mcp", tags=["MCP 模型上下文协议"], dependencies=[Depends(verify_token)])