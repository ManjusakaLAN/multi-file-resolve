from starlette import status

from core.exception import AppException


class McpException(AppException):
    """MCP异常"""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            code=400,
            status_code=status.HTTP_400_BAD_REQUEST
        )
