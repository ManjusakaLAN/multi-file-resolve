from pydantic_settings import BaseSettings


class FileUploadSettings(BaseSettings):
    """
    文件上传配置 MB
    """
    MAX_UPLOAD_SIZE: int = 50