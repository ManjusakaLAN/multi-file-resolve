# 初始化迁移脚本
alembic init
# 数据库迁移命令
alembic revision --autogenerate -m "init"
# 更新到最新版本:
alembic upgrade head
# 向上更新一个版本:
alembic upgrade +1
# 更新到指定版本:
alembic upgrade <revision_id> (ID 可以在脚本文件名中找到)

# 导出项目依赖
pip list --format=freeze > requirements.txt

# 本地开发混合启动命令(不在生产环境使用)
celery -A core.infrastructure.celery_app worker -B -l info

# 启动celery 异步任务
celery -A core.infrastructure.celery_app worker -l info --pool=threads --concurrency=4

# 启动celery 定时任务
celery -A core.infrastructure.celery_app beat -l info
