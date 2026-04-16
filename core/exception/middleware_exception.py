from starlette import status

from core.exception import AppException


class DBException(AppException):
    """数据库异常"""

    def __init__(self, message: str, code: int = 400, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(
            message=message,
            code=code,
            status_code=status_code
        )
