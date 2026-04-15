import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import configparser

# 确保 alembic 能找到你的 app 目录
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 导入你的配置和模型
from core.config import settings
from core.infrastructure.database import Base

# 必须导入模型类，Alembic 才能检测到表
from models import user
from models import file
from models import dict
from models import knowledge

# Alembic Config 对象
config = context.config

# --- 核心修复：禁用百分号 (%) 的插值检查 ---
# 这样带 % 的转义密码就不会报错了
section = config.config_ini_section
config.file_config = configparser.ConfigParser(interpolation=None)
if config.config_file_name:
    config.file_config.read(config.config_file_name)

# 解释：从 settings.db 获取异步 URL 并转为同步驱动给 Alembic 使用
# 因为 Alembic 默认运行在同步环境
database_url = settings.ASYNC_DATABASE_URL.replace("aiomysql", "pymysql")
config.set_section_option(section, "sqlalchemy.url", database_url)

# 解释：配置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 解释：设置元数据
target_metadata = Base.metadata
print(f"Detected tables: {Base.metadata.tables.keys()}")
def run_migrations_offline() -> None:
    """在 'offline' 模式下运行迁移"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """在 'online' 模式下运行迁移"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()