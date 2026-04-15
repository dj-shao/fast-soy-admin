"""字段级约束类型别名 — 与数据库列类型范围对齐。

在 Pydantic schema 中直接用这些别名替代 ``int``/``str``，让前端传入的
数值或文本超出边界时在进入业务代码之前就被 422 拦截。

业务模块统一从 ``app.utils`` 导入；``app.system.*`` 内部为避免循环导入，
应直接从 ``app.core.types`` 导入::

    from app.utils import Int32              # 业务模块
    from app.core.types import Int32         # 系统模块

    class ProductCreate(SchemaBase):
        stock: Int32 = Field(title="库存")
"""

from typing import Annotated

from pydantic import Field

__all__ = ["Int16", "Int32", "Int64"]

# 有符号整型范围（与 Tortoise SmallIntField / IntField / BigIntField 对齐，
# 同时也匹配 PostgreSQL smallint / int / bigint 与 MySQL SMALLINT / INT / BIGINT）。
Int16 = Annotated[int, Field(ge=-32_768, le=32_767)]
Int32 = Annotated[int, Field(ge=-2_147_483_648, le=2_147_483_647)]
Int64 = Annotated[int, Field(ge=-9_223_372_036_854_775_808, le=9_223_372_036_854_775_807)]
