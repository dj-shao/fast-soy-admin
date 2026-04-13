from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from tortoise import fields, models

from app.core.config import APP_SETTINGS
from app.core.tools import to_lower_camel_case


class BaseModel(models.Model):
    async def to_dict(
        self,
        include_fields: list[str] | None = None,
        exclude_fields: list[str] | None = None,
        m2m: bool = False,
        fmt_datetime: bool = True,
    ):
        """将模型实例转为 camelCase 字典。

        Args:
            include_fields: 仅包含指定字段（白名单）。
            exclude_fields: 排除指定字段（黑名单）。
            m2m: 是否同时序列化多对多关系。
            fmt_datetime: 是否额外输出格式化时间字段（``fmtCreatedAt`` 等）。
                为 False 时 datetime 仅输出毫秒时间戳。
        """
        include_fields = include_fields or []
        exclude_fields = exclude_fields or []

        d = {}
        for field in self._meta.db_fields:
            if (not include_fields or field in include_fields) and (not exclude_fields or field not in exclude_fields):
                value = getattr(self, field)
                if isinstance(value, datetime):
                    if fmt_datetime:
                        d[to_lower_camel_case("fmt_" + field)] = value.strftime(APP_SETTINGS.DATETIME_FORMAT)
                    value = int(value.timestamp() * 1000)
                elif isinstance(value, UUID):
                    value = str(value)
                elif isinstance(value, Decimal):
                    value = float(value)
                elif isinstance(value, Enum):
                    value = value.value
                d[to_lower_camel_case(field)] = value

        if m2m:
            for field in self._meta.m2m_fields:
                if (not include_fields or field in include_fields) and (not exclude_fields or field not in exclude_fields):
                    values = [value for value in await getattr(self, field).all().values()]
                    for value in values:
                        _value = value.copy()
                        for k, v in _value.items():
                            if isinstance(v, datetime):
                                if fmt_datetime:
                                    d[to_lower_camel_case("fmt_" + field)] = v.strftime(APP_SETTINGS.DATETIME_FORMAT)
                                v = int(v.timestamp() * 1000)
                            elif isinstance(v, UUID):
                                v = str(v)
                            elif isinstance(v, Decimal):
                                v = float(v)
                            value.pop(k)
                            value[to_lower_camel_case(k)] = v
                    d[to_lower_camel_case(field)] = values
        return d

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        abstract = True


class AuditMixin:
    created_by = fields.CharField(max_length=64, null=True, description="创建人")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_by = fields.CharField(max_length=64, null=True, description="更新人")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")


class EnumBase(Enum):
    @classmethod
    def get_member_values(cls):
        return [item.value for item in cls._member_map_.values()]

    @classmethod
    def get_member_names(cls):
        return [name for name in cls._member_names_]

    @classmethod
    def get_name_by_value(cls, value: str | int):
        for item in cls._member_map_.values():
            if item.value == value:
                return item.name


class IntEnum(int, EnumBase): ...


class StrEnum(str, EnumBase): ...


class MethodType(str, Enum):
    GET = "get"
    POST = "post"
    PUT = "put"
    PATCH = "patch"
    DELETE = "delete"


class StatusType(str, Enum):
    all = "0"
    enable = "1"
    disable = "2"
    invalid = "3"


class GenderType(str, Enum):
    male = "1"
    female = "2"
    unknow = "3"  # Soybean 前端未使用


class MenuType(str, Enum):
    catalog = "1"  # 目录
    menu = "2"  # 菜单


class IconType(str, Enum):
    iconify = "1"
    local = "2"


__all__ = ["BaseModel", "AuditMixin", "EnumBase", "IntEnum", "StrEnum", "MethodType", "StatusType", "GenderType", "MenuType", "IconType"]
