from fastapi import APIRouter, Depends

from api.deps import verify_token

audit_router = APIRouter(prefix="/audit", tags=["审核"], dependencies=[Depends(verify_token)])