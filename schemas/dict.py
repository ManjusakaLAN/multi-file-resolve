from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


# 1. 共享属性基类 (定义公共字段)
class DictBase(BaseModel):
    dict_code: str = Field(..., description="字典编码", max_length=50)
    label: Optional[str] = Field(None, description="字典名称/标签", max_length=100)
    value: Optional[str] = Field(None, description="字典键值", max_length=100)
    sort: int = Field(default=0, description="排序")
    is_system: int = Field(default=0, description="是否系统内部数据 (通常 0:否, 1:是)")


# 2. 创建字典时使用的 Schema (POST)
class DictCreate(DictBase):
    """
    创建字典时的入参。
    由于 DictBase 中的字段已经满足创建需求（dict_code 必填，其他有默认值或可选），
    这里直接继承即可。如果后续有仅在创建时需要的字段，可以在这里添加。
    """
    pass


# 3. 更新字典信息时使用的 Schema (PATCH/PUT)
class DictUpdate(BaseModel):
    """
    更新字典时的入参。
    所有字段均设为 Optional，表示只更新传入的字段。
    """
    id: str = Field(..., description="字典ID")
    dict_code: Optional[str] = Field(None, description="字典编码", max_length=50)
    label: Optional[str] = Field(None, description="字典名称/标签", max_length=100)
    value: Optional[str] = Field(None, description="字典键值", max_length=100)
    sort: Optional[int] = Field(None, description="排序")
    is_system: Optional[int] = Field(None, description="是否系统内部数据")


# 4. 接口返回/读取详细信息时使用的 Schema (Response)
class DictResponse(DictBase):
    """
    返回给前端的字典信息，包含主键 ID 等由数据库生成的字段。
    """
    id: str = Field(..., description="字典ID")

    # Pydantic V2 配置：允许从 SQLAlchemy 模型对象直接转换
    model_config = ConfigDict(from_attributes=True)
