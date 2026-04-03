from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from core.config import settings
from core.infrastructure.database import engine, reset_database
from scheduler.tasks import cleanup_expired_users


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- 【启动阶段】 ----
    # 1. 初始化数据库/Redis等
    # await redis_client.connect()
    # 检查配置：如果设置为 True，则重置数据库
    if settings.CLEAN_DB_ON_START:
        print("⚠️ 警告：检测到 CLEAN_DB_ON_START=True，正在清空数据库...")
        await reset_database()


    # 2. 初始化并启动调度器
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
    # 3. 停止调度器 (关键！)
    scheduler.shutdown()
    print("⏰ 定时任务已安全关闭")

    # 4. 释放数据库连接
    await engine.dispose()
    print("🛑 数据库连接已释放")