from pydantic import BaseModel, ConfigDict, computed_field, Field
from typing import Generic, TypeVar, Optional, Any, List
import math

# 定义泛型变量
T = TypeVar("T")


class Result(BaseModel, Generic[T]):
    """全局统一响应结构"""
    code: int = Field(default=200, description="业务状态码，200代表请求成功")
    message: str = Field(default="success", description="响应提示信息")
    data: Optional[T] = Field(default=None, description="实际的业务数据")

    # ----------------------------------------------------
    # 提供几个便捷的类方法，方便在 Service 或 Router 中快速返回
    # ----------------------------------------------------

    @classmethod
    def success(cls, data: Optional[T] = None, message: str = "success") -> "Result[T]":
        """快速返回成功响应"""
        return cls(code=200, message=message, data=data)

    @classmethod
    def fail(cls, code: int = 400, message: str = "操作失败", data: Any = None) -> "Result[Any]":
        """快速返回失败响应（通常在业务逻辑不抛异常，只返回特殊状态时使用）"""
        return cls(code=code, message=message, data=data)


class PageResponse(BaseModel, Generic[T]):
    total: int  # 总条数
    data: List[T]  # 数据列表
    page: int  # 当前页码
    page_size: int  # 每页条数

    # 必须加上这一段，否则 Pydantic 无法处理 data 列表里的 ORM 对象
    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def total_pages(self) -> int:
        return math.ceil(self.total / self.page_size) if self.page_size > 0 else 0
