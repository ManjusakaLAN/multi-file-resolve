from api.deps import get_contract_service, get_storage
from core.infrastructure.database import AsyncSessionLocal
from services.file.file_service import FileService


async def execute_contract_preview():
    async with AsyncSessionLocal() as db:
        minio_client = await get_storage()
        file_service = FileService(db, minio_client)
        contract_service = await get_contract_service(db, file_service, minio_client)
        await contract_service.contract_preview()
