"""循环重建：每 10 分钟清空所有表并重新执行完整启动初始化流程。

初始化顺序对齐 app/__init__.py 的 _run_init_data：
    init_menus -> refresh_api_list -> init_users -> 业务模块 init_data.init() -> refresh_all_cache

支持 sqlite / postgres / mysql / mssql —— 按连接的 `capabilities.dialect` 自动分派。
"""

import time
from typing import Any

from loguru import logger
from tortoise import Tortoise, run_async
from tortoise.backends.base.client import BaseDBAsyncClient

from app.core.autodiscover import discover_business_init_data
from app.core.cache import refresh_all_cache
from app.core.config import APP_SETTINGS
from app.core.redis import close_redis, init_redis
from app.system.api.utils import refresh_api_list
from app.system.init_data import init_menus, init_users

_KEEP_TABLES = {"tortoise_migrations"}


async def _list_tables(conn: BaseDBAsyncClient, dialect: str) -> list[str]:
    if dialect == "sqlite":
        sql = "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%';"
        key = "name"
    elif dialect == "postgres":
        sql = "SELECT tablename AS name FROM pg_tables WHERE schemaname = 'public';"
        key = "name"
    elif dialect == "mysql":
        sql = "SELECT table_name AS name FROM information_schema.tables WHERE table_schema = DATABASE();"
        key = "name"
    elif dialect == "mssql":
        sql = "SELECT name FROM sys.tables;"
        key = "name"
    else:
        raise RuntimeError(f"unsupported dialect: {dialect}")

    _, rows = await conn.execute_query(sql)
    return [row[key] for row in rows if row[key] not in _KEEP_TABLES]


async def _truncate(conn: BaseDBAsyncClient, dialect: str, tables: list[str]) -> None:
    if not tables:
        return

    if dialect == "sqlite":
        for name in tables:
            await conn.execute_query(f'DELETE FROM "{name}";')
            await conn.execute_query(f"UPDATE sqlite_sequence SET seq = 0 WHERE name = '{name}';")
    elif dialect == "postgres":
        joined = ", ".join(f'"{t}"' for t in tables)
        await conn.execute_query(f"TRUNCATE TABLE {joined} RESTART IDENTITY CASCADE;")
    elif dialect == "mysql":
        await conn.execute_query("SET FOREIGN_KEY_CHECKS = 0;")
        try:
            for name in tables:
                await conn.execute_query(f"TRUNCATE TABLE `{name}`;")
        finally:
            await conn.execute_query("SET FOREIGN_KEY_CHECKS = 1;")
    elif dialect == "mssql":
        # 关外键 → DELETE → 重置 IDENTITY → 开外键
        await conn.execute_query("EXEC sp_MSforeachtable 'ALTER TABLE ? NOCHECK CONSTRAINT ALL';")
        try:
            for name in tables:
                await conn.execute_query(f'DELETE FROM "{name}";')
                await conn.execute_query(
                    f"IF OBJECTPROPERTY(OBJECT_ID('{name}'), 'TableHasIdentity') = 1 "
                    f"DBCC CHECKIDENT ('{name}', RESEED, 0);"
                )
        finally:
            await conn.execute_query("EXEC sp_MSforeachtable 'ALTER TABLE ? WITH CHECK CHECK CONSTRAINT ALL';")
    else:
        raise RuntimeError(f"unsupported dialect: {dialect}")


async def reset_once() -> None:
    await Tortoise.init(config=APP_SETTINGS.TORTOISE_ORM)
    await Tortoise.generate_schemas()

    for conn_name in APP_SETTINGS.TORTOISE_ORM["connections"]:
        conn: Any = Tortoise.get_connection(conn_name)
        dialect: str = conn.capabilities.dialect
        tables = await _list_tables(conn, dialect)
        logger.debug(f"truncate {conn_name} ({dialect}): {len(tables)} tables")
        await _truncate(conn, dialect, tables)

    redis = await init_redis()
    try:
        await init_menus()
        await refresh_api_list()
        await init_users()
        for init_fn in discover_business_init_data():
            try:
                await init_fn()
            except Exception:
                module_name = getattr(init_fn, "__module__", "unknown")
                logger.exception(f"business init failed: {module_name}")
        await refresh_all_cache(redis)
    finally:
        await close_redis(redis)
        await Tortoise.close_connections()


if __name__ == "__main__":
    while True:
        run_async(reset_once())
        logger.info("Reset all tables")
        time.sleep(60 * 10)
