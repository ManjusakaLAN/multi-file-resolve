from starlette import status

from core.exception import AppException


class McpException(AppException):
    """MCP异常"""

    def __init__(self, message: str, code: int = 400, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(
            message=message,
            code=code,
            status_code=status_code
        )



class KBException(AppException):
    """知识库异常"""

    def __init__(self, message: str, code: int = 400, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(
            message=message,
            code=code,
            status_code=status_code
        )




class ModelException(AppException):
    """模型异常"""

    def __init__(self, message: str, code: int = 400 , status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(
            message=message,
            code=code,
            status_code=status_code
        )


class CredentialException(AppException):
    """凭据异常"""

    def __init__(self, message: str, code: int = 400, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(
            message=message,
            code=code,
            status_code=status_code
        )
