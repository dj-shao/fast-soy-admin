"""自定义 Tortoise 字段类型。"""

from typing import Any

from tortoise import fields
from tortoise.models import Model

__all__ = ["DelimitedListField"]


class DelimitedListField(fields.CharField):
    """把 ``list[str]`` 以 ``|a|b|c|`` 格式存进 CharField。

    Python 端始终是 ``list[str]``，DB 端是带前后分隔符的字符串，
    查询可用 ``tags__icontains=f"|{tag}|"`` 精确匹配某个 tag，
    跨 SQLite / MySQL / PostgreSQL 都走 LIKE。

    注意：单个 tag 中若含分隔符 ``|`` 会被 strip。
    """

    DELIM = "|"

    def __init__(self, max_length: int = 500, **kwargs: Any) -> None:
        super().__init__(max_length=max_length, **kwargs)

    def to_db_value(self, value: Any, instance: type[Model] | Model) -> str | None:
        if not value:
            return None
        if isinstance(value, str):
            inner = value.strip(self.DELIM)
            return f"{self.DELIM}{inner}{self.DELIM}" if inner else None
        cleaned = [str(v).replace(self.DELIM, "") for v in value if v]
        if not cleaned:
            return None
        return f"{self.DELIM}{self.DELIM.join(cleaned)}{self.DELIM}"

    def to_python_value(self, value: Any) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return value
        return [t for t in str(value).strip(self.DELIM).split(self.DELIM) if t]
