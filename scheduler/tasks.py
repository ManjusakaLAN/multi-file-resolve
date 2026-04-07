from core.infrastructure.database import AsyncSessionLocal

async def cleanup_expired_users():
    # print("⏰ 正在执行定时清理任务...")
    async with AsyncSessionLocal() as db:
        pass