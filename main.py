import uvicorn
from fastapi import FastAPI
from api.router import api_router
from core.config.log_config import setup_logging
from core.exception.handler import register_exception_handlers
from core.infrastructure.lifespan import lifespan
from core.middleware.cors import init_middleware
from core.config import settings

def create_app() -> FastAPI:
    # 初始化日志模块
    setup_logging()

    """应用工厂函数"""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        lifespan=lifespan
    )

    # 初始中间件 (跨域等)
    init_middleware(app)

    # 注册总路由
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # 挂载全局异常处理器
    register_exception_handlers(app)

    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)