from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from config.config import settings


def init_middleware(app: FastAPI):
    pass
    # 跨域配置
    # if settings.ALLOW_ORIGINS:
    #     app.add_middleware(
    #         CORSMiddleware,
    #         allow_origins=[str(origin) for origin in settings.ALLOW_ORIGINS],
    #         allow_credentials=True,
    #         allow_methods=["*"],
    #         allow_headers=["*"],
    #     )

    # 你还可以在这里添加自定义中间件（如日志、请求计时等）