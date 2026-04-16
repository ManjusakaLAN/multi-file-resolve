from starlette import status

from core.exception import AppException


class UserLoginException(AppException):
    """用户登录异常"""

    def __init__(self, message: str, code: int = 400, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(
            message=message,
            code=code,
            status_code=status_code
        )


class UserRegisterException(AppException):
    """用户注册异常"""

    def __init__(self, message: str, code: int = 400, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(
            message=message,
            code=code,
            status_code=status_code
        )



class CaptchaExpireOrNotExistError(AppException):
    """验证码异常"""

    def __init__(self, message: str, code: int = 400, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(
            message=message,
            code=code,
            status_code=status_code
        )


class UserEditException(AppException):
    """用户修改异常"""

    def __init__(self, message: str, code: int = 400, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(
            message=message,
            code=code,
            status_code=status_code
        )
