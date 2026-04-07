from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

from core.exception import AppException

logger = logging.getLogger(__name__)

# 定义一个翻译字典
ERROR_MESSAGES = {
    "missing": "该字段不能为空",
    "greater_than_equal": "数值太小啦，必须大于或等于 {ge}",
    "less_than_equal": "数值太大啦，必须小于或等于 {le}",
    "int_parsing": "必须是有效的整数",
    "string_too_short": "字符串长度不能少于 {min_length}",
    "string_too_long": "字符串长度不能超过 {max_length}",
}

def register_exception_handlers(app: FastAPI):
    """注册全局异常捕获"""

    # # 1. 捕获自定义的业务异常 (AppException)
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.warning(f"业务异常: {request.method} {request.url} | Code: {exc.code} | Msg: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": exc.detail
            }
        )

    # 2. 捕获 FastAPI 自带的参数校验异常 (重写 422 响应)
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        formatted_errors = []

        for err in errors:
            # 获取发生错误的字段名 (比如 ['query', 'page'] -> 'page')
            field = err["loc"][-1]
            error_type = err["type"]

            # 尝试从翻译字典中获取自定义消息，如果没有则使用自带的英文消息
            # err['ctx'] 中包含了校验的阈值，比如 {'ge': 1}
            ctx = err.get("ctx", {})
            custom_msg = ERROR_MESSAGES.get(error_type, err["msg"]).format(**ctx)

            formatted_errors.append(f"{field}: {custom_msg}")

        error_msg = "; ".join(formatted_errors)

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "code": 422,
                "message": "参数校验失败",
                "details": error_msg
            }
        )

    # 3. 捕获所有未预期的异常 (兜底 500)
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"未捕获的系统异常: {request.method} {request.url}", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": 500,
                "message": "服务器内部繁忙，请稍后再试",
                "details": str(exc)  # 生产环境建议将此处设为 None，避免泄露代码结构
            }
        )