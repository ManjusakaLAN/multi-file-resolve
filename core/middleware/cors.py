from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings

def init_cors(app: FastAPI) -> None:
    """
    初始化 CORS 中间件
    """
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware, # type: ignore
            # 允许跨域的源列表
            allow_origins=settings.CORS_ORIGINS,
            # 是否允许携带 Cookie
            allow_credentials=True,
            # 允许跨域的方法 (GET, POST, PUT, DELETE 等)
            allow_methods=["*"],
            # 允许跨域的请求头
            allow_headers=["*"],
        )