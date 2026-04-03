from core.infrastructure.database import AsyncSessionLocal
from services.file_service import FileService


async def cleanup_expired_users():
    print("⏰ 正在执行定时清理任务...")
    async with AsyncSessionLocal() as db:
        # 将手动创建的 db 注入给 Service
        file_service = FileService(db)
        # try:
        #     await file_service.create_task("test.pdf", "md5", 1)
        #     await db.commit()
        # except Exception:
        #     await db.rollback()
        #     raise