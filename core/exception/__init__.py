from fastapi import status

class AppException(Exception):
    """全局业务异常基类"""
    def __init__(
        self,
        message: str,
        code: int = 400,
        status_code: int = status.HTTP_400_BAD_REQUEST
    ):
        self.message = message
        self.code = code
        self.status_code = status_code

class TaskNotFoundException(AppException):
    """任务不存在异常"""
    def __init__(self, task_id: str):
        super().__init__(
            message=f"识别任务 [{task_id}] 不存在",
            code=400,
            status_code=status.HTTP_404_NOT_FOUND
        )

class FileProcessException(AppException):
    """文件处理异常"""
    def __init__(self, detail: str):
        super().__init__(
            message=f"文件处理失败: {detail}",
            code=400,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )