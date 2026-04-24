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

from typing import Annotated, Any

from pydantic import BeforeValidator, Field, PlainSerializer

from app.core.sqids import decode_id, encode_id

__all__ = ["Int16", "Int32", "Int64", "SqidId", "SqidPath"]

# 有符号整型范围（与 Tortoise SmallIntField / IntField / BigIntField 对齐，
# 同时也匹配 PostgreSQL smallint / int / bigint 与 MySQL SMALLINT / INT / BIGINT）。
Int16 = Annotated[int, Field(ge=-32_768, le=32_767)]
Int32 = Annotated[int, Field(ge=-2_147_483_648, le=2_147_483_647)]
Int64 = Annotated[int, Field(ge=-9_223_372_036_854_775_808, le=9_223_372_036_854_775_807)]


def _sqid_to_int(v: Any) -> int:
    return decode_id(str(v))


# 请求/响应两端均走 sqid 字符串；校验时把 sqid 解成 int，JSON 序列化时再编回 sqid。
# 仅在 JSON 模式序列化时编码，Python 模式（model_dump()）保留 int，避免在传给 ORM 时把 FK 变成字符串。
SqidId = Annotated[int, BeforeValidator(_sqid_to_int), PlainSerializer(encode_id, return_type=str, when_used="json")]
# 仅用于 FastAPI 路径参数（``{item_id}``），只需解码 sqid → int，不参与序列化输出。
SqidPath = Annotated[int, BeforeValidator(_sqid_to_int)]
