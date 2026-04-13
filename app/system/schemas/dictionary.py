# pyright: reportIncompatibleVariableOverride=false
"""系统字典 CRUD Schema。"""

from pydantic import Field

from app.core.base_model import StatusType
from app.core.base_schema import PageQueryBase, SchemaBase


class DictionaryBase(SchemaBase):
    dict_type: str | None = Field(None, title="字典类型")
    label: str | None = Field(None, title="显示标签")
    value: str | None = Field(None, title="存储值")
    order: int | None = Field(None, title="排序")
    status: StatusType | None = Field(None, title="状态")
    remark: str | None = Field(None, title="备注")


class DictionaryCreate(DictionaryBase):
    dict_type: str = Field(title="字典类型")
    label: str = Field(title="显示标签")
    value: str = Field(title="存储值")


class DictionaryUpdate(DictionaryBase): ...


class DictionarySearch(DictionaryBase, PageQueryBase):
    pass
