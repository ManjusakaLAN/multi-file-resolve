from starlette import status

from core.exception import AppException


class TokenException(AppException):
    """用户登录异常"""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            code=400,
            status_code=status.HTTP_400_BAD_REQUEST
        )