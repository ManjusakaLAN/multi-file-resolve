import uvicorn
from fastapi import FastAPI
from api.router import api_router
from infrastructure.lifespan import lifespan
from middleware.cors import init_middleware
from config.config import settings

def create_app() -> FastAPI:
    """应用工厂函数"""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        lifespan=lifespan
    )

    # 1. 初始中间件 (跨域等)
    init_middleware(app)

    # 2. 注册总路由
    app.include_router(api_router, prefix=settings.API_V1_STR)

    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)