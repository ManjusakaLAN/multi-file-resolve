from sqlalchemy.ext.asyncio import AsyncSession

class AgentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def contract_judge_agent(self, contract_id: str):