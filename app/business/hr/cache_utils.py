"""
HR 模块缓存失效工具。

在员工数据变更（创建/编辑/删除/状态流转）后调用 ``invalidate_dept_stats()``
使部门统计缓存及时失效。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redis.asyncio import Redis


async def invalidate_dept_stats(redis: Redis | None) -> None:
    """清除部门统计缓存。

    使用 SCAN 遍历匹配的 key 并删除，避免在大量 key 时使用 KEYS 命令阻塞 Redis。
    """
    if redis is None:
        return
    cursor: int = 0
    while True:
        cursor, keys = await redis.scan(cursor=cursor, match="hr_dept_stats:*", count=100)
        if keys:
            await redis.delete(*keys)
        if cursor == 0:
            break
