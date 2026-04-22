from api.deps import get_contract_service, get_storage
from core.infrastructure.database import AsyncSessionLocal
from services.contract.contract_agent_service import ContractAgentService
from services.file.file_service import FileService
from services.llm.model_service import LLMModelService


async def execute_contract_preview():
    async with AsyncSessionLocal() as db:
        minio_client = await get_storage()
        file_service = FileService(db, minio_client)
        model_service = LLMModelService(db)
        contract_agent_service = ContractAgentService(db)
        contract_service = await get_contract_service(
            db=db,
            file_service=file_service,
            contract_agent_service=contract_agent_service,
            model_service=model_service,
            minio_client=minio_client
        )
        await contract_service.contract_preview()
