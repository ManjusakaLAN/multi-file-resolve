from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from core.config import settings
from core.infrastructure.database import engine, reset_database, AsyncSessionLocal
from core.infrastructure.cache import redis_manager, get_redis_client
from scheduler.tasks import cleanup_expired_users
from services.init.init_service import InitService
from api.deps import get_storage, get_milvus


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- 【启动阶段】 ----
    # 缓存初始化
    await redis_manager.init_redis()

    # 存储中间件初始化
    minio_client = await get_storage()
    minio_client.init_client()

    milvus_vdb = await get_milvus()

    # 检查配置：如果设置为 True，则重置数据库
    if settings.CLEAN_DB_ON_START:
        print("⚠️ 警告：检测到 CLEAN_DB_ON_START=True，正在清空数据库 以及 向量数据库")
        await reset_database()

        collections = milvus_vdb.list_all_collections()
        for collection in collections:
            milvus_vdb.drop_collection(collection)

        # 重新初始化数据
        print("♻️ 正在初始化数据库...")
        async with AsyncSessionLocal() as db:
            redis = get_redis_client()
            service = InitService(db, redis, milvus_vdb)
            await service.init_basic_data()
        print("♻️ 数据库已清空并重建")

    # 启动定时任务
    scheduler = AsyncIOScheduler()
    # 使用 interval 触发器，设置 seconds=10
    scheduler.add_job(
        cleanup_expired_users,
        "interval",
        seconds=10
    )
    scheduler.start()
    print("🚀 基础设施已就绪，定时任务已启动")

    yield  # 分界线：上方是启动，下方是关闭

    # ---- 【关闭阶段】 ----
    # 停止调度器
    scheduler.shutdown()
    print("⏰ 定时任务已安全关闭")

    # 释放redis连接
    await redis_manager.close_redis()
    print("🛑 Redis 连接已释放")

    # 释放数据库连接
    await engine.dispose()
    print("🛑 数据库连接已释放")

    # 释放 Milvus 连接
    milvus_vdb.close()
    print("🛑 Milvus 链接已释放")
