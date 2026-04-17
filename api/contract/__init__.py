from fastapi import APIRouter, Depends

from api.deps import verify_token

contract_router = APIRouter(prefix="/contract", tags=["合同"], dependencies=[Depends(verify_token)])