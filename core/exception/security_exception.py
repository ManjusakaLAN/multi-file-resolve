from starlette import status

from core.exception import AppException


class TokenException(AppException):
    """用户登录异常"""

    def __init__(self, message: str, code: int = 400, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(
            message=message,
            code=code,
            status_code=status_code
        )
