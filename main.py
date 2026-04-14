import uvicorn
from fastapi import FastAPI
from api.router import api_router
from core.config.log_config import setup_logging
from core.exception.handler import register_exception_handlers
from core.infrastructure.lifespan import lifespan
from core.middleware.cors import init_cors
from core.config import settings


def create_app() -> FastAPI:
    # 初始化日志模块
    setup_logging()

    """应用工厂函数"""
    echo_app = FastAPI(
        title=settings.PROJECT_NAME,
        lifespan=lifespan
    )

    # 初始跨域配置
    init_cors(echo_app)

    # 注册总路由
    echo_app.include_router(api_router)

    # 挂载全局异常处理器
    register_exception_handlers(echo_app)

    return echo_app


app = create_app()

if __name__ == "__main__":
    # 打印项目运行端口
    print(f"🚀 项目运行端口：{settings.SERVER_PORT}")
    uvicorn.run("main:app", host="0.0.0.0", port=settings.SERVER_PORT, reload=False)
