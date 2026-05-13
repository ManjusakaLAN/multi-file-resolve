from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import  NullPool
from core.config import settings

# 1. 创建异步引擎
engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=settings.DB_LOG,  # 生产环境建议设为 False，设为 True 会打印所有 SQL 语句
    pool_pre_ping=True,  # 自动检查连接是否可用
    poolclass=NullPool,  # 👈 增加这一行，禁用连接池缓存
)

# 2. 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# 3. 创建声明式基类，供 models 继承
class Base(DeclarativeBase):
    pass


# 4. 依赖注入函数：获取数据库连接
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# infrastructure/database.py
from sqlalchemy import text, NullPool  # 必须导入这个


async def reset_database():
    """清空并重建所有数据库表"""
    async with engine.begin() as conn:
        # 使用 text() 包装 SQL 字符串
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))

        # 删除所有表
        await conn.run_sync(Base.metadata.drop_all)

        # 重新创建所有表
        await conn.run_sync(Base.metadata.create_all)

        # 恢复外键检查
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    print("♻️ 数据库已清空并重建")