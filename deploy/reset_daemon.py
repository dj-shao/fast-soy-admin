"""循环重建数据库的 daemon：每 10 分钟清空所有表并重新执行完整启动初始化流程。

以独立容器形式常驻运行（见 docker-compose.yml 的 `reset_daemon` 服务, profile=reset）。
容器内 while True + sleep(600) 自循环; 异常退出由 docker `restart: unless-stopped` 拉起。

初始化顺序对齐 app/__init__.py 的 _run_init_data：
    init_menus -> refresh_api_list -> init_users -> 业务模块 init_data.init() -> refresh_all_cache

支持 sqlite / postgres / mysql / mssql —— 按连接的 `capabilities.dialect` 自动分派。
"""

import asyncio
import os
import time
from typing import Any

import httpx
from loguru import logger
from tortoise import Tortoise, run_async
from tortoise.backends.base.client import BaseDBAsyncClient

from app.core.autodiscover import discover_business_init_data
from app.core.cache import refresh_all_cache
from app.core.config import APP_SETTINGS
from app.core.redis import close_redis, init_redis
from app.system.api.utils import refresh_api_list
from app.system.init_data import init_menus, init_users

_APP_BASE_URL = os.getenv("RESET_DAEMON_APP_URL", "http://app:9999")
_SEED_USER = os.getenv("RESET_DAEMON_USER", "Soybean")
_SEED_PASSWORD = os.getenv("RESET_DAEMON_PASSWORD", "123456")

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


async def _populate_radar_data(base_url: str) -> None:
    """初始化完成后向后端发起若干请求，让 Radar 监控有数据。

    - 登录获取 JWT
    - 多次调用部门列表接口（有效请求，生成性能监控数据）
    - 调用 /__radar/api/_boom 触发未捕获异常（需 APP_DEBUG=true）
    - 请求一个不存在的业务路径（生成 404 记录）
    """
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        # 等待 app /health 就绪（最长 ~60s）
        for _ in range(60):
            try:
                r = await client.get("/health", timeout=2.0)
                if r.status_code == 200:
                    break
            except Exception:
                pass
            await asyncio.sleep(1)
        else:
            logger.warning(f"radar populate: /health not ready after 60s (base_url={base_url})")
            return

        try:
            resp = await client.post(
                "/api/v1/auth/login",
                json={"userName": _SEED_USER, "password": _SEED_PASSWORD},
            )
            payload = resp.json()
            token = (payload.get("data") or {}).get("token")
        except Exception:
            logger.exception(f"radar populate: login failed (base_url={base_url})")
            return

        if not token:
            logger.warning(f"radar populate: login returned no token: {payload}")
            return

        headers = {"Authorization": f"Bearer {token}"}

        # 正常请求：部门列表搜索（构造不同分页参数制造多条数据）
        for current, size in [(1, 10), (1, 5), (2, 10)]:
            try:
                await client.post(
                    "/api/v1/business/hr/departments/search",
                    headers=headers,
                    json={"current": current, "size": size, "name": None, "code": None, "status": None},
                )
            except Exception:
                logger.exception("radar populate: departments/search failed")

        # 触发未捕获异常
        for kind in ("runtime", "zero", "key", "attr"):
            try:
                await client.get("/__radar/api/_boom", params={"kind": kind}, headers=headers)
            except Exception:
                # boom 会返回 500，httpx 不抛；真正网络错误才落入此处
                logger.exception(f"radar populate: _boom({kind}) failed")

        # 404：不存在的业务路径
        try:
            await client.get("/api/v1/business/hr/departments/not-exist-xxx", headers=headers)
        except Exception:
            logger.exception("radar populate: 404 probe failed")


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

    await _populate_radar_data(_APP_BASE_URL)


if __name__ == "__main__":
    while True:
        run_async(reset_once())
        logger.info("Reset all tables")
        time.sleep(60 * 10)
