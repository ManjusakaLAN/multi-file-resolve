from fastapi import status

class AppException(Exception):
    """全局业务异常基类"""
    def __init__(
        self,
        message: str,
        code: int = 400,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        detail: str = ""
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.detail = detail


