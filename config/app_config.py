from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    PROJECT_NAME: str = "My FastAPI Project"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True
    CLEAN_DB_ON_START: bool = False  # 默认 False，生产环境务必保持 False