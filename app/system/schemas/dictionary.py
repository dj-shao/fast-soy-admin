# pyright: reportIncompatibleVariableOverride=false
"""系统字典 CRUD Schema。"""

from typing import Annotated

from pydantic import Field

from app.core.base_model import StatusType
from app.core.base_schema import PageQueryBase, SchemaBase
from app.core.types import Int32


class DictionaryBase(SchemaBase):
    dict_type: Annotated[str, Field(max_length=100)] | None = Field(None, title="字典类型")
    label: Annotated[str, Field(max_length=100)] | None = Field(None, title="显示标签")
    value: Annotated[str, Field(max_length=100)] | None = Field(None, title="存储值")
    order: Int32 | None = Field(None, title="排序")
    status: StatusType | None = Field(None, title="状态")
    remark: Annotated[str, Field(max_length=500)] | None = Field(None, title="备注")


class DictionaryCreate(DictionaryBase):
    dict_type: Annotated[str, Field(max_length=100)] = Field(title="字典类型")
    label: Annotated[str, Field(max_length=100)] = Field(title="显示标签")
    value: Annotated[str, Field(max_length=100)] = Field(title="存储值")


class DictionaryUpdate(DictionaryBase): ...


class DictionarySearch(DictionaryBase, PageQueryBase):
    pass
