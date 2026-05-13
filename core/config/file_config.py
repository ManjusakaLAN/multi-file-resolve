from pydantic_settings import BaseSettings


class FileUploadSettings(BaseSettings):
    """
    文件上传配置 MB
    """
    MAX_UPLOAD_SIZE: int = 50

class FileResolveSettings(BaseSettings):
    """
    文件解析配置
    """
    MINERU_API_URL: str = "http://192.168.31.155:8000/file_parse"