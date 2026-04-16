## 目录结构

```
multi-file-resolve/
├── .env                                    # 环境变量配置（数据库凭证、项目设置）
├── .gitignore                              # Git 忽略规则
├── alembic.ini                             # Alembic 数据库迁移配置
├── Dockerfile                              # Docker 镜像定义（占位）
├── main.py                                 # FastAPI 应用入口
├── requirements.txt                        # Python 依赖
├── README.md                               # 项目说明
├── __init__.py                             # 根包标记
│
├── alembic/                                # 数据库迁移脚本
│   ├── env.py                              # Alembic 环境配置（异步URL转同步）
│   ├── script.py.mako                      # 迁移模板
│   ├── README                              # Alembic 说明
│   └── versions/
│
├── api/                                    # API 路由层
│   ├── __init__.py
│   ├── deps.py                             # 依赖注入（数据库会话、FileService）
│   ├── router.py                           # 顶层路由，挂载 v1 子路由
│   └── v1/
│       ├── __init__.py
│       └── file_recognize.py               # 文件识别任务接口（分页查询）
│
├── core/                                   # 核心基础设施
│   ├── __init__.py
│   ├── config/                             # 配置管理
│   │   ├── __init__.py                     # Settings 组合类，导出单例 settings
│   │   ├── app_config.py                   # AppSettings: 项目名、API前缀、调试模式、时区
│   │   └── infrastructure_config.py        # MySQLSettings: 数据库凭证、异步连接URL
│   ├── enum/                               # 枚举定义
│   │   ├── __init__.py
│   │   └── status.py                       # FileRecognizeTaskStatus (RESOLVING/FINISH/FAILED)
│   ├── infrastructure/                     # 基础设施
│   │   ├── __init__.py
│   │   ├── database.py                     # 异步 SQLAlchemy 引擎、会话工厂、Base 模型
│   │   └── lifespan.py                     # FastAPI 生命周期管理（DB初始化、调度器启停）
│   └── middleware/                         # 中间件
│       ├── __init__.py
│       └── cors.py                         # CORS 中间件初始化（当前为占位）
│
├── docker/                                 # Docker 相关（预留）
│
├── models/                                 # SQLAlchemy ORM 模型
│   ├── __init__.py
│   └── file_task.py                        # FileRecognizeTask、FileRecognizeWorker
│
├── scheduler/                              # 定时任务
│   ├── __init__.py
│   └── tasks.py                            # APScheduler 后台任务（清理任务占位）
│
├── schemas/                                # Pydantic 数据验证模型
│   ├── __init__.py
│   ├── date.py                             # CustomDatetime: 时区感知的时间序列化
│   ├── file_recognize_task.py              # 任务的 Base/Create/Update/Response Schema
│   └── page.py                             # 通用 PageResponse[T] 分页响应模型
│
├── services/                               # 业务逻辑层
│   ├── __init__.py
│   └── file_service.py                     # FileRecognizeTask CRUD 操作
│
├── temp/                                   # 临时文件目录（预留）
│
├── tests/                                  # 测试目录（预留）
│
└── util/                                   # 工具函数
    ├── __init__.py
    ├── db_util.py                          # paginate() 通用分页助手
    └── file_util.py                        # PDF页数统计、LibreOffice格式转换
```

---

## 技术栈

| 类别 | 依赖 | 版本 | 用途 |
|------|------|------|------|
| Web 框架 | `fastapi` | 0.135.2 | 异步 Web 框架 |
| ASGI 服务器 | `uvicorn` | 0.42.0 | ASGI 服务器 |
| ORM | `SQLAlchemy` | 2.0.48 | 异步 ORM |
| 数据库驱动 | `aiomysql` | 0.3.2 | 异步 MySQL 驱动 |
| 数据库驱动 | `PyMySQL` | 1.1.2 | 同步 MySQL 驱动（Alembic 用） |
| 数据库迁移 | `alembic` | 1.18.4 | 数据库 Schema 迁移 |
| 数据验证 | `pydantic` | 2.12.5 | 数据验证与序列化 |
| 配置管理 | `pydantic-settings` | 2.13.1 | 环境变量配置管理 |
| 定时任务 | `APScheduler` | 3.11.2 | 后台任务调度 |
| PDF 处理 | `pypdf` | 6.9.2 | PDF 文件读取与页数统计 |
| 环境变量 | `python-dotenv` | 1.2.2 | .env 文件加载 |
| 加密 | `cryptography` | 46.0.6 | 加密原语 |

---

## 架构模式

1. **分层架构**: `api` (路由) → `services` (业务逻辑) → `models` (ORM) → `schemas` (DTO)
2. **工厂模式**: `create_app()` 构建 FastAPI 应用
3. **依赖注入**: FastAPI `Depends()` 注入数据库会话和服务实例
4. **Service 模式**: `FileService` 封装所有数据库操作
5. **DTO 模式**: Pydantic Schema 分离请求/响应契约与数据库模型
6. **泛型分页**: `PageResponse[T]` 通用分页响应模型
7. **生命周期管理**: FastAPI async lifespan 管理启动/关闭
8. **配置管理**: pydantic-settings 多继承组合配置
9. **全异步设计**: 异步 SQLAlchemy 引擎、异步会话、异步路由

