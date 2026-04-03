import math

from pydantic import BaseModel, ConfigDict, computed_field
from typing import Generic, TypeVar, List

T = TypeVar("T")

class PageResponse(BaseModel, Generic[T]):
    total: int          # 总条数
    data: List[T]      # 数据列表
    page: int           # 当前页码
    size: int           # 每页条数

    # 必须加上这一段，否则 Pydantic 无法处理 data 列表里的 ORM 对象
    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def total_pages(self) -> int:
        return math.ceil(self.total / self.size) if self.size > 0 else 0