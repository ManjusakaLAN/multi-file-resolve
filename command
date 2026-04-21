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
